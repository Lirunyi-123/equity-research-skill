#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_quote.py — A股行情与估值快照（equity-research skill，尽力而为）

用法:
    python3 fetch_quote.py 600519           # 默认输出人类可读摘要
    python3 fetch_quote.py SH600519 --json  # 输出完整机器可读 JSON

输出约定（本 skill 全部采集脚本统一）：
    默认打印人类可读摘要（markdown/文本）；
    加 --json 时输出完整机器可读 JSON（结构见各脚本 main 返回值）。

数据源: 腾讯行情接口(主) → 东方财富 push2(备)。均为公开非官方接口，可能变动；
输出务必与东方财富/新浪 F10 网页抽查核对后才能写入报告。失败时打印 guidance，
改走网页采集，不得编造。北交所暂不支持，请走网页。仅标准库。

接口 URL / UA / 超时集中配置在同目录 endpoints.py，本文件不硬编码任何 URL。
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime

import endpoints


def parse_symbol(arg):
    s = arg.strip().upper()
    m = re.match(r"^(SH|SZ|BJ)?(\d{6})$", s)
    if not m:
        die(f"无法解析代码: {arg}（仅支持6位A股代码）")
    pre, code = m.group(1), m.group(2)
    if pre is None:
        if code.startswith("6"):
            pre = "SH"
        elif code[0] in "03":
            pre = "SZ"
        elif code[0] in "48":
            die("北交所代码暂不支持自动行情，请走网页采集")
        elif code[0] == "5":
            die("5开头是沪市基金/ETF代码，本skill仅覆盖上市公司股票")
        else:
            die(f"无法识别代码归属: {code}（沪6/深0/3/创业板3/科创688/北4·8）")
    if pre == "BJ":
        die("北交所代码暂不支持自动行情，请走网页采集")
    # 腾讯接口区分大小写，只认小写前缀
    return (pre + code).lower(), pre.lower(), code


def die(msg, sym=None):
    page = f"quote.eastmoney.com/{sym}.html" if sym else "东方财富/新浪个股页"
    print(json.dumps({"ok": False, "error": msg,
                      "guidance": f"改走网页采集：WebFetch 东方财富个股页 {page} "
                                  "或新浪财经个股页，记录现价/市值/PE/PB 及访问时间"},
                     ensure_ascii=False))
    sys.exit(1)


def http_get(url, decode="utf-8"):
    req = urllib.request.Request(url, headers=endpoints.UA)
    return urllib.request.urlopen(req, timeout=endpoints.TIMEOUT_QUOTE).read().decode(decode, "ignore")


def num(fields, i):
    try:
        v = float(fields[i])
        return v if v != 0 else None
    except (ValueError, IndexError):
        return None


def fetch_tencent(sym):
    raw = http_get(endpoints.TENCENT_QUOTE_URL.format(sym=sym), decode="gbk")
    m = re.search(r'"(.*)"', raw)
    if not m:
        raise RuntimeError("腾讯接口返回为空或格式变化")
    f = m.group(1).split("~")
    # 需要 1(名称) 3(价) 39(PE) 44/45(市值) 46(PB)，共47个字段（位置见 endpoints.py 注释）
    if len(f) < 47 or not f[1] or not num(f, 3):
        raise RuntimeError(f"腾讯接口字段缺失(len={len(f)})")
    return {
        "ok": True, "source": "qt.gtimg.cn", "symbol": sym, "name": f[1],
        "price": num(f, 3), "pe_ttm": num(f, 39),
        "float_mcap_yi": num(f, 44), "total_mcap_yi": num(f, 45), "pb": num(f, 46),
        "quote_time": f[30] if len(f) > 30 else None,
    }


def fetch_eastmoney(mkt, code):
    secid = f"{'1' if mkt == 'sh' else '0'}.{code}"
    data = json.loads(http_get(
        endpoints.EM_PUSH2_URL.format(secid=secid, fields=endpoints.EM_PUSH2_FIELDS)))
    d = data.get("data") or {}
    if not d.get("f58"):
        raise RuntimeError("东方财富接口返回为空")

    def scale100(v):
        # push2 接口的比率和价格字段为实际值×100（见 endpoints.py 注释）
        return v / 100 if isinstance(v, (int, float)) else None

    return {
        "ok": True, "source": "push2.eastmoney.com", "symbol": f"{mkt}{code}",
        "name": d.get("f58"), "price": scale100(d.get("f43")),
        "pe_ttm": scale100(d.get("f163")), "pb": scale100(d.get("f167")),
        "total_mcap_yi": (d.get("f116") / 1e8 if isinstance(d.get("f116"), (int, float)) else None),
        "float_mcap_yi": (d.get("f117") / 1e8 if isinstance(d.get("f117"), (int, float)) else None),
        "quote_time": None,
    }


def get_quote(code_arg):
    """主流程：解析代码 → 腾讯(主)/东财push2(备) 降级链，返回结果 dict。"""
    sym, mkt, code = parse_symbol(code_arg)
    result = None
    errors = []
    for attempt in range(2):  # 出网连接偶发被重置，每源重试一次
        for fetcher in (lambda: fetch_tencent(sym), lambda: fetch_eastmoney(mkt, code)):
            try:
                result = fetcher()
                break
            except Exception as e:  # noqa: BLE001 — 降级链：记录错误换下一源
                errors.append(f"第{attempt+1}次: {e}")
        if result:
            break
        time.sleep(1)
    if not result:
        die("；".join(errors), sym=sym)
    result["unit_note"] = "价格元；市值亿元；PE/PB为倍数。来自非官方公开接口，用前与F10网页抽查核对。"
    result["errors_ignored"] = errors or None
    result["accessed_at"] = datetime.now().isoformat(timespec="seconds")
    return result


def print_summary(r):
    """默认的人类可读摘要：名称/现价/市值/PE/PB/来源/访问时间。"""
    def fmt(v, nd=2):
        return "-" if v is None else f"{v:,.{nd}f}"
    print(f"行情快照 — {r['name']}（{r['symbol']}）")
    print(f"- 现价: {fmt(r['price'])} 元")
    print(f"- 总市值: {fmt(r['total_mcap_yi'], 1)} 亿元；流通市值: {fmt(r['float_mcap_yi'], 1)} 亿元")
    print(f"- PE(TTM): {fmt(r['pe_ttm'])}；PB: {fmt(r['pb'])}")
    print(f"- 数据来源: {r['source']}；访问时间: {r['accessed_at']}")
    if r.get("quote_time"):
        print(f"- 行情时间: {r['quote_time']}")
    print(f"- 注意: {r['unit_note']}")


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(2)
    result = get_quote(args[0])
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)


if __name__ == "__main__":
    main()
