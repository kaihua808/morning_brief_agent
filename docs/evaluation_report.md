# 单基金研究晨报 Agent 评测报告

> 版本：v0.1
> 评测对象：基金 `006131` 研究晨报
> 评测日期：2026-09-04
> 评测目标：验证数据异常不会形成错误晨报，确定性指标由 Python 负责，Model 解释受到边界约束，并能生成可读 HTML。

## 一、评测口径

- 自动化评测：使用固定数据、临时文件和 Mock，不调用付费 Model 或真实交易接口。
- 手工端到端评测：运行真实 Agent，检查工具调用、结构化结果和 HTML 文件。
- 通过标准：实际行为符合 MVP 规格，异常场景必须明确阻断，不能静默返回错误数字。

自动化评测命令：

```bash
python -B -m unittest discover -s tests
```

## 二、10 条产品评测

| ID | 场景 | 预期行为 | 自动化证据 | 当前结果 |
|---|---|---|---|---|
| EV-001 | `006131` 数据新鲜且完整 | 返回 `normal + completed`，七项指标均存在 | `test_fresh_data_returns_all_metrics`，以及三个指标函数测试 | 通过 |
| EV-002 | 输入不支持的基金代码 | 在调用 Model 前拒绝，`metrics` 为 `None` | `test_unsupported_fund_is_blocked` | 通过 |
| EV-003 | CSV 不存在或缺少必要字段 | 返回 `missing + blocked`，给出明确错误 | `test_missing_file`、`test_missing_required_column` | 通过 |
| EV-004 | 历史数据不足 21 条 | 返回 `insufficient + blocked` | `test_insufficient_rows` | 通过 |
| EV-005 | 日期、净值格式非法，或净值不为正数 | 返回 `invalid + blocked`，不计算指标 | `test_invalid_date_text`、`test_non_positive_nav` | 通过 |
| EV-006 | 数据超过新鲜度阈值 | 4 个自然日仍为 `normal`，5 日起为 `delayed + blocked` | `test_four_day_boundary_is_normal`、`test_five_day_boundary_is_delayed`、`test_delayed_data_is_blocked` | 通过 |
| EV-007 | 下载失败或候选数据不可信 | 保留原 CSV；正式指标入口返回 `refresh_failed + blocked` | `test_fetch_failure_keeps_existing_csv`、`test_invalid_candidate_keeps_existing_csv`、`test_refresh_failure_blocks_metric_calculation` | 通过 |
| EV-008 | Model 复述数字、程序流程、直接交易建议或无依据标签 | Python 拒绝该解释，不生成正常晨报 | `test_program_speech_is_blocked`、数值、交易指令和定性标签测试 | 通过 |
| EV-009 | Model 三段解释发生字段对调，或 HTML 中出现特殊字符 | 错位解释被拒绝；进入 HTML 的文字被转义 | 三段职责测试、`test_model_text_is_html_escaped` | 通过 |
| EV-010 | 正常端到端运行 `python -B fund_main.py 006131` | Agent 先调用基金工具，再生成通过校验的三段解释和 `output/fund_brief.html` | 2026-09-03 实际终端运行与浏览器检查 | 手工通过 |

## 三、第一版结果

| 类型 | 通过 | 总数 | 通过率 |
|---|---:|---:|---:|
| 产品评测 | 10 | 10 | 100% |
| 自动化测试 | 59 | 59 | 100% |

结论：当前版本已经覆盖单基金晨报 MVP 的主要正常路径、数据异常路径、Model 输出边界和 HTML 输出路径。这里的通过率只代表本评测集，不代表真实金融数据源和自然语言表达不存在其他风险。

## 四、仍需保留的限制

- 新鲜度暂时按自然日判断，长假期间可能误报；后续应接入交易日历。
- 正式净值 CSV 目前仍在仓库中保留一份可复现快照，后续应把运行缓存与测试固件分离。
- Model 校验主要依赖关键词和字段最低职责，不等于完整理解中文语义。
- 当前只支持 `006131`，没有验证多基金参数传递和批量报告。
- 端到端 Model 评测依赖外部 API，目前还不是可重复的离线自动化测试。

## 五、后续评测方向

1. 给每次真实 Model 输出保存脱敏评测结果，而不是只依赖终端观察。
2. 记录新的真实 badcase，再决定是否扩展 Prompt 或校验规则。
3. 接入交易日历后，为长假、披露延迟和日历失效增加评测。
4. 支持下一只基金前，先增加不同基金代码与不同数据路径的隔离测试。
