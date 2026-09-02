#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""template_provider.py — 第三方数据源 Provider 模板。

启用方式：
1. 复制本文件为 scripts/providers/active.py；
2. 按需实现下面四个函数（可只实现一部分，未实现的保留 NotImplementedError，
   agent 流程会对该部分自动降级到内置脚本）；
3. 接口细节（返回结构、单位、错误约定）见同目录 provider_interface.md。

错误约定：失败一律抛异常（不要返回 ok=False 的 dict），agent 流程捕获后走降级链。
密钥从环境变量读取，不要写进代码。
"""

# 示例：从环境变量取 token（以 Tushare 为例）
# import os
# TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN")


def get_quote(code):
    """行情快照。输入 "600519"/"SH600519"，返回结构见 provider_interface.md。

    实现指引：
    - 调用你的数据源 SDK 取现价/PE(TTM)/PB/总市值/流通市值；
    - 市值换算成亿元，PE/PB 为倍数；
    - source 字段填数据源名，便于报告里标注来源编号。
    """
    raise NotImplementedError("请实现 get_quote：行情快照，结构同 fetch_quote.py --json 输出")


def get_financials(secucode):
    """年报财务三表。输入 "600519.SH"，返回结构同 collect_f10.py 输出文件。

    实现指引：
    - 字段清单见 collect_f10.py 顶部的 MAIN_FIELDS / BALANCE_FIELDS / CASHFLOW_FIELDS；
    - 所有金额字段必须是亿元（calc.py 的输入约定），比率/同比字段为百分数；
    - years 至少 2 个年度，按任意顺序均可（calc.py 会自行按 year 排序）。
    """
    raise NotImplementedError("请实现 get_financials：财务三表，结构同 collect_f10.py 输出")


def get_valuation_series(secucode):
    """估值日频序列分位。输入 "600519.SH"，返回结构同 pe_percentile.py --json 输出。

    实现指引：
    - 需要约 10 年（≥2500 个交易日）的 PE_TTM/PB_MRQ 日频序列；
    - percentile = 序列中 ≤ 当前值的样本占比（%），见 pe_percentile.pct_rank。
    """
    raise NotImplementedError("请实现 get_valuation_series：估值序列，结构同 pe_percentile.py --json 输出")


def get_f10_sections(code):
    """F10 分节（主营构成 + 十大股东）。输入 "SH600519"，返回结构同 f10_sections.py --json 输出。

    实现指引：
    - 主营构成按最新报告期，分行业/产品/地区三类，金额亿元、比率百分数；
    - 十大股东持股数量单位为亿股。
    """
    raise NotImplementedError("请实现 get_f10_sections：F10 分节，结构同 f10_sections.py --json 输出")
