# Provider 接口约定（第三方数据插件适配层）

本目录为**第三方行情/财务数据源插件**预留的接口。内置采集脚本（`fetch_quote.py` /
`collect_f10.py` / `pe_percentile.py` / `f10_sections.py`）走的是腾讯/东财/巨潮的公开
非官方接口，可能限流或失效；如果你手里有正式数据服务（iFinD / Tushare / akshare /
Wind 等），可以实现本接口替换内置数据源。

## 启用方式

1. 复制 `template_provider.py` 为 **`scripts/providers/active.py`**；
2. 实现其中四个函数（可只实现一部分，见下方降级约定）；
3. 文件名必须是 `active.py`——agent 流程发现该文件存在即优先调用，否则走内置脚本。

注意：采集脚本本身**不做自动 import 探测**，本接口只在文档层约定，由 agent 流程
（SKILL.md 的研究步骤）负责"有 active.py 就调它、失败再降级到内置脚本"。
保持脚本简单是本 skill 的明确取舍。

## 函数接口

四个函数，输入均为字符串代码，返回值均为 **dict**（与内置脚本的 JSON 输出结构一致，
可直接喂给下游 calc.py / dcf.py / 报告写作步骤）。

### `get_quote(code) -> dict`

- 输入：`code` — 6 位代码或带交易所前缀，如 `"600519"` / `"SH600519"`。
- 返回：与 `fetch_quote.py --json` 相同的结构：

  ```json
  {"ok": true, "source": "tushare", "symbol": "sh600519", "name": "贵州茅台",
   "price": 1500.0, "pe_ttm": 22.0, "pb": 7.5,
   "float_mcap_yi": 18000.0, "total_mcap_yi": 18000.0,
   "quote_time": "...", "accessed_at": "ISO8601"}
  ```

  单位约定：价格元、市值亿元、PE/PB 倍数。`source` 填你的数据源名。

### `get_financials(secucode) -> dict`

- 输入：`secucode` — 形如 `"600519.SH"`。
- 返回：与 `collect_f10.py` 输出文件相同的结构（calc.py 直接可吃）：

  ```json
  {"company": "...", "code": "600519.SH", "unit": "亿元", "currency": "CNY",
   "_meta": {...}, "years": [{"year": 2024, "revenue": ..., "net_profit": ..., ...}]}
  ```

  **金额字段必须是亿元**（calc.py 的输入约定），`year` 为 int，年份数 ≥2。
  字段清单见 `collect_f10.py` 顶部的映射表（MAIN_FIELDS / BALANCE_FIELDS /
  CASHFLOW_FIELDS）与 `scripts/examples/financials_example.json`。

### `get_valuation_series(secucode) -> dict`

- 输入：`secucode` — 形如 `"600519.SH"`。
- 返回：与 `pe_percentile.py --json` 相同的结构：

  ```json
  {"ok": true, "secucode": "600519.SH", "span": "2015-01-01 ~ 2026-09-01",
   "trading_days": 2600,
   "pe_ttm": {"current": 22.0, "percentile": 35.0, "min": 9.0, "median": 28.0, "max": 60.0},
   "pb": {"current": 7.5, "percentile": 40.0, "min": 3.0, "median": 8.0, "max": 15.0}}
  ```

### `get_f10_sections(code) -> dict`

- 输入：`code` — 形如 `"SH600519"`。
- 返回：与 `f10_sections.py --json` 相同的结构：

  ```json
  {"ok": true, "code": "SH600519",
   "business_breakdown": {"report_date": "2025-12-31", "unit": "亿元",
                          "segments": [{"category": "按产品", "item": "...", "income_yi": 0.0,
                                        "income_ratio_percent": 0.0, "gross_margin_percent": 0.0}]},
   "top10_holders": {"end_date": "2025-12-31", "unit": "亿股",
                     "holders": [{"name": "...", "hold_num_yi": 0.0, "hold_ratio": 0.0}]}}
  ```

## 错误约定

- **抛异常即视为失败**。不要返回 `{"ok": false}` 或部分填充的 dict——agent 流程
  捕获异常后走内置降级链（内置脚本→网页采集）。
- 未实现的函数保留 `raise NotImplementedError`；只实现了部分函数的 provider 是合法的，
  未实现的部分会自动走内置通道。
- 数据源的 token / 账号从环境变量读取，**不要把密钥写进代码**。

## 可适配的数据源示例

| 数据源 | 接入方式 | 备注 |
|---|---|---|
| iFinD（同花顺） | `iFinDPy` SDK | 机构终端，字段全 |
| Tushare | `tushare` pip 包 + token | 积分制，财务三表/行情齐全 |
| akshare | `akshare` pip 包 | 免费，本质是各公开接口的封装 |
| Wind（万得） | `WindPy` SDK | 机构终端 |

这些 SDK 都不是标准库，需要用户自行安装——这正是它们放在 provider 层而不是
内置脚本里的原因（内置脚本全部仅标准库）。
