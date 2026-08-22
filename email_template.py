from __future__ import annotations

from html import escape

from rate_agent import MorningBriefReport


def _theme(recommendation: str) -> dict[str, str]:
    """根据建议结论返回配色主题。"""
    rec = recommendation.strip()
    if "划算" in rec or "低" in rec or "充" in rec:
        return {
            "accent": "#10b981",
            "accentDark": "#047857",
            "accentLight": "#ecfdf5",
            "accentBorder": "#a7f3d0",
            "icon": "✅",
        }
    if "贵" in rec or "高" in rec or "观察" in rec or "等" in rec:
        return {
            "accent": "#f59e0b",
            "accentDark": "#b45309",
            "accentLight": "#fffbeb",
            "accentBorder": "#fde68a",
            "icon": "⏸️",
        }
    return {
        "accent": "#3b82f6",
        "accentDark": "#1e40af",
        "accentLight": "#eff6ff",
        "accentBorder": "#bfdbfe",
        "icon": "💡",
    }


def _trend_style(trend_change_percent: float) -> tuple[str, str]:
    """返回趋势颜色与箭头。"""
    if trend_change_percent > 0:
        return "#dc2626", "▲"
    if trend_change_percent < 0:
        return "#16a34a", "▼"
    return "#6b7280", "▬"


def render_email_html(report: MorningBriefReport) -> str:
    theme = _theme(report.recommendation)
    trend_color, trend_arrow = _trend_style(report.trend_change_percent)
    trend_change = f"{report.trend_change_percent:+.2f}%"

    reasons = "".join(
        f"""<li style="margin:0 0 12px; padding-left:10px; line-height:1.7; color:#374151; border-left:2px solid {theme['accentBorder']};">
            <span style="display:inline-block; width:20px; height:20px; margin-right:8px; text-align:center; line-height:20px; border-radius:50%; background:{theme['accent']}; color:#ffffff; font-size:12px; font-weight:700;">{idx}</span>
            {escape(reason)}
        </li>"""
        for idx, reason in enumerate(report.rationale, start=1)
    )

    # 卡片四向留白：border-spacing 横纵均为 12px，相邻卡片不粘连。
    # 按密度排布：两个核心数字横排（紧凑），14日位置与短期趋势各占全宽，
    # 让进度条有舒展空间，信息少的趋势卡不再被强行撑大。
    metric_cards = f"""<table role="presentation" style="width:100%; border-collapse:separate; border-spacing:12px; margin-bottom:24px;">
      <tr>
        <td class="mb-cell" style="width:50%; padding:14px 16px; background:#ffffff; border:1px solid #e5e7eb; border-radius:10px; vertical-align:top;">
          <div style="font-size:11px; color:#6b7280; margin-bottom:4px; letter-spacing:0.4px;">USD / CNY</div>
          <div class="mb-title" style="font-size:20px; font-weight:700; color:#111827;">{report.usd_cny_rate:.4f}</div>
        </td>
        <td class="mb-cell" style="width:50%; padding:14px 16px; background:#ffffff; border:1px solid #e5e7eb; border-radius:10px; vertical-align:top;">
          <div style="font-size:11px; color:#6b7280; margin-bottom:4px; letter-spacing:0.4px;">{report.usd_amount:g} 美元参考成本</div>
          <div class="mb-title" style="font-size:20px; font-weight:700; color:#111827;">¥{report.cny_cost:.2f}</div>
        </td>
      </tr>
      <tr>
        <td class="mb-cell" colspan="2" style="padding:14px 16px; background:#ffffff; border:1px solid #e5e7eb; border-radius:10px; vertical-align:top;">
          <div style="font-size:11px; color:#6b7280; margin-bottom:6px; letter-spacing:0.4px;">14 日位置</div>
          <div class="mb-title" style="font-size:16px; font-weight:700; color:#111827; margin-bottom:10px;">{report.position_percentile:.1f}% · {escape(report.position_label)}</div>
          <table role="presentation" style="width:100%; height:5px; border-collapse:collapse; background:#eef2f6; border-radius:3px; overflow:hidden;">
            <tr><td style="width:{report.position_percentile:.1f}%; background:{theme['accent']}; font-size:0; line-height:0;">&nbsp;</td><td style="width:{100 - report.position_percentile:.1f}%; font-size:0; line-height:0;">&nbsp;</td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td class="mb-cell" colspan="2" style="padding:13px 16px; background:#ffffff; border:1px solid #e5e7eb; border-radius:10px; vertical-align:top;">
          <div style="font-size:11px; color:#6b7280; margin-bottom:4px; letter-spacing:0.4px;">短期趋势</div>
          <div class="mb-title" style="font-size:16px; font-weight:700; color:#111827;">
            <span style="color:{trend_color}; margin-right:5px;">{trend_arrow}</span>{escape(report.trend_label)} · {trend_change}
          </div>
          <div style="font-size:11px; color:#9ca3af; margin-top:4px;">非未来预测</div>
        </td>
      </tr>
    </table>"""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    @media (prefers-color-scheme: dark) {{
      .mb-wrapper {{ background:#0b1220 !important; }}
      .mb-card {{ background:#161e2e !important; border-color:#2a3548 !important; }}
      .mb-cell {{ background:#1c2640 !important; border-color:#2a3548 !important; }}
      .mb-title {{ color:#f3f5f9 !important; }}
      .mb-body {{ color:#c3cad6 !important; }}
      .mb-foot {{ background:#11192a !important; border-color:#2a3548 !important; color:#7a8aa3 !important; }}
    }}
  </style>
</head>
<body class="mb-wrapper" style="margin:0; padding:24px 16px; background:#eef1f5; color:#1f2937; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;">
  <div class="mb-card" style="max-width:600px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:14px; overflow:hidden; box-shadow:0 4px 16px rgba(15,23,42,0.07);">
    <div style="padding:24px 28px 20px; background:#0f172a; color:#ffffff;">
      <div style="font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; opacity:0.6; margin-bottom:6px;">每日晨报 · 汇率</div>
      <div class="mb-title" style="font-size:24px; font-weight:800; letter-spacing:-0.3px; color:#ffffff;">{escape(report.effective_rate_date)}</div>
    </div>
    <div style="height:4px; background:{theme['accent']}; font-size:0; line-height:0;">&nbsp;</div>

    <div class="mb-body" style="padding:24px 22px 26px;">
      <div style="padding:12px 0 14px 14px; margin-bottom:22px; border-left:3px solid {theme['accent']};">
        <div style="font-size:11px; color:#6b7280; font-weight:600; margin-bottom:4px; letter-spacing:0.3px;">{theme['icon']} 今日充值建议</div>
        <div class="mb-title" style="font-size:21px; font-weight:800; color:#111827;">{escape(report.recommendation)}</div>
      </div>

      {metric_cards}

      <div style="font-size:15px; font-weight:700; color:#111827; margin:0 0 14px 2px;">判断理由</div>
      <ol style="margin:0; padding-left:0; list-style:none;">{reasons}</ol>
    </div>

    <div class="mb-foot" style="padding:14px 22px; background:#f7f9fb; border-top:1px solid #e5e7eb; font-size:11px; color:#9ca3af; text-align:center; line-height:1.6;">
      数据有效日期 {escape(report.effective_rate_date)} · 基于最近 {report.observation_count} 个有效观测
    </div>
  </div>
</body>
</html>"""
