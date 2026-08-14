# Morning Brief Agent / 每日晨报 Agent

[中文说明](#中文说明) · [English](#english)

## 中文说明

一个可以持续扩展的个人晨报 Agent。当前版本每天获取美元兑人民币汇率，分析 20 美元的人民币成本，并生成适合通过 Gmail 发送的 HTML 邮件。

项目采用混合工作流：Python 和工具负责获取、计算与校验确定性数据，OpenAI Agents SDK 调用硅基流动的 GLM-5.2 生成自然语言分析，Codex 定时任务负责运行项目并发送邮件。

### 当前功能

- 获取最近 14 个自然日内的有效 USD/CNY 数据
- 计算 20 美元需要多少人民币
- 判断今日汇率处于近期低位、中位还是高位
- 比较最近 3 个交易日与之前 3 个交易日，生成短期趋势信号
- 使用中国银行外汇牌价进行交叉验证
- 校验模型输出，拒绝保存与工具数据不一致的报告
- 生成结构化 JSON 和 HTML 卡片邮件
- 由 Codex 定时任务通过已连接的 Gmail 发送

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
```

### 项目结构

```text
morning_brief_agent/
├── main.py                       # 运行 Agent、校验报告、生成 HTML 邮件
├── rate_agent.py                 # Agent、模型客户端、工具注册和输出结构
├── tools.py                      # 汇率获取、交叉验证和确定性计算
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
- 环境变量：`SILICONFLOW_API_KEY`

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
python -m unittest discover -s tests -v
```

成功后会生成 `output/latest_report.json`。测试不会调用硅基流动或其他付费模型。

### 判断规则

- 14 日有效数据排名最低 30%：现在充比较划算
- 中间 40%：差异不大，按需充值
- 最高 30%：当前偏贵，可以观察
- 最近 3 日均值相对之前 3 日变化超过 ±0.3%：标记短期上升或下降

趋势信号只描述近期历史变化，不是对未来汇率的预测。

### 定时运行说明

当前定时任务在本地 Codex 中运行。Mac 必须处于开机、未休眠、联网状态，Codex 也需要能够在后台运行；电脑关机或休眠时无法保证准时执行。Gmail 发送由 Codex 自动化负责，不在 Python 项目中直接保存 Gmail 凭据。

---

## English

An extensible personal morning brief agent. The current version retrieves the USD/CNY exchange rate, calculates the CNY cost of USD 20, and generates an HTML email suitable for Gmail delivery.

The project uses a hybrid workflow: Python tools handle deterministic data retrieval, calculation, and validation; the OpenAI Agents SDK calls GLM-5.2 through SiliconFlow for natural-language analysis; a Codex automation runs the project and sends the email.

### Features

- Retrieves valid USD/CNY observations from the latest 14 calendar days
- Calculates the CNY cost of USD 20
- Classifies today's rate as relatively low, medium, or high
- Compares the latest three trading days with the previous three to produce a short-term trend signal
- Cross-checks the reference rate against Bank of China exchange rates
- Rejects model output that does not match deterministic tool data
- Generates structured JSON and an HTML email card
- Supports delivery through a connected Gmail account using Codex automation

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
```

### Project Structure

```text
morning_brief_agent/
├── main.py                       # Runs the agent, validates output, renders HTML
├── rate_agent.py                 # Agent, model client, tool registration, schemas
├── tools.py                      # Rate retrieval, cross-checking, calculations
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
- Environment variable: `SILICONFLOW_API_KEY`

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
python -m unittest discover -s tests -v
```

On success, the report is saved to `output/latest_report.json`. Unit tests do not call SiliconFlow or any other paid model API.

### Recommendation Rules

- Lowest 30% of valid 14-day observations: a relatively good time to recharge
- Middle 40%: little difference; recharge when needed
- Highest 30%: relatively expensive; consider waiting
- A change greater than ±0.3% between the latest and previous three-day averages is marked as a short-term rise or fall

The trend signal describes recent historical movement only; it is not a forecast.

### Scheduling Notes

The current automation runs locally through Codex. The Mac must be powered on, awake, online, and able to keep Codex running in the background. Execution cannot be guaranteed while the computer is shut down or asleep. Gmail delivery is handled by Codex automation, so Gmail credentials are not stored directly in this Python project.
