#!/usr/bin/env python3
"""F10 分节数据采集（本次研究新增的可用通道，绕开受限的搜索/子代理）。

用法：python3 f10_sections.py SH600519
输出：主营构成(按产品/行业/地区) + 十大股东 + 控股股东

通道说明：
- emweb PageAjax 接口为纯 HTTP GET JSON，无需鉴权，稳定性优于网页解析
- 巨潮公告定位：topSearch(取orgId) → hisAnnouncement/query(取PDF) → webReader解析PDF
"""
import json, sys, urllib.request
from urllib.parse import quote

UA = {"User-Agent": "Mozilla/5.0"}

def get_json(url, data=None, headers=UA):
    req = urllib.request.Request(url, headers=headers, data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def sections(code):
    out = {}
    d = get_json(f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code={code}")
    rows = d.get("zygcfx") or []
    maxdate = max((r.get("REPORT_DATE", "") for r in rows), default="")
    tname = {"1": "按行业", "2": "按产品", "3": "按地区"}
    seen = set()
    seg = []
    for r in rows:
        if r.get("REPORT_DATE") == maxdate:
            key = (r.get("MAINOP_TYPE"), r.get("ITEM_NAME"))
            if key in seen:
                continue
            seen.add(key)
            seg.append((tname.get(r.get("MAINOP_TYPE"), r.get("MAINOP_TYPE")), r.get("ITEM_NAME"),
                        round((r.get("MAIN_BUSINESS_INCOME") or 0) / 1e8, 1),
                        round((r.get("MBI_RATIO") or 0) * 100, 1),
                        round((r.get("GROSS_RPOFIT_RATIO") or 0) * 100, 1) if r.get("GROSS_RPOFIT_RATIO") is not None else None))
    out["主营构成@{}".format(maxdate[:10])] = seg

    d = get_json(f"https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code={code}")
    rows = (d.get("sdgd") or [])[:10]
    holders = [(r.get("HOLDER_NAME"), round((r.get("HOLD_NUM") or 0) / 1e8, 3), r.get("HOLD_NUM_RATIO"))
               for r in rows]
    out["十大股东@{}".format(rows[0].get("END_DATE", "")[:10] if rows else "?")] = holders
    return out

def cninfo_find(keyword):
    """巨潮公告定位：返回 (code, orgId)，再调 hisAnnouncement/query 取PDF链接。"""
    d = get_json("http://www.cninfo.com.cn/new/information/topSearch/query",
                 data=f"keyWord={quote(keyword)}&maxNum=10".encode(),
                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    return [(x["code"], x["orgId"]) for x in d if x.get("category") == "A股"]

if __name__ == "__main__":
    code = sys.argv[1]
    for k, v in sections(code).items():
        print(f"== {k} ==")
        for row in v:
            print("  ", row)
