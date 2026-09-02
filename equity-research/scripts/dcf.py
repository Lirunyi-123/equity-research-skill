#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dcf.py — 三情景 DCF + 敏感性矩阵（equity-research skill）

用法:
    python3 dcf.py params.json          # 输出 markdown 报告
    python3 dcf.py params.json --json   # 仅输出 JSON

输入格式见同目录 examples/dcf_example.json。
单位: FCF 亿元、净现金 亿元、股本 亿股 → 每股价值 = 亿元/亿股 = 元。
仅标准库。所有输入参数在报告中标【假设】。
"""
import json
import sys


def value_scenario(base_fcf, growths, terminal_g, wacc, net_cash, shares):
    fcf = base_fcf
    pv = 0.0
    for t, gr in enumerate(growths, start=1):
        fcf *= (1 + gr)
        pv += fcf / (1 + wacc) ** t
    if terminal_g >= wacc:
        return {"per_share": None, "error": "永续增长率 >= WACC，终值无意义"}
    pv_tv = fcf * (1 + terminal_g) / (wacc - terminal_g) / (1 + wacc) ** len(growths)
    equity = pv + pv_tv + net_cash
    per_share = equity / shares if shares else None
    return {
        "fcf_path_end": fcf,
        "pv_explicit": pv,
        "pv_terminal": pv_tv,
        "terminal_share_of_value": pv_tv / (pv + pv_tv),
        "equity_value_yi": equity,
        "per_share": per_share,
    }


def fmt(x):
    return "-" if x is None else f"{x:,.1f}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    as_json = "--json" in sys.argv
    with open(sys.argv[1], encoding="utf-8") as f:
        p = json.load(f)

    base_fcf = p["base_fcf_yi"]
    net_cash = p.get("net_cash_yi", 0.0)
    shares = p["total_shares_yi"]
    price = p.get("market_price")
    scen_names = ["bear", "base", "bull"]
    scen_label = {"bear": "悲观", "base": "基准", "bull": "乐观"}

    out = {"company": p.get("company"), "scenarios": {}}
    for name in scen_names:
        s = p["scenarios"][name]
        r = value_scenario(base_fcf, s["growth"], s["terminal_g"], s["wacc"], net_cash, shares)
        if price and r.get("per_share"):
            r["safety_margin"] = 1 - price / r["per_share"]
        out["scenarios"][name] = {"params": s, **r}

    sens = p.get("sensitivity")
    base_growth = p["scenarios"]["base"]["growth"]
    matrix = None
    if sens:
        waccs = sens["wacc_list"]
        tgs = sens["terminal_g_list"]
        matrix = [[value_scenario(base_fcf, base_growth, tg, w, net_cash, shares)["per_share"]
                   for tg in tgs] for w in waccs]
        out["sensitivity"] = {"wacc_list": waccs, "terminal_g_list": tgs, "matrix": matrix}

    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print(f"# DCF 计算结果 — {p.get('company','')}\n")
    print(f"基期FCF: {fmt(base_fcf)} 亿元；净现金: {fmt(net_cash)} 亿元；股本: {shares} 亿股"
          + (f"；现价: {price} 元\n" if price else "\n"))
    print("| 情景 | 显性期增速 | 永续g | WACC | 每股价值(元) | 安全边际 | 终值占比 |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for name in scen_names:
        s = p["scenarios"][name]
        r = out["scenarios"][name]
        g_str = "/".join(f"{g*100:.0f}" for g in s["growth"])
        sm = r.get("safety_margin")
        ts = r.get("terminal_share_of_value")
        print(f"| {scen_label[name]} | {g_str}% | {s['terminal_g']*100:.1f}% | {s['wacc']*100:.1f}% "
              f"| {fmt(r.get('per_share'))} | {('-' if sm is None else f'{sm*100:.0f}%')} "
              f"| {('-' if ts is None else f'{ts*100:.0f}%')} |")
    vals = [out["scenarios"][n].get("per_share") for n in scen_names if out["scenarios"][n].get("per_share")]
    if len(vals) >= 2:
        print(f"\n**每股价值区间（悲观~乐观）: {min(vals):,.0f} ~ {max(vals):,.0f} 元；中枢=基准情景**【假设】")
    if matrix:
        print("\n## 敏感性矩阵（基准情景路径；行=WACC，列=永续增长率；单位:元/股）【假设】")
        waccs = out["sensitivity"]["wacc_list"]
        tgs = out["sensitivity"]["terminal_g_list"]
        print("| WACC\\g | " + " | ".join(f"{tg*100:.1f}%" for tg in tgs) + " |")
        print("|---|" + "---:|" * len(tgs))
        for w, row in zip(waccs, matrix):
            print(f"| {w*100:.1f}% | " + " | ".join(fmt(v) for v in row) + " |")
        flat = [v for row in matrix for v in row if v is not None]
        if flat and max(flat) / max(min(flat), 1e-9) > 2:
            print("\n⚠️ 矩阵角点值相差超过2倍：估值对参数高度敏感，结论须保守并注明不确定性高。")
    print("\n（以上全部为【假设】驱动的模型输出，不构成任何投资建议）")


if __name__ == "__main__":
    main()
