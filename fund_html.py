"""把经过校验的基金晨报报告渲染为独立 HTML 页面。"""
from __future__ import annotations

from html import escape

from fund_agent import FundBriefReport


def _change_style(change_percent: float) -> tuple[str, str]:
    """根据已经发生的涨跌返回展示颜色和箭头。"""
    if change_percent > 0:
        return "#dc2626", "▲"
    if change_percent < 0:
        return "#16a34a", "▼"
    return "#64748b", "▬"


def _format_change(change_percent: float) -> str:
    """把涨跌幅格式化为带正负号的百分比文字。"""
    return f"{change_percent:+.2f}%"


def render_fund_html(report: FundBriefReport) -> str:
    """将 FundBriefReport 字段映射为可在浏览器打开的基金晨报。"""
    change_5d_color, change_5d_arrow = _change_style(report.change_5d_percent)
    change_20d_color, change_20d_arrow = _change_style(report.change_20d_percent)
    position_percent = min(max(report.position_20d_percent, 0.0), 100.0)
    freshness_label = {
        "calendar_days": "自然日校验",
    }.get(report.freshness_basis, report.freshness_basis)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>基金 {escape(report.fund_code)} 晨报</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 28px 16px; background: #eef2f7; color: #1f2937; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }}
    .report {{ max-width: 680px; margin: 0 auto; overflow: hidden; background: #ffffff; border: 1px solid #dfe5ee; border-radius: 18px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08); }}
    .header {{ padding: 28px 30px 24px; color: #ffffff; background: linear-gradient(135deg, #0f172a, #1e3a5f); }}
    .eyebrow {{ margin-bottom: 8px; font-size: 12px; letter-spacing: 1.4px; opacity: 0.7; }}
    .header h1 {{ margin: 0; font-size: 27px; }}
    .header-meta {{ display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 13px; color: #dbeafe; font-size: 13px; }}
    .status {{ display: inline-block; padding: 4px 9px; color: #166534; background: #dcfce7; border-radius: 999px; font-size: 12px; font-weight: 700; }}
    .content {{ padding: 26px 24px 30px; }}
    .section-title {{ margin: 0 0 12px; color: #0f172a; font-size: 16px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }}
    .metric {{ padding: 15px; background: #f8fafc; border: 1px solid #e5eaf1; border-radius: 12px; }}
    .metric-label {{ margin-bottom: 7px; color: #64748b; font-size: 12px; }}
    .metric-value {{ color: #0f172a; font-size: 21px; font-weight: 800; }}
    .range-card {{ margin-bottom: 24px; padding: 18px; border: 1px solid #e5eaf1; border-radius: 12px; }}
    .range-row {{ display: flex; justify-content: space-between; gap: 16px; margin-bottom: 11px; font-size: 13px; }}
    .range-value {{ color: #0f172a; font-weight: 700; }}
    .track {{ height: 8px; overflow: hidden; background: #e2e8f0; border-radius: 999px; }}
    .track-fill {{ width: {position_percent:.2f}%; height: 100%; background: linear-gradient(90deg, #2563eb, #38bdf8); }}
    .range-scale {{ display: flex; justify-content: space-between; margin-top: 7px; color: #94a3b8; font-size: 11px; }}
    .risk-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }}
    .narratives {{ display: grid; gap: 12px; }}
    .narrative {{ padding: 16px 17px; border-left: 4px solid #3b82f6; background: #f8fafc; border-radius: 8px; }}
    .narrative.risk {{ border-left-color: #f59e0b; }}
    .narrative.reminder {{ border-left-color: #8b5cf6; }}
    .narrative h3 {{ margin: 0 0 7px; color: #334155; font-size: 13px; }}
    .narrative p {{ margin: 0; color: #334155; font-size: 14px; line-height: 1.75; }}
    .footer {{ padding: 15px 24px; color: #64748b; background: #f8fafc; border-top: 1px solid #e5eaf1; font-size: 11px; line-height: 1.7; text-align: center; }}
    @media (max-width: 560px) {{
      body {{ padding: 0; background: #ffffff; }}
      .report {{ border: 0; border-radius: 0; box-shadow: none; }}
      .header {{ padding: 24px 20px; }}
      .content {{ padding: 22px 16px 26px; }}
      .metric-grid {{ grid-template-columns: 1fr; }}
      .risk-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="report">
    <header class="header">
      <div class="eyebrow">DAILY FUND BRIEF</div>
      <h1>基金 {escape(report.fund_code)} 晨报</h1>
      <div class="header-meta">
        <span>净值日期：{escape(report.data_date)}</span>
        <span>数据年龄：{report.age_calendar_days} 个自然日</span>
        <span class="status">数据正常 · {escape(freshness_label)}</span>
      </div>
    </header>

    <div class="content">
      <h2 class="section-title">核心指标</h2>
      <section class="metric-grid" aria-label="核心指标">
        <div class="metric">
          <div class="metric-label">最新单位净值</div>
          <div class="metric-value">{report.latest_nav:.4f}</div>
        </div>
        <div class="metric">
          <div class="metric-label">近 5 日变化</div>
          <div class="metric-value" style="color:{change_5d_color};">{change_5d_arrow} {_format_change(report.change_5d_percent)}</div>
        </div>
        <div class="metric">
          <div class="metric-label">近 20 日变化</div>
          <div class="metric-value" style="color:{change_20d_color};">{change_20d_arrow} {_format_change(report.change_20d_percent)}</div>
        </div>
      </section>

      <h2 class="section-title">近期区间与风险</h2>
      <section class="range-card" aria-label="近期区间与风险">
        <div class="range-row">
          <span>近 20 日区间位置</span>
          <span class="range-value">{report.position_20d_percent:.2f}%</span>
        </div>
        <div class="track" aria-hidden="true"><div class="track-fill"></div></div>
        <div class="range-scale"><span>低点 {report.lowest_20d:.4f}</span><span>高点 {report.highest_20d:.4f}</span></div>
        <div class="risk-row">
          <div class="metric">
            <div class="metric-label">近 20 日最大回撤</div>
            <div class="metric-value" style="color:#b45309;">{report.max_drawdown_20d_percent:.2f}%</div>
          </div>
          <div class="metric">
            <div class="metric-label">计算状态</div>
            <div class="metric-value" style="font-size:17px;">{escape(report.calculation_status)}</div>
          </div>
        </div>
      </section>

      <h2 class="section-title">晨报解读</h2>
      <section class="narratives" aria-label="晨报解读">
        <article class="narrative">
          <h3>变化摘要</h3>
          <p>{escape(report.summary)}</p>
        </article>
        <article class="narrative risk">
          <h3>风险观察</h3>
          <p>{escape(report.risk_note)}</p>
        </article>
        <article class="narrative reminder">
          <h3>行为提醒</h3>
          <p>{escape(report.behavior_reminder)}</p>
        </article>
      </section>
    </div>

    <footer class="footer">
      本页面使用本地基金净值样例生成，不代表实时行情。指标由 Python 计算，文字仅用于解释已发生的数据变化，不构成投资建议。
    </footer>
  </main>
</body>
</html>"""
