#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pe_percentile.py — 拉取东方财富个股估值日频序列，计算当前 PE/PB 历史分位。

用法:
    python3 pe_percentile.py 600519.SH           # 默认输出人类可读摘要
    python3 pe_percentile.py 600519.SH --json    # 输出完整机器可读 JSON

输出约定（本 skill 全部采集脚本统一）：
    默认打印人类可读摘要；加 --json 时输出完整机器可读 JSON。

接口 URL / UA / 超时集中配置在同目录 endpoints.py，本文件不硬编码任何 URL。
仅标准库。
"""
import json
import sys
import urllib.request
from datetime import datetime

import endpoints


def fetch_all(secucode):
    """估值日频序列（约 10 年交易日），返回 [{TRADE_DATE, PE_TTM, PB_MRQ}, ...]。"""
    req = urllib.request.Request(endpoints.em_valuation_url(secucode),
                                 headers=endpoints.UA)
    with urllib.request.urlopen(req, timeout=endpoints.TIMEOUT_VALUATION) as r:
        d = json.load(r)
    return (d.get("result") or {}).get("data") or []


def pct_rank(series, cur):
    """当前值在序列中的百分位（≤当前值的样本占比，%）。"""
    below = sum(1 for v in series if v <= cur)
    return below / len(series) * 100


def series_stats(series, cur):
    """一组估值序列的分位统计。"""
    srt = sorted(series)
    return {
        "current": cur,
        "percentile": round(pct_rank(series, cur), 1),
        "min": round(srt[0], 2),
        "median": round(srt[len(srt) // 2], 2),
        "max": round(srt[-1], 2),
    }


def analyze(secucode):
    """主流程，返回结构化结果 dict。"""
    rows = fetch_all(secucode)
    if not rows:
        raise RuntimeError(f"估值接口返回为空: {secucode}")
    pes = [r["PE_TTM"] for r in rows if r.get("PE_TTM") and 0 < r["PE_TTM"] < 500]
    pbs = [r["PB_MRQ"] for r in rows if r.get("PB_MRQ") and r["PB_MRQ"] > 0]
    if not pes or not pbs:
        raise RuntimeError(f"估值序列无有效样本: {secucode}")
    cur_pe, cur_pb = pes[0], pbs[0]
    result = {
        "ok": True,
        "secucode": secucode,
        "source": "datacenter.eastmoney.com RPT_VALUEANALYSIS_DET",
        "span": f"{rows[-1]['TRADE_DATE'][:10]} ~ {rows[0]['TRADE_DATE'][:10]}",
        "trading_days": len(pes),
        "pe_ttm": series_stats(pes, cur_pe),
        "pb": series_stats(pbs, cur_pb),
        "accessed_at": datetime.now().isoformat(timespec="seconds"),
    }
    # 近5年（约1250个交易日）/全样本 PE 分位
    for days, key in [(1250, "pe_percentile_5y"), (2500, "pe_percentile_all")]:
        if len(pes) > days:
            result[key] = round(pct_rank(pes[:days], cur_pe), 1)
    return result


def print_summary(r):
    print(f"估值分位 — {r['secucode']} 样本区间 {r['span']} 共{r['trading_days']}个交易日")
    for name, s in [("PE_TTM", r["pe_ttm"]), ("PB", r["pb"])]:
        print(f"  {name}: 当前{s['current']:.2f} | 分位{s['percentile']:.0f}%"
              f" | 最低{s['min']:.1f} 中位{s['median']:.1f} 最高{s['max']:.1f}")
    for key, label in [("pe_percentile_5y", "近5年"), ("pe_percentile_all", "全样本")]:
        if key in r:
            print(f"  PE {label}分位: {r[key]:.0f}%")
    print(f"  数据来源: {r['source']}；访问时间: {r['accessed_at']}")


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    if not args:
        print(__doc__)
        sys.exit(2)
    result = analyze(args[0])
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)


if __name__ == "__main__":
    main()
