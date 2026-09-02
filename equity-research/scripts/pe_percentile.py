#!/usr/bin/env python3
"""拉取东方财富个股估值日频序列，计算当前PE/PB在历史中的分位。"""
import json, sys, urllib.request
from urllib.parse import quote

def fetch_all(secucode, max_rows=2600):
    url = (f"https://datacenter.eastmoney.com/securities/api/data/v1/get"
           f"?reportName=RPT_VALUEANALYSIS_DET&columns=TRADE_DATE,PE_TTM,PB_MRQ"
           f"&filter=(SECUCODE%3D%22{secucode}%22)&pageNumber=1&pageSize={max_rows}"
           f"&sortTypes=-1&sortColumns=TRADE_DATE&source=WEB&client=WEB")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    return (d.get("result") or {}).get("data") or []

def pct_rank(series, cur):
    below = sum(1 for v in series if v <= cur)
    return below / len(series) * 100

if __name__ == "__main__":
    secucode = sys.argv[1]
    rows = fetch_all(secucode)
    pes = [r["PE_TTM"] for r in rows if r.get("PE_TTM") and 0 < r["PE_TTM"] < 500]
    pbs = [r["PB_MRQ"] for r in rows if r.get("PB_MRQ") and r["PB_MRQ"] > 0]
    cur_pe, cur_pb = pes[0], pbs[0]
    span = f"{rows[-1]['TRADE_DATE'][:10]} ~ {rows[0]['TRADE_DATE'][:10]}"
    print(f"{secucode} 样本区间 {span} 共{len(pes)}个交易日")
    for name, s, cur in [("PE_TTM", pes, cur_pe), ("PB", pbs, cur_pb)]:
        srt = sorted(s)
        print(f"  {name}: 当前{cur:.2f} | 分位{pct_rank(s, cur):.0f}% | 最低{srt[0]:.1f} 中位{srt[len(srt)//2]:.1f} 最高{srt[-1]:.1f}")
    # 近5年分位
    for years, label in [(1250, "近5年"), (2500, "全样本")]:
        if len(pes) > years:
            p5 = pes[:years]
            print(f"  PE {label}分位: {pct_rank(p5, cur_pe):.0f}%")
