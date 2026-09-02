#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selfcheck.py — equity-research skill 自检脚本。

用途：
    1. 新用户安装后跑一遍，确认环境与脚本可用（hello world）；
    2. 东财/腾讯公开接口变动时第一时间报警（接口失效先看 endpoints.py）。

用法：
    python3 selfcheck.py            # 离线 + 在线全部检查
    python3 selfcheck.py --offline  # 只跑离线检查（无需网络）

退出码：任一检查失败 exit 1，全部通过 exit 0。仅标准库。
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "examples")
PY = sys.executable

results = []  # (名称, 是否通过, 一句话说明)


def check(name, fn):
    try:
        ok, note = fn()
    except Exception as e:  # noqa: BLE001 — 自检不得崩溃，异常即失败
        ok, note = False, f"执行异常: {e}"
    results.append((name, ok, note))
    print(f"{'✅' if ok else '❌'} {name} — {note}")
    return ok


def run(script, *args):
    """跑 scripts/ 下某脚本，返回 (returncode, stdout)。"""
    p = subprocess.run([PY, os.path.join(HERE, script), *args],
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


# ---------------------------------------------------------------- 离线检查
def offline_calc():
    rc, out, err = run("calc.py", os.path.join(EXAMPLES, "financials_example.json"))
    if rc != 0:
        return False, f"calc.py 退出码 {rc}: {err.strip()[:100]}"
    with open(os.path.join(EXAMPLES, "calc_example.expected.md"), encoding="utf-8") as f:
        expected = f.read()
    if out.strip() == expected.strip():
        return True, "calc.py 输出与 expected 一致"
    return False, "calc.py 输出与 calc_example.expected.md 不一致（脚本逻辑被改动或环境差异）"


def offline_dcf():
    rc, out, err = run("dcf.py", os.path.join(EXAMPLES, "dcf_example.json"))
    if rc != 0:
        return False, f"dcf.py 退出码 {rc}: {err.strip()[:100]}"
    with open(os.path.join(EXAMPLES, "dcf_example.expected.md"), encoding="utf-8") as f:
        expected = f.read()
    if out.strip() == expected.strip():
        return True, "dcf.py 输出与 expected 一致"
    return False, "dcf.py 输出与 dcf_example.expected.md 不一致"


# ---------------------------------------------------------------- 在线检查
def online_quote():
    rc, out, err = run("fetch_quote.py", "600519", "--json")
    if rc != 0:
        return False, f"行情接口失败（看 endpoints.py 是否需更新）: {(err or out).strip()[:100]}"
    d = json.loads(out)
    if d.get("ok") and d.get("price"):
        return True, f"{d.get('name')} 现价 {d['price']} 元（{d.get('source')}）"
    return False, f"返回缺字段: {out[:100]}"


def online_collect():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tmp = tf.name
    try:
        rc, out, err = run("collect_f10.py", "600519.SH", tmp)
        if rc != 0:
            return False, f"财务接口失败: {(err or out).strip()[:100]}"
        with open(tmp, encoding="utf-8") as f:
            d = json.load(f)
        years = d.get("years", [])
        if len(years) < 5:
            return False, f"仅采到 {len(years)} 年数据"
        rev = years[0].get("revenue") or 0
        if not (100 < rev < 10000):
            return False, f"营收 {rev} 数量级异常（应为百~千亿元，检查单位换算）"
        return True, f"采到 {len(years)} 年年报，{d.get('company')} 最新年营收 {rev:.0f} 亿元"
    finally:
        os.unlink(tmp)


def online_pe():
    rc, out, err = run("pe_percentile.py", "600519.SH")
    if rc == 0 and "分位" in out:
        return True, out.strip().splitlines()[0][:80]
    return False, f"估值序列接口失败: {(err or out).strip()[:100]}"


def online_sections():
    rc, out, err = run("f10_sections.py", "SH600519")
    if rc == 0 and "十大股东" in out:
        return True, "主营构成与十大股东采集成功"
    return False, f"F10 分节接口失败: {(err or out).strip()[:100]}"


def main():
    offline_only = "--offline" in sys.argv
    print("== 离线检查（calc/dcf 计算引擎）==")
    check("calc.py 指标计算", offline_calc)
    check("dcf.py 三情景估值", offline_dcf)
    if not offline_only:
        print("\n== 在线检查（公开接口连通性，失效看 endpoints.py）==")
        check("fetch_quote.py 行情快照", online_quote)
        check("collect_f10.py 财务序列", online_collect)
        check("pe_percentile.py 估值分位", online_pe)
        check("f10_sections.py F10 分节", online_sections)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n总结: {passed}/{len(results)} 通过")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
