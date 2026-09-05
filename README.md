# Morning Brief Agent / 每日晨报 Agent

[中文说明](#中文说明) · [English](#english)

## 中文说明

一个可以持续扩展的个人晨报 Agent。当前版本包含美元兑人民币汇率晨报，以及面向基金 `006131` 的单基金实验模块。

项目采用混合工作流：Python 和工具负责获取、计算与校验确定性数据，OpenAI Agents SDK 调用硅基流动的 GLM-5.2 生成自然语言分析，Codex 定时任务负责运行项目并发送邮件。

### 当前功能

- 获取最近 14 个自然日内的有效 USD/CNY 数据
- 计算 20 美元需要多少人民币
- 判断今日汇率处于近期低位、中位还是高位
- 比较最近 3 个交易日与之前 3 个交易日，生成短期趋势信号
- 使用中国银行外汇牌价进行交叉验证
- Python 直接使用工具数据组装确定性字段，模型只生成自然语言理由
- 生成结构化 JSON 和 HTML 卡片邮件
- 由 Codex 定时任务通过已连接的 Gmail 发送

基金实验模块还支持：

- 安全刷新本地净值 CSV，候选数据未通过校验时保留原文件并阻止生成晨报
- 由 Python 计算近 5 日、近 20 日变化、区间位置和最大回撤
- 由 Agent 调用基金工具，Model 只解释已校验指标，Python 再校验三段解释职责
- 生成可在浏览器中查看的响应式基金 HTML 晨报

### 项目文档

- [基金晨报 MVP 定义](docs/fund_morning_brief_mvp.md)
- [基金指标概念与算法](docs/fund_metrics_guide.md)
- [基金晨报系统架构](docs/architecture.md)
- [基金晨报评测报告](docs/evaluation_report.md)
- [BC-001：过期数据仍输出指标](docs/BC-001.md)
- [BC-002：Tool 参数解析与诊断](docs/BC-002.md)
- [BC-003：测试静默失效](docs/BC-003.md)
- [ADR-001：延迟数据阻断决策](docs/ADR-001.md)

### 工作流程

```text
Codex 定时任务
    ↓
main.py
    ↓
OpenAI Agents SDK + 硅基流动 GLM-5.2
    ↓ 调用工具
Frankfurter API + 中国银行外汇牌价
    ↓
确定性计算与报告校验
    ↓
output/latest_report.json
    ↓
Gmail HTML 邮件
    ↓
delivery_log.py → logs/morning_brief.log
```

基金实验模块：

```text
fund_main.py 006131
    ↓
安全刷新并校验净值 CSV
    ↓
Python 计算确定性指标
    ↓
Agent 调用工具，Model 生成三段解释
    ↓
Python 校验解释并生成 output/fund_brief.html
```

### 项目结构

```text
morning_brief_agent/
├── main.py                       # 运行 Agent、校验并保存报告
├── email_template.py             # 生成 HTML 邮件卡片
├── logging_config.py             # 日志轮换和保留策略
├── delivery_log.py               # 记录 Gmail 投递结果
├── rate_agent.py                 # Agent、模型客户端、工具注册和输出结构
├── tools.py                      # 汇率获取、交叉验证和确定性计算
├── fund_metrics.py               # 基金数据校验和确定性指标计算
├── fund_data_probe.py            # 安全获取、校验并替换基金净值样例
├── fund_agent.py                 # 基金工具、Agent 指令和输出结构
├── fund_main.py                  # 运行基金 Agent 并生成正式 HTML
├── fund_html.py                  # 渲染基金 HTML 晨报
├── fund_preview.py               # 使用固定可信数据生成离线预览
├── data/                         # 基金样例数据与测试固件
├── docs/                         # MVP、指标说明等项目文档
├── LICENSE                       # MIT 许可证
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量示例
└── tests/                        # 不调用付费模型的本地测试
```

### 安装

建议使用 Python 3.11 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 配置

项目通过硅基流动的 OpenAI-compatible Chat Completions API 调用 `zai-org/GLM-5.2`：

- Base URL：`https://api.siliconflow.cn/v1`
- 密钥名称：`SILICONFLOW_API_KEY`

本地定时任务推荐使用项目根目录的 `.env`，只需配置一次：

```bash
cp .env.example .env
chmod 600 .env
```

然后在本地编辑 `.env`：

```text
SILICONFLOW_API_KEY=你的硅基流动API Key
```

程序会自动读取 `.env`。该文件已加入 `.gitignore`，不会提交到 GitHub。不要把文件内容或真实密钥发送给其他人。

也可以临时使用系统环境变量；系统环境变量存在时优先于 `.env`：

macOS / Linux：

```bash
export SILICONFLOW_API_KEY="你的硅基流动 API Key"
```

Windows PowerShell：

```powershell
$env:SILICONFLOW_API_KEY="你的硅基流动 API Key"
```

不要把 API Key 写进源码或提交到 GitHub。

### 运行与测试

```bash
python main.py
python -B fund_main.py 006131
python -B fund_preview.py
python -m unittest discover -s tests -v
```

汇率入口会生成 `output/latest_report.json`；基金正式入口会生成 `output/fund_brief.html`；离线预览会生成 `output/fund_brief_preview.html`。测试不会调用硅基流动或其他付费模型。

### 运行日志

完整运行链路记录在 `logs/morning_brief.log`：数据获取、模型调用、报告校验、文件保存以及 Gmail 投递结果。每次运行通过 `run_id` 关联，日志每天轮换并保留最近 14 天。

日志不会记录 API Key、Gmail Token、完整模型响应或完整邮件 HTML。`email_sent` 表示 Gmail 已发送成功，`email_failed` 表示发送失败；如果当天完全没有 `run_started`，说明本地定时任务没有启动。

### 判断规则

- 14 日有效数据排名最低 30%：现在充比较划算
- 中间 40%：差异不大，按需充值
- 最高 30%：当前偏贵，可以观察
- 最近 3 日均值相对之前 3 日变化超过 ±0.3%：标记短期上升或下降

趋势信号只描述近期历史变化，不是对未来汇率的预测。

### 基金实验模块的已知限制

- 基金数据新鲜度暂时按自然日判断，春节、国庆等长假可能把合法数据误判为延迟；正式版本应接入交易日历。
- 本地 CSV 会在正式运行前尝试安全刷新，但仍是实验数据样例，不代表实时行情；候选数据校验失败时不会覆盖原文件。
- 金融数值由 Python 校验和计算，Model 只解释已经通过校验的结构化结果，不自行修改数字。
- 延迟数据采用保守策略：返回 `delayed + blocked`，不生成正常指标，避免用户把旧数据当作最新情况。

### 定时运行说明

当前定时任务在本地 Codex 中运行。Mac 必须处于开机、未休眠、联网状态，Codex 也需要能够在后台运行；电脑关机或休眠时无法保证准时执行。Gmail 发送由 Codex 自动化负责，不在 Python 项目中直接保存 Gmail 凭据。

### 许可证

本项目使用 [MIT License](LICENSE)，版权所有 © 2026 KaiHua。

---

## English

An extensible personal morning brief agent. The current version includes a USD/CNY exchange-rate brief and an experimental single-fund workflow for fund `006131`.

The project uses a hybrid workflow: Python tools handle deterministic data retrieval, calculation, and validation; the OpenAI Agents SDK calls GLM-5.2 through SiliconFlow for natural-language analysis; a Codex automation runs the project and sends the email.

### Features

- Retrieves valid USD/CNY observations from the latest 14 calendar days
- Calculates the CNY cost of USD 20
- Classifies today's rate as relatively low, medium, or high
- Compares the latest three trading days with the previous three to produce a short-term trend signal
- Cross-checks the reference rate against Bank of China exchange rates
- Uses Python to assemble deterministic fields from tool data while the model only writes natural-language rationale
- Generates structured JSON and an HTML email card
- Supports delivery through a connected Gmail account using Codex automation

The fund experiment also:

- Safely refreshes the local NAV CSV and preserves the previous file when candidate data fails validation
- Uses Python to calculate 5-day and 20-day changes, range position, and maximum drawdown
- Uses an Agent tool call for verified metrics, limits the model to explanation, and validates the three narrative roles in Python
- Generates a responsive fund brief that can be opened in a browser

### Project Documentation

- [Fund Brief MVP Definition](docs/fund_morning_brief_mvp.md)
- [Fund Metrics Guide](docs/fund_metrics_guide.md)
- [Fund Brief Architecture](docs/architecture.md)
- [Fund Brief Evaluation Report](docs/evaluation_report.md)
- [BC-001: Stale Data Used as Current Metrics](docs/BC-001.md)
- [BC-002: Tool Argument Parsing and Diagnostics](docs/BC-002.md)
- [BC-003: Silently Disabled Tests](docs/BC-003.md)
- [ADR-001: Blocking Stale Fund Data](docs/ADR-001.md)

### Workflow

```text
Codex automation
    ↓
main.py
    ↓
OpenAI Agents SDK + SiliconFlow GLM-5.2
    ↓ tool call
Frankfurter API + Bank of China exchange rates
    ↓
Deterministic calculations and report validation
    ↓
output/latest_report.json
    ↓
Gmail HTML email
    ↓
delivery_log.py → logs/morning_brief.log
```

Fund experiment:

```text
fund_main.py 006131
    ↓
Safely refresh and validate the NAV CSV
    ↓
Calculate deterministic metrics in Python
    ↓
Agent tool call and model-generated narrative
    ↓
Validate the narrative and render output/fund_brief.html
```

### Project Structure

```text
morning_brief_agent/
├── main.py                       # Runs the agent, validates and saves reports
├── email_template.py             # Renders the HTML email card
├── logging_config.py             # Configures log rotation and retention
├── delivery_log.py               # Records Gmail delivery results
├── rate_agent.py                 # Agent, model client, tool registration, schemas
├── tools.py                      # Rate retrieval, cross-checking, calculations
├── fund_metrics.py               # Fund validation and deterministic metrics
├── fund_data_probe.py            # Safe fund data refresh and replacement
├── fund_agent.py                 # Fund tool, Agent instructions, output schemas
├── fund_main.py                  # Runs the fund Agent and saves the final HTML
├── fund_html.py                  # Renders the fund HTML brief
├── fund_preview.py               # Builds an offline preview from fixed data
├── data/                         # Fund sample data and test fixtures
├── docs/                         # MVP definition and metrics guide
├── LICENSE                       # MIT License
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable example
└── tests/                        # Local tests with no paid model calls
```

### Installation

Python 3.11 or later is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Configuration

The project calls `zai-org/GLM-5.2` through SiliconFlow's OpenAI-compatible Chat Completions API:

- Base URL: `https://api.siliconflow.cn/v1`
- Secret name: `SILICONFLOW_API_KEY`

For local scheduling, use a `.env` file in the project root and configure it once:

```bash
cp .env.example .env
chmod 600 .env
```

Then edit `.env` locally:

```text
SILICONFLOW_API_KEY=your_siliconflow_api_key
```

The application loads `.env` automatically. The file is excluded by `.gitignore` and will not be committed to GitHub. Never share its contents or the real key.

You can also use a temporary system environment variable. System environment variables take precedence over `.env`:

macOS / Linux:

```bash
export SILICONFLOW_API_KEY="your_siliconflow_api_key"
```

Windows PowerShell:

```powershell
$env:SILICONFLOW_API_KEY="your_siliconflow_api_key"
```

Never place the API key in source code or commit it to GitHub.

### Run and Test

```bash
python main.py
python -B fund_main.py 006131
python -B fund_preview.py
python -m unittest discover -s tests -v
```

The exchange-rate workflow saves `output/latest_report.json`; the fund workflow saves `output/fund_brief.html`; the offline preview saves `output/fund_brief_preview.html`. Unit tests do not call SiliconFlow or any other paid model API.

### Run Logs

The complete workflow is recorded in `logs/morning_brief.log`, including data retrieval, model calls, report validation, file output, and Gmail delivery. A shared `run_id` links every stage. Logs rotate daily and are retained for 14 days.

API keys, Gmail tokens, full model responses, and full email HTML are never logged. `email_sent` means Gmail delivery succeeded, while `email_failed` means it failed. If no `run_started` entry exists for a date, the local scheduled task did not start.

### Recommendation Rules

- Lowest 30% of valid 14-day observations: a relatively good time to recharge
- Middle 40%: little difference; recharge when needed
- Highest 30%: relatively expensive; consider waiting
- A change greater than ±0.3% between the latest and previous three-day averages is marked as a short-term rise or fall

The trend signal describes recent historical movement only; it is not a forecast.

### Known Limitations of the Fund Experiment

- Fund freshness currently uses calendar days. Long market holidays may incorrectly classify valid data as delayed; a production version should use a trading calendar.
- The local CSV is safely refreshed before a formal run, but remains an experimental sample rather than a real-time market feed. Invalid candidate data never replaces the previous file.
- Python validates and calculates financial figures. The model may only explain validated structured results and must not alter deterministic values.
- Delayed data follows a conservative policy: return `delayed + blocked` and do not generate normal metrics, so stale information is not presented as current.

### Scheduling Notes

The current automation runs locally through Codex. The Mac must be powered on, awake, online, and able to keep Codex running in the background. Execution cannot be guaranteed while the computer is shut down or asleep. Gmail delivery is handled by Codex automation, so Gmail credentials are not stored directly in this Python project.

### License

This project is licensed under the [MIT License](LICENSE). Copyright © 2026 KaiHua.
