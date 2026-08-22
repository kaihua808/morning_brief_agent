"""计算基金历史净值的确定性指标。"""

from pathlib import Path

import pandas as pd


SAMPLE_DATA_PATH = Path(__file__).with_name("data") / "006131_unit_nav_sample.csv"
SUPPORTED_FUND_CODE = "006131"


def load_fund_sample():
    fund_df = pd.read_csv(SAMPLE_DATA_PATH)
    fund_df["净值日期"] = pd.to_datetime(fund_df["净值日期"])
    return fund_df


def build_fund_brief(fund_code):
    """读取 006131 本地样例并返回结构化基金指标。"""
    # ===== 你手敲：代码校验、数据校验、指标计算和 brief 字典 =====
    pass


def calculate_period_change(nav_values, trading_days):
    start_value = nav_values[-(trading_days + 1)]
    end_value = nav_values[-1]
    return (end_value / start_value - 1) * 100


def calculate_range_position(nav_values):
    highest_value = max(nav_values)
    lowest_value = min(nav_values)
    current_value = nav_values[-1]

    if highest_value == lowest_value:
        raise ValueError("最高值与最低值相同，无法计算区间位置")

    position = (current_value - lowest_value) / (highest_value - lowest_value) * 100
    return highest_value, lowest_value, position


def calculate_max_drawdown(nav_values):
    peak_value = nav_values[0]
    max_drawdown = 0.0

    for nav_value in nav_values:
        peak_value = max(peak_value, nav_value)
        drawdown = (nav_value / peak_value - 1) * 100
        max_drawdown = min(max_drawdown, drawdown)

    return max_drawdown


def test_calculate_period_change():
    assert round(
        calculate_period_change([1.00, 1.01, 1.02, 1.03, 1.04, 1.05], 5),
        2,
    ) == 5.00
    assert round(
        calculate_period_change([1.00, 0.99, 0.98, 0.97, 0.96, 0.95], 5), 2) == -5.00


def main():
    # 已完成：近 5 日变化的固定数据验证
    example_navs = [1.00, 1.02, 1.01, 1.03, 1.04, 1.05]
    result_5days = calculate_period_change(example_navs, 5)
    print(f"近5日变化：{result_5days:.2f}%")

    test_calculate_period_change()
    print("区间变化测试通过")

    position_example_navs = [1.00, 1.20, 1.10]
    highest_value, lowest_value, position = calculate_range_position(position_example_navs)
    current_value = position_example_navs[-1]

    print(f"区间最高值：{highest_value:.2f}")
    print(f"区间最低值：{lowest_value:.2f}")
    print(f"当前值：{current_value:.2f}")
    print(f"区间位置：{position:.2f}%")

    drawdown_example_navs = [1.00, 1.20, 1.10, 0.90, 1.15]
    max_drawdown = calculate_max_drawdown(drawdown_example_navs)
    print(f"最大回撤：{max_drawdown:.2f}%")

    fund_df = load_fund_sample()
    latest_date = fund_df["净值日期"].iloc[-1]
    print(f"\n真实样例记录数：{len(fund_df)}")
    print(f"真实样例最新日期：{latest_date.date()}")

    nav_values = fund_df["单位净值"].tolist()
    recent_20_navs = nav_values[-20:]

    latest_nav = nav_values[-1]
    fund_change_5d = calculate_period_change(nav_values, 5)
    fund_change_20d = calculate_period_change(nav_values, 20)
    highest_value, lowest_value, position = calculate_range_position(recent_20_navs)
    max_drawdown = calculate_max_drawdown(recent_20_navs)

    print(f"\n006131 真实指标（截至 {latest_date.date()}）")
    print(f"最新单位净值：{latest_nav:.4f}")
    print(f"近5日变化：{fund_change_5d:.2f}%")
    print(f"近20日变化：{fund_change_20d:.2f}%")
    print(f"近20日最高值：{highest_value:.4f}")
    print(f"近20日最低值：{lowest_value:.4f}")
    print(f"近20日区间位置：{position:.2f}%")
    print(f"近20日最大回撤：{max_drawdown:.2f}%")

if __name__ == "__main__":
    main()
