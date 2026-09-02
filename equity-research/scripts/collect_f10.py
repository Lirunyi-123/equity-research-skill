#!/usr/bin/env python3
"""从东方财富 F10 接口采集主要财务指标+资产负债表+现金流量表，输出 calc.py 需要的 JSON。"""
import json, sys, urllib.request
from urllib.parse import quote

BASE = "https://datacenter.eastmoney.com/securities/api/data/v1/get"

def fetch(report, secucode, page_size=12, report_type="年报"):
    rt = quote(report_type)
    url = (f"{BASE}?reportName={report}&columns=ALL"
           f"&filter=(SECUCODE%3D%22{secucode}%22)(REPORT_TYPE%3D%22{rt}%22)"
           f"&pageNumber=1&pageSize={page_size}&sortTypes=-1&sortColumns=REPORT_DATE"
           f"&source=HSF10&client=PC")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    return (d.get("result") or {}).get("data") or []

def collect(secucode):
    main = fetch("RPT_F10_FINANCE_MAINFINADATA", secucode)
    bal = fetch("RPT_F10_FINANCE_GBALANCE", secucode)
    cf = fetch("RPT_F10_FINANCE_GCASHFLOW", secucode)
    bal_m, cf_m = {}, {}
    for r in bal: bal_m[r["REPORT_DATE"][:4]] = r
    for r in cf: cf_m[r["REPORT_DATE"][:4]] = r
    years = []
    for r in main:
        y = r["REPORT_DATE"][:4]
        b, c = bal_m.get(y, {}), cf_m.get(y, {})
        years.append({
            "year": int(y),
            "revenue": r.get("TOTALOPERATEREVE"),
            "net_profit": r.get("PARENTNETPROFIT"),
            "deduct_net_profit": r.get("KCFJCXSYJLR"),
            "gross_margin_percent": r.get("XSMLL"),
            "net_margin_percent": r.get("XSJLL"),
            "roe_percent": r.get("ROEJQ"),
            "operating_cash_flow": r.get("NETCASH_OPERATE_PK"),
            "capex": c.get("CONSTRUCT_LONG_ASSET"),
            "total_assets": b.get("TOTAL_ASSETS"),
            "total_liabilities": b.get("TOTAL_LIABILITIES"),
            "interest_bearing_debt": (b.get("SHORT_LOAN") or 0) + (b.get("LONG_LOAN") or 0)
                                      + (b.get("BOND_PAYABLE") or 0) + (b.get("NONCURRENT_LIAB_1YEAR") or 0),
            "equity": b.get("TOTAL_PARENT_EQUITY"),
            "goodwill": b.get("GOODWILL"),
            "inventory": b.get("INVENTORY"),
            "accounts_receivable": b.get("ACCOUNTS_RECEIVE"),
            "rev_yoy": r.get("TOTALOPERATEREVETZ"),
            "np_yoy": r.get("PARENTNETPROFITTZ"),
            "deduct_yoy": r.get("KCFJCXSYJLRTZ"),
            "ocf_yoy": r.get("JYXJLYYSR"),
        })
    return years

if __name__ == "__main__":
    secucode = sys.argv[1]
    out = sys.argv[2]
    data = collect(secucode)
    with open(out, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"saved {len(data)} annual rows -> {out}")
    for y in data:
        print(y["year"], round((y["revenue"] or 0)/1e8,1), round((y["net_profit"] or 0)/1e8,1),
              y["rev_yoy"], y["np_yoy"], y["roe_percent"])
