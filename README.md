# equity-research-skill

> 给 AI Agent 用的上市公司基本面深度研究与估值分析技能（A 股为主）。
> 输入一家公司，产出**标准化、可验证、可复盘**的研究报告：公司概况、行业与同业、商业模式、财务质量、成长性、护城河、治理、估值（DCF + 相对估值 + 历史分位）、多空对照与结论映射。

[![selfcheck](https://github.com/OWNER/equity-research-skill/actions/workflows/selfcheck.yml/badge.svg)](../../actions/workflows/selfcheck.yml)

## 它解决什么问题

让任何支持 SKILL.md 规范的 AI Agent（Claude Code、Kimi、Cursor、Codex 等）具备纪律化的个股研究能力：

- **数据可验证**：关键数字必须带来源编号与 URL；禁止模型凭记忆写财务数据
- **计算可复现**：增长率/ROE/DCF 等一切计算由脚本完成，禁止心算
- **结论有纪律**：一票否决清单、70% 数据完备率门槛、质量分 × 安全边际的结论映射（🟢/🟡/🔴）
- **零配置可用**：采集脚本仅依赖 Python 标准库 + 公开免鉴权接口，不需要任何付费终端

## 30 秒上手

```bash
# 1. 自检（离线校验计算引擎 + 在线校验四个数据接口）
python3 equity-research/scripts/selfcheck.py

# 2. 把 equity-research/ 目录装入你的 Agent 技能目录，然后对它说：
#    "深度研究 600519 值不值得长期投资"
```

Agent 会按 SKILL.md 的九步流程执行：标的确认 → 数据采集（四个脚本）→ 核验 → 指标计算 → 九大模块分析 → DCF 估值 → 多空对照 → 评分 → 报告。

**示例产出**：[examples/report_600519.md](examples/report_600519.md) —— 贵州茅台完整研究报告（真实数据采集 + 结构演示）。

## 两种模式

| | 快速筛选 | 深度研究（默认） |
|---|---|---|
| 触发 | "快速看看XX" | "分析XX""XX值不值得长期投资" |
| 输出 | 一页纸 + 🟢/🟡/🔴 | 完整报告 + 质量分 + 估值区间 |

## 目录结构

```
equity-research/          # skill 本体
├── SKILL.md              # 触发条件、九步工作流、数据硬规则、评分与结论映射
├── references/           # 数据源 SOP / 分析模块细则 / 估值方法 / 报告模板
└── scripts/              # 仅标准库，无需 pip install
    ├── endpoints.py      # ★ 所有外部接口 URL/字段集中配置（接口失效只改这里）
    ├── fetch_quote.py    # 行情/PE/PB/市值快照
    ├── collect_f10.py    # 12 年财务三表序列（亿元口径，calc 就绪）
    ├── pe_percentile.py  # PE/PB 历史分位
    ├── f10_sections.py   # 主营构成 + 十大股东
    ├── calc.py           # 增长/ROE/杜邦/FCF/偿债 + 自动红旗
    ├── dcf.py            # 三情景 DCF + 敏感性矩阵
    ├── selfcheck.py      # 自检（--offline 跳过网络检查）
    ├── providers/        # 数据 Provider 适配层（接入 iFinD/Tushare/akshare/Wind）
    └── examples/         # 输入样例 + expected output（供 diff 验证）
examples/report_600519.md # 真实数据跑出的示例研究报告
```

## 数据源与局限

- 采集基于东方财富/腾讯/巨潮的**公开非官方接口**，免鉴权但可能变动
- 接口失效怎么办：`selfcheck.py` 定位故障 → 改 `scripts/endpoints.py` 一处即可 → 或到 [Issues](../../issues) 查看/报告（有每周自动巡检，见下）
- 内置脚本覆盖沪深 A 股；北交所/港股/美股有手动采集 SOP（见 `references/data-sources.md`）
- 有付费终端？实现 `scripts/providers/provider_interface.md` 的四个函数，存为 `scripts/providers/active.py` 即可让 skill 优先走你的数据源（iFinD/Tushare/akshare/Wind 均可适配）

## 与付费终端方案对比

| | 本 skill | 专业终端插件（Wind/iFinD 等） |
|---|---|---|
| 成本 | 免费 | 需要终端账号 |
| 数据稳定性 | 公开接口，尽力而为 | 官方接口，稳定互备 |
| 适用 | 个人投资者、开源社区、离线环境 | 机构级日常研究 |
| 研究纪律 | 内置（硬规则 + 一票否决） | 取决于上层流程 |

## 输出约定

- 采集类脚本：默认人类可读摘要，`--json` 输出机器可读 JSON（`collect_f10.py` 直接写 JSON 文件）
- 计算类脚本（calc/dcf）：默认 markdown 报告，`--json` 输出 JSON
- 报告：关键数字带来源编号 `[n]`，全篇标注【事实】【计算】【判断】【假设】【结论】

## 运维：接口巡检

`.github/workflows/selfcheck.yml` 每周自动运行 `selfcheck.py`，接口失效时自动开 Issue 报警。Fork 后无需任何配置即可生效。

## 贡献

- 报告接口失效：先跑 `selfcheck.py`，把 ❌ 项贴进 Issue
- 贡献 Provider：按 `scripts/providers/provider_interface.md` 实现接口并发 PR
- 数据纪律 PR 要求：任何代码路径不得引入"无来源数据"

## 免责声明

本项目不构成任何投资建议。数据来自公开网页接口，可能存在错误或滞后，请以官方披露为准，独立判断、自担风险。详见 [LICENSE](LICENSE)。

## License

[MIT](LICENSE)

---

## English Summary

**equity-research-skill** is an agent skill (SKILL.md convention) for disciplined fundamental research on listed companies (China A-shares primarily). It turns any SKILL.md-compatible AI agent into an equity analyst: mandatory source citations, script-only calculations (no mental math), a 9-step workflow, one-vote veto checks, a 70% data-completeness gate, and a quality-score × safety-margin conclusion mapping (🟢/🟡/🔴). Collection scripts use only the Python standard library plus free public endpoints — zero credentials required. Paid data terminals (iFinD/Tushare/akshare/Wind) can be plugged in via `scripts/providers/`. See `equity-research/SKILL.md` (Chinese) for the full workflow. MIT licensed; not investment advice.
