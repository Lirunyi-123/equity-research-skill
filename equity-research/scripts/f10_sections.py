#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f10_sections.py — F10 分节数据采集（绕开受限的搜索/子代理的可用通道）。

用法:
    python3 f10_sections.py SH600519           # 默认输出人类可读摘要
    python3 f10_sections.py SH600519 --json    # 输出完整机器可读 JSON

输出约定（本 skill 全部采集脚本统一）：
    默认打印人类可读摘要；加 --json 时输出完整机器可读 JSON。

内容：主营构成(按产品/行业/地区，最新报告期) + 十大股东。

通道说明：
- emweb PageAjax 接口为纯 HTTP GET JSON，无需鉴权，稳定性优于网页解析
- 巨潮公告定位：topSearch(取orgId) → hisAnnouncement/query(取PDF) → webReader解析PDF
  （cninfo_find 为公告定位辅助函数，主流程不使用）

接口 URL / UA / 超时集中配置在同目录 endpoints.py，本文件不硬编码任何 URL。
仅标准库。
"""
import gzip
import json
import sys
import urllib.request
from datetime import datetime
from urllib.parse import quote

import endpoints


def get_json(url, data=None, headers=None):
    req = urllib.request.Request(url, headers=headers or endpoints.UA, data=data)
    with urllib.request.urlopen(req, timeout=endpoints.TIMEOUT_DATACENTER) as r:
        raw = r.read()
    # emweb 有时返回 gzip 压缩体（响应头未声明 Content-Encoding 时也要兜底）
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8", "ignore"))


def sections(code):
    """采集主营构成 + 十大股东。code 形如 SH600519。返回结构化 dict。"""
    out = {"ok": True, "code": code,
           "source": "emweb.securities.eastmoney.com PC_HSF10 PageAjax",
           "accessed_at": datetime.now().isoformat(timespec="seconds")}

    # ---- 主营构成（最新报告期，按行业/产品/地区）----
    d = get_json(endpoints.EM_EMWEB_F10.format(section="BusinessAnalysis", code=code))
    rows = d.get("zygcfx") or []
    maxdate = max((r.get("REPORT_DATE", "") for r in rows), default="")
    tname = {"1": "按行业", "2": "按产品", "3": "按地区"}
    seen = set()
    seg = []
    for r in rows:
        if r.get("REPORT_DATE") != maxdate:
            continue
        key = (r.get("MAINOP_TYPE"), r.get("ITEM_NAME"))
        if key in seen:
            continue
        seen.add(key)
        seg.append({
            "category": tname.get(r.get("MAINOP_TYPE"), r.get("MAINOP_TYPE")),
            "item": r.get("ITEM_NAME"),
            "income_yi": round((r.get("MAIN_BUSINESS_INCOME") or 0) / 1e8, 1),  # 亿元
            "income_ratio_percent": round((r.get("MBI_RATIO") or 0) * 100, 1),
            "gross_margin_percent": (round(r["GROSS_RPOFIT_RATIO"] * 100, 1)
                                     if r.get("GROSS_RPOFIT_RATIO") is not None else None),
        })
    out["business_breakdown"] = {"report_date": maxdate[:10], "unit": "亿元", "segments": seg}

    # ---- 十大股东 ----
    d = get_json(endpoints.EM_EMWEB_F10.format(section="ShareholderResearch", code=code))
    rows = (d.get("sdgd") or [])[:10]
    holders = [{
        "name": r.get("HOLDER_NAME"),
        "hold_num_yi": round((r.get("HOLD_NUM") or 0) / 1e8, 3),  # 亿股
        "hold_ratio": r.get("HOLD_NUM_RATIO"),
    } for r in rows]
    out["top10_holders"] = {
        "end_date": rows[0].get("END_DATE", "")[:10] if rows else None,
        "unit": "亿股",
        "holders": holders,
    }
    return out


def cninfo_find(keyword):
    """巨潮公告定位：返回 (code, orgId)，再调 hisAnnouncement/query 取PDF链接。"""
    d = get_json(endpoints.CNINFO_TOPSEARCH_URL,
                 data=f"keyWord={quote(keyword)}&maxNum=10".encode(),
                 headers={**endpoints.UA,
                          "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    return [(x["code"], x["orgId"]) for x in d if x.get("category") == "A股"]


def print_summary(out):
    bd = out["business_breakdown"]
    print(f"== 主营构成@{bd['report_date']}（亿元） ==")
    for s in bd["segments"]:
        gm = "-" if s["gross_margin_percent"] is None else f"{s['gross_margin_percent']}%"
        print(f"   {s['category']} | {s['item']} | 收入{s['income_yi']}亿"
              f" | 占比{s['income_ratio_percent']}% | 毛利率{gm}")
    th = out["top10_holders"]
    print(f"== 十大股东@{th['end_date']}（亿股） ==")
    for h in th["holders"]:
        print(f"   {h['name']} | {h['hold_num_yi']}亿股 | {h['hold_ratio']}%")
    print(f"== 数据来源: {out['source']}；访问时间: {out['accessed_at']} ==")


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    if not args:
        print(__doc__)
        sys.exit(2)
    result = sections(args[0])
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)


if __name__ == "__main__":
    main()
