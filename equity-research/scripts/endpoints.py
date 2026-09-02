#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""endpoints.py — 全部外部接口的 URL 模板、字段映射、超时与 UA 集中配置。

为什么有这个文件：
本 skill 的采集脚本依赖腾讯/东方财富/巨潮的公开非官方接口，这些接口可能
随时变动（URL、字段名、缩放规则）。接口变动时**只需要改这一个文件**，
不用动任何采集逻辑。

发现接口失效（selfcheck.py 报错）时的排查顺序：
1. 用浏览器/curl 手动访问下方对应 URL，确认是 URL 失效还是字段变化；
2. 若是字段变化，修改本文件中的字段映射常量；
3. 若是整个接口下线，到 GitHub Issues 查看是否已有修复，或提交 issue。

所有接口均为公开网页接口，与相关公司无任何隶属关系，不保证长期可用。
"""
from urllib.parse import quote

# 公共请求头（部分接口无 UA 会拒绝服务）
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# 超时（秒）
TIMEOUT_QUOTE = 10       # 行情快照
TIMEOUT_DATACENTER = 30  # 东财 datacenter（财务/F10）
TIMEOUT_VALUATION = 60   # 估值长序列

# ---------------------------------------------------------------- 腾讯行情
# 返回 GBK 编码的 v_sh600519="1~贵州茅台~600519~..." 按 ~ 分隔的字段串。
# 关键字段位置（0 基）：1=名称 3=现价 39=PE(TTM) 44=流通市值(亿) 45=总市值(亿) 46=PB 30=行情时间
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={sym}"  # sym 为小写，如 sh600519

# ---------------------------------------------------------------- 东方财富 push2 实时行情
# secid: 沪市 1.{code}，深市 0.{code}；f43/f163/f167 为实际值×100；f116/f117 单位元
EM_PUSH2_URL = "https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"
EM_PUSH2_FIELDS = "f43,f57,f58,f116,f117,f163,f167"

# ---------------------------------------------------------------- 东方财富 datacenter（财务序列）
EM_DATACENTER_BASE = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
# F10 财务三张表 reportName
EM_RPT_MAIN = "RPT_F10_FINANCE_MAINFINADATA"   # 主要指标（含同比、毛利率、ROE）
EM_RPT_BALANCE = "RPT_F10_FINANCE_GBALANCE"    # 资产负债表
EM_RPT_CASHFLOW = "RPT_F10_FINANCE_GCASHFLOW"  # 现金流量表
# 估值日频序列 reportName（PE_TTM / PB_MRQ）
EM_RPT_VALUATION = "RPT_VALUEANALYSIS_DET"


def em_datacenter_url(report, secucode, page_size=12, report_type="年报",
                      columns="ALL", sort="REPORT_DATE", client="HSF10", source="HSF10"):
    """拼东财 datacenter 查询 URL。secucode 形如 600519.SH。"""
    rt = quote(report_type)
    filt = f"(SECUCODE%3D%22{secucode}%22)"
    if report_type:
        filt += f"(REPORT_TYPE%3D%22{rt}%22)"
    return (f"{EM_DATACENTER_BASE}?reportName={report}&columns={columns}"
            f"&filter={filt}&pageNumber=1&pageSize={page_size}"
            f"&sortTypes=-1&sortColumns={sort}&source={source}&client={client}")


def em_valuation_url(secucode, max_rows=2600):
    """估值日频序列 URL（约 10 年交易日）。"""
    return (f"{EM_DATACENTER_BASE}?reportName={EM_RPT_VALUATION}"
            f"&columns=TRADE_DATE,PE_TTM,PB_MRQ"
            f"&filter=(SECUCODE%3D%22{secucode}%22)&pageNumber=1&pageSize={max_rows}"
            f"&sortTypes=-1&sortColumns=TRADE_DATE&source=WEB&client=WEB")


# ---------------------------------------------------------------- 东方财富 emweb F10 分节
# code 形如 SH600519；纯 GET JSON
EM_EMWEB_F10 = "https://emweb.securities.eastmoney.com/PC_HSF10/{section}/PageAjax?code={code}"

# ---------------------------------------------------------------- 巨潮资讯网（公告定位）
CNINFO_TOPSEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
CNINFO_ANNOUNCE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
