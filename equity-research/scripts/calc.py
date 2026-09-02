#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calc.py — 财务指标计算器（equity-research skill）

用法:
    python3 calc.py financials.json          # 输出 markdown 指标表 + 摘要
    python3 calc.py financials.json --json   # 仅输出 JSON

输入格式见同目录 examples/financials_example.json。
金额单位亿元，股本单位亿股。缺项不猜测，记入 warnings。仅标准库。
"""
import json
import sys


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def cagr(first, last, years):
    if first is None or last is None or years is None or years <= 0:
        return None
    if first <= 0 or last <= 0:
        return None
    return (last / first) ** (1.0 / years) - 1.0


def avg2(a, b):
    vals = [v for v in (a, b) if v is not None]
    return sum(vals) / len(vals) if vals else None


def pct(x, nd=1):
    return "-" if x is None else f"{x*100:.{nd}f}%"


def num(x, nd=2):
    return "-" if x is None else f"{x:,.{nd}f}"


def yoy(cur, prev):
    if cur is None or prev is None or prev == 0:
        return None
    return (cur - prev) / abs(prev)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    as_json = "--json" in sys.argv
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    years = sorted(data.get("years", []), key=lambda y: y.get("year", 0))
    if len(years) < 2:
        print("[calc] 至少需要两个年度的数据", file=sys.stderr)
        sys.exit(1)

    warnings = []
    rows = []
    roes, ocf_nps, fcfs = [], [], []
    for i, y in enumerate(years):
        prev = years[i - 1] if i > 0 else None
        rev = y.get("revenue")
        np_ = y.get("net_profit")
        dnp = y.get("deduct_net_profit")
        if rev is None or np_ is None:
            warnings.append(f"{y.get('year')}: 缺 revenue 或 net_profit")
        ocf = y.get("operating_cash_flow")
        capex = y.get("capex")
        fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
        ta = y.get("total_assets")
        tl = y.get("total_liabilities")
        eq = y.get("equity", y.get("net_assets"))
        ta_p = prev.get("total_assets") if prev else None
        eq_p = prev.get("equity", prev.get("net_assets")) if prev else None
        roe = safe_div(np_, avg2(eq, eq_p))
        roa = safe_div(np_, avg2(ta, ta_p))
        ocf_np = safe_div(ocf, np_)
        row = {
            "year": y.get("year"),
            "revenue": rev,
            "rev_yoy": yoy(rev, prev.get("revenue") if prev else None),
            "net_profit": np_,
            "np_yoy": yoy(np_, prev.get("net_profit") if prev else None),
            "deduct_net_profit": dnp,
            "deduct_np_yoy": yoy(dnp, prev.get("deduct_net_profit") if prev else None),
            "gross_margin": y.get("gross_margin_percent"),
            "net_margin": safe_div(np_, rev),
            "roe": roe,
            "roa": roa,
            "ocf": ocf,
            "fcf": fcf,
            "ocf_np": ocf_np,
            "debt_ratio": safe_div(tl, ta),
            "turnover": safe_div(rev, avg2(ta, ta_p)),
            "equity_multiplier": safe_div(avg2(ta, ta_p), avg2(eq, eq_p)),
        }
        rows.append(row)
        if roe is not None:
            roes.append(roe)
        if ocf_np is not None:
            ocf_nps.append(ocf_np)
        if fcf is not None:
            fcfs.append(fcf)

    def col(key, i):
        return years[i].get(key)

    n_span = len(years) - 1
    summary = {
        "years_covered": [years[0]["year"], years[-1]["year"]],
        "revenue_cagr_full": cagr(col("revenue", 0), col("revenue", -1), n_span),
        "net_profit_cagr_full": cagr(col("net_profit", 0), col("net_profit", -1), n_span),
        "deduct_np_cagr_full": cagr(col("deduct_net_profit", 0), col("deduct_net_profit", -1), n_span),
        "roe_avg": sum(roes) / len(roes) if roes else None,
        "roe_min": min(roes) if roes else None,
        "roe_max": max(roes) if roes else None,
        "ocf_np_avg": sum(ocf_nps) / len(ocf_nps) if ocf_nps else None,
        "fcf_sum": sum(fcfs) if fcfs else None,
    }
    if len(years) >= 6:  # 近5年 CAGR（需要6个点）
        summary["revenue_cagr_5y"] = cagr(col("revenue", -6), col("revenue", -1), 5)
        summary["net_profit_cagr_5y"] = cagr(col("net_profit", -6), col("net_profit", -1), 5)
        summary["deduct_np_cagr_5y"] = cagr(col("deduct_net_profit", -6), col("deduct_net_profit", -1), 5)

    # 市场快照衍生指标
    mkt = data.get("market") or {}
    rev_last = col("revenue", -1)
    np_last = col("net_profit", -1)
    mkt_calc = {
        "ps": safe_div(mkt.get("total_market_cap"), rev_last),
        "pe_static_check": safe_div(mkt.get("total_market_cap"), np_last),
        "dividend_yield": safe_div(mkt.get("dividend_per_share_ttm"), mkt.get("price")),
    }

    # 自动红旗（提示线索，须人工复核）
    flags = []
    recent = [r for r in rows[-3:] if r["ocf_np"] is not None]
    if len(recent) >= 2 and all(r["ocf_np"] < 0.8 for r in recent):
        flags.append("近%d年经营现金流/净利润均<0.8：利润质量风险，需核查应收/存货" % len(recent))
    if summary["roe_avg"] is not None and summary["roe_avg"] < 0.08:
        flags.append("平均ROE<8%：盈利能力偏弱")
    last_y = years[-1]
    gw_ratio = safe_div(last_y.get("goodwill"), last_y.get("equity", last_y.get("net_assets")))
    if gw_ratio is not None and gw_ratio > 0.2:
        flags.append(f"商誉/净资产={pct(gw_ratio)}：超过20%红线")
    if summary.get("fcf_sum") is not None and summary["fcf_sum"] < 0:
        flags.append("区间内FCF合计为负：商业模式造血能力存疑")

    result = {"company": data.get("company"), "rows": rows, "summary": summary,
              "market_derived": mkt_calc, "auto_flags": flags, "warnings": warnings}

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"# 指标计算结果 — {data.get('company','')}\n")
    hdr = ["年份", "营收", "增速", "净利", "增速", "扣非", "毛利率", "净利率", "ROE", "OCF", "FCF", "OCF/NP", "负债率"]
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---:|" * len(hdr))
    for r in rows:
        print("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            r["year"], num(r["revenue"]), pct(r["rev_yoy"]), num(r["net_profit"]),
            pct(r["np_yoy"]), num(r["deduct_net_profit"]),
            pct(r["gross_margin"] / 100 if r["gross_margin"] else None) if r["gross_margin"] else "-",
            pct(r["net_margin"]), pct(r["roe"]), num(r["ocf"]), num(r["fcf"]),
            num(r["ocf_np"]), pct(r["debt_ratio"])))
    print("\n## 摘要【计算】")
    print(f"- 区间: {summary['years_covered'][0]}–{summary['years_covered'][1]}（{len(years)}年）")
    print(f"- 营收CAGR(全区间): {pct(summary['revenue_cagr_full'])}"
          + (f"；近5年: {pct(summary.get('revenue_cagr_5y'))}" if summary.get("revenue_cagr_5y") is not None else ""))
    print(f"- 净利CAGR(全区间): {pct(summary['net_profit_cagr_full'])}"
          + (f"；近5年: {pct(summary.get('net_profit_cagr_5y'))}" if summary.get("net_profit_cagr_5y") is not None else ""))
    print(f"- ROE 均值 {pct(summary['roe_avg'])}（{pct(summary['roe_min'])}~{pct(summary['roe_max'])}）")
    print(f"- OCF/净利 均值: {num(summary['ocf_np_avg'])}；FCF 合计: {num(summary['fcf_sum'])}")
    if mkt.get("total_market_cap"):
        print(f"- PS(静态): {num(mkt_calc['ps'])}；PE(静态,校验用): {num(mkt_calc['pe_static_check'])}"
              + (f"；股息率: {pct(mkt_calc['dividend_yield'])}" if mkt_calc["dividend_yield"] else ""))
    if flags:
        print("\n## 自动红旗提示（线索，须人工复核）")
        for fl in flags:
            print(f"- ⚠️ {fl}")
    if warnings:
        print("\n## 数据警告")
        for w in warnings:
            print(f"- {w}")


if __name__ == "__main__":
    main()
