"""计算基金历史净值的确定性指标。"""
import json
from datetime import date
from pathlib import Path


import pandas as pd


SAMPLE_DATA_PATH = Path(__file__).with_name("data") / "006131_unit_nav_sample.csv"
SUPPORTED_FUND_CODE = "006131"


def load_fund_sample(path=SAMPLE_DATA_PATH):
    """读取指定基金净值 CSV，并返回尚未清洗的 DataFrame。"""
    return pd.read_csv(path)


def build_fund_brief(
    fund_code,
    reference_date=None,
    data_path=SAMPLE_DATA_PATH,
):
    """校验基金数据，并在数据可信时返回结构化指标结果。"""
    freshness_basis = "calendar_days"

    if reference_date is None:
        reference_date = date.today()

    if fund_code != SUPPORTED_FUND_CODE:
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "invalid",
            "calculation_status": "blocked",
            "metrics": None,
            "error": f"当前版本只支持基金{SUPPORTED_FUND_CODE}",
        }

    data_path = Path(data_path)
    if not data_path.exists():
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "missing",
            "calculation_status": "blocked",
            "metrics": None,
            "error": "基金数据文件不存在",
        }

    fund_df = load_fund_sample(data_path)

    required_columns = ["净值日期", "单位净值"]
    missing_columns = [
        column for column in required_columns if column not in fund_df.columns
    ]
    if missing_columns:
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "missing",
            "calculation_status": "blocked",
            "metrics": None,
            "error": f"基金数据缺少必要字段：{missing_columns}",
        }

    missing_date_count = int(fund_df["净值日期"].isnull().sum())
    missing_nav_count = int(fund_df["单位净值"].isnull().sum())

    converted_dates = pd.to_datetime(
        fund_df["净值日期"],
        errors="coerce",
        format="mixed",
    )
    converted_navs = pd.to_numeric(fund_df["单位净值"], errors="coerce")
    invalid_date_count = int(converted_dates.isnull().sum()) - missing_date_count
    invalid_nav_format_count = int(converted_navs.isnull().sum()) - missing_nav_count

    fund_df["净值日期"] = converted_dates
    fund_df["单位净值"] = converted_navs

    if missing_date_count > 0 or missing_nav_count > 0:
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "missing",
            "calculation_status": "blocked",
            "metrics": None,
            "error": (
                f"基金数据存在缺失值："
                f"日期缺失{missing_date_count}条，"
                f"单位净值缺失{missing_nav_count}条"
            ),
        }

    if invalid_date_count > 0 or invalid_nav_format_count > 0:
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "invalid",
            "calculation_status": "blocked",
            "metrics": None,
            "error": (
                f"基金数据存在格式错误："
                f"日期无效{invalid_date_count}条，"
                f"单位净值无效{invalid_nav_format_count}条"
            ),
        }

    invalid_nav_count = int((fund_df["单位净值"] <= 0).sum())
    if invalid_nav_count > 0:
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "invalid",
            "calculation_status": "blocked",
            "metrics": None,
            "error": f"基金数据存在{invalid_nav_count}条非正净值",
        }

    if len(fund_df) < 21:
        return {
            "fund_code": fund_code,
            "freshness_basis": freshness_basis,
            "data_status": "insufficient",
            "calculation_status": "blocked",
            "metrics": None,
            "error": f"基金数据不足21条，当前只有{len(fund_df)}条",
        }

    fund_df = fund_df.sort_values("净值日期").reset_index(drop=True)
    latest_date = fund_df["净值日期"].iloc[-1].date()
    age_calendar_days = (reference_date - latest_date).days

    if age_calendar_days < 0:
        return {
            "fund_code": fund_code,
            "data_date": latest_date.isoformat(),
            "age_calendar_days": age_calendar_days,
            "freshness_basis": freshness_basis,
            "data_status": "invalid",
            "calculation_status": "blocked",
            "metrics": None,
            "error": "基金数据日期晚于参考日期",
        }

    if age_calendar_days > 4:
        return {
            "fund_code": fund_code,
            "data_date": latest_date.isoformat(),
            "age_calendar_days": age_calendar_days,
            "freshness_basis": freshness_basis,
            "data_status": "delayed",
            "calculation_status": "blocked",
            "metrics": None,
            "error": "基金数据已过期，请更新后重新分析",
        }

    nav_values = fund_df["单位净值"].tolist()
    recent_20_navs = nav_values[-20:]

    latest_nav = nav_values[-1]
    change_5d = calculate_period_change(nav_values, 5)
    change_20d = calculate_period_change(nav_values, 20)
    highest_20d, lowest_20d, position_20d = calculate_range_position(recent_20_navs)
    max_drawdown_20d = calculate_max_drawdown(recent_20_navs)

    return {
        "fund_code": fund_code,
        "data_date": latest_date.isoformat(),
        "age_calendar_days": age_calendar_days,
        "freshness_basis": freshness_basis,
        "data_status": "normal",
        "calculation_status": "completed",
        "metrics": {
            "latest_nav": round(latest_nav, 4),
            "change_5d_percent": round(change_5d, 2),
            "change_20d_percent": round(change_20d, 2),
            "highest_20d": round(highest_20d, 4),
            "lowest_20d": round(lowest_20d, 4),
            "position_20d_percent": round(position_20d, 2),
            "max_drawdown_20d_percent": round(max_drawdown_20d, 2),
        },
        "error": None,
    }

def calculate_period_change(nav_values, trading_days):
    """计算指定交易日区间内的净值变化百分比。"""
    start_value = nav_values[-(trading_days + 1)]
    end_value = nav_values[-1]
    return (end_value / start_value - 1) * 100


def calculate_range_position(nav_values):
    """计算当前净值在区间最高值与最低值之间的位置百分比。"""
    highest_value = max(nav_values)
    lowest_value = min(nav_values)
    current_value = nav_values[-1]

    if highest_value == lowest_value:
        raise ValueError("最高值与最低值相同，无法计算区间位置")

    position = (current_value - lowest_value) / (highest_value - lowest_value) * 100
    return highest_value, lowest_value, position


def calculate_max_drawdown(nav_values):
    """计算净值序列中从阶段高点到后续低点的最大跌幅。"""
    peak_value = nav_values[0]
    max_drawdown = 0.0

    for nav_value in nav_values:
        peak_value = max(peak_value, nav_value)
        drawdown = (nav_value / peak_value - 1) * 100
        max_drawdown = min(max_drawdown, drawdown)

    return max_drawdown


def main():
    """生成受数据校验保护的基金指标 JSON，并打印到终端。"""
    brief = build_fund_brief(SUPPORTED_FUND_CODE)

    print(
        json.dumps(
            brief,
            indent=2,
            ensure_ascii=False,
        )
    )

if __name__ == "__main__":
    main()
