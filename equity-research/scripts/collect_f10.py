#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""collect_f10.py — 从东方财富 F10 接口采集年报财务三表，输出 calc.py 可直接消费的 JSON。

用法:
    python3 collect_f10.py 600519.SH out.json

输出约定（本 skill 全部采集脚本统一）：
    本脚本的职责就是生成机器可读 JSON 文件（供 calc.py / dcf.py 消费），
    因此没有 --json 开关；stdout 固定打印逐年人类可读摘要。

输出 JSON 结构：
    {"company": str, "code": str, "unit": "亿元", "currency": "CNY",
     "_meta": {...}, "years": [{...}, ...]}
    - 所有金额字段已统一除以 1e8 转为 **亿元**（与 examples/financials_example.json
      的 calc.py 输入约定一致；历史版本直接输出原始单位"元"，属 bug，已修正）；
    - *_percent / *_yoy 字段保持接口原值（百分数）；
    - calc.py 通过 data.get("years") 读取年份数组，天然兼容。

接口 URL / reportName / UA / 超时集中配置在同目录 endpoints.py，本文件不硬编码任何 URL。
仅标准库。
"""
import json
import sys
import urllib.request
from datetime import datetime

import endpoints

# ------------------------------------------------------------------ 字段映射表
# 东财原始字段名 → (输出字段名, 中文含义, 是否金额字段)
# 金额字段（is_amount=True）输出时除以 1e8 转亿元；比率/同比字段保持原值。
# 口径：三张表均为合并报表年报（REPORT_TYPE=年报，见 endpoints.em_datacenter_url）。
MAIN_FIELDS = {  # RPT_F10_FINANCE_MAINFINADATA（主要指标）
    "TOTALOPERATEREVE":  ("revenue",             "营业总收入", True),
    "PARENTNETPROFIT":   ("net_profit",          "归母净利润", True),
    "KCFJCXSYJLR":       ("deduct_net_profit",   "扣非净利润", True),
    "XSMLL":             ("gross_margin_percent", "销售毛利率(%)", False),
    "XSJLL":             ("net_margin_percent",   "销售净利率(%)", False),
    "ROEJQ":             ("roe_percent",          "ROE加权(%)", False),
    "NETCASH_OPERATE_PK": ("operating_cash_flow", "经营活动现金流净额", True),
    "TOTALOPERATEREVETZ": ("rev_yoy",             "营收同比(%)", False),
    "PARENTNETPROFITTZ":  ("np_yoy",              "归母净利同比(%)", False),
    "KCFJCXSYJLRTZ":      ("deduct_yoy",          "扣非净利同比(%)", False),
    "JYXJLYYSR":          ("ocf_yoy",             "经营现金流同比(%)", False),
}
BALANCE_FIELDS = {  # RPT_F10_FINANCE_GBALANCE（资产负债表）
    "TOTAL_ASSETS":        ("total_assets",        "资产总计", True),
    "TOTAL_LIABILITIES":   ("total_liabilities",   "负债合计", True),
    "TOTAL_PARENT_EQUITY": ("equity",              "归母股东权益", True),
    "GOODWILL":            ("goodwill",            "商誉", True),
    "INVENTORY":           ("inventory",           "存货", True),
    "ACCOUNTS_RECEIVE":    ("accounts_receivable", "应收账款", True),
}
CASHFLOW_FIELDS = {  # RPT_F10_FINANCE_GCASHFLOW（现金流量表）
    "CONSTRUCT_LONG_ASSET": ("capex", "购建固定资产等支付的现金（资本开支）", True),
}
# 有息负债 = 短期借款+长期借款+应付债券+一年内到期的非流动负债（四项求和，亿元）
DEBT_PARTS = ("SHORT_LOAN", "LONG_LOAN", "BOND_PAYABLE", "NONCURRENT_LIAB_1YEAR")


def fetch(report, secucode, page_size=12):
    """拉一张 F10 年报数据表（合并报表），返回原始行列表。"""
    url = endpoints.em_datacenter_url(report, secucode, page_size=page_size)
    req = urllib.request.Request(url, headers=endpoints.UA)
    with urllib.request.urlopen(req, timeout=endpoints.TIMEOUT_DATACENTER) as r:
        d = json.load(r)
    return (d.get("result") or {}).get("data") or []


def yi(v):
    """金额原始单位（元）→ 亿元；非数值/空值原样透传。"""
    return v / 1e8 if isinstance(v, (int, float)) else None


def collect(secucode):
    """采集三张表并合并成 calc.py 输入结构（金额单位：亿元）。"""
    main = fetch(endpoints.EM_RPT_MAIN, secucode)
    bal = fetch(endpoints.EM_RPT_BALANCE, secucode)
    cf = fetch(endpoints.EM_RPT_CASHFLOW, secucode)
    # 资产负债表/现金流量表按年份建索引（REPORT_DATE 前4位为年度）
    bal_m = {r["REPORT_DATE"][:4]: r for r in bal}
    cf_m = {r["REPORT_DATE"][:4]: r for r in cf}

    years = []
    for r in main:
        y = r["REPORT_DATE"][:4]
        b, c = bal_m.get(y, {}), cf_m.get(y, {})
        row = {"year": int(y)}
        for src, table in ((r, MAIN_FIELDS), (b, BALANCE_FIELDS), (c, CASHFLOW_FIELDS)):
            for em_name, (out_name, _desc, is_amount) in table.items():
                v = src.get(em_name)
                row[out_name] = yi(v) if is_amount else v
        debt_raw = sum(b.get(k) or 0 for k in DEBT_PARTS)
        row["interest_bearing_debt"] = yi(debt_raw)
        years.append(row)

    company = main[0].get("SECURITY_NAME_ABBR") if main else None
    return {
        "company": company,
        "code": secucode,
        "unit": "亿元",
        "currency": "CNY",
        "_meta": build_meta(secucode),
        "years": years,
    }


def build_meta(secucode):
    """元信息：字段口径/单位、数据来源 URL、采集时间。"""
    fields = {}
    for table in (MAIN_FIELDS, BALANCE_FIELDS, CASHFLOW_FIELDS):
        for em_name, (out_name, desc, is_amount) in table.items():
            fields[out_name] = {
                "desc": desc,
                "source_field": em_name,
                "unit": "亿元" if is_amount else "%",
            }
    fields["interest_bearing_debt"] = {
        "desc": "有息负债=短期借款+长期借款+应付债券+一年内到期的非流动负债",
        "source_field": "+".join(DEBT_PARTS),
        "unit": "亿元",
    }
    return {
        "scope": "合并报表，年报（REPORT_TYPE=年报）",
        "amount_unit": "亿元（原始接口单位为元，已除以1e8）",
        "percent_unit": "%（接口原值）",
        "fields": fields,
        "source_urls": [
            endpoints.em_datacenter_url(endpoints.EM_RPT_MAIN, secucode),
            endpoints.em_datacenter_url(endpoints.EM_RPT_BALANCE, secucode),
            endpoints.em_datacenter_url(endpoints.EM_RPT_CASHFLOW, secucode),
        ],
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    secucode, out = sys.argv[1], sys.argv[2]
    data = collect(secucode)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    # 逐年人类可读摘要（金额已是亿元，无需再除）
    print(f"saved {len(data['years'])} annual rows -> {out}（单位: 亿元）")
    print("年份 | 营收 | 归母净利 | 营收同比% | 净利同比% | ROE%")
    for y in data["years"]:
        def r1(v):
            return "-" if v is None else round(v, 1)
        print(y["year"], r1(y["revenue"]), r1(y["net_profit"]),
              y["rev_yoy"], y["np_yoy"], y["roe_percent"])


if __name__ == "__main__":
    main()
