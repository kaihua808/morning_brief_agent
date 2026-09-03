"""安全获取并更新单只基金的历史单位净值数据。"""
from __future__ import annotations

from pathlib import Path

import akshare as ak
import pandas as pd


SUPPORTED_FUND_CODE = "006131"
DEFAULT_DATA_PATH = (
    Path(__file__).with_name("data") / "006131_unit_nav_sample.csv"
)
REQUIRED_COLUMNS = ("净值日期", "单位净值", "日增长率")


def show_fund_data(fund_df: pd.DataFrame) -> None:
    """显示 DataFrame 的基本结构和头尾数据。"""
    print("返回类型：")
    print(type(fund_df))

    print("\n表格大小（行数, 列数）：")
    print(fund_df.shape)

    print("\n列名：")
    print(fund_df.columns)

    print("\n每列的数据类型：")
    print(fund_df.dtypes)

    print("\n最前面的 5 行：")
    print(fund_df.head())

    print("\n最后面的 5 行：")
    print(fund_df.tail())


def fetch_fund_nav_data(fund_code: str) -> pd.DataFrame:
    """从 AKShare 获取指定基金的单位净值走势。"""
    return ak.fund_open_fund_info_em(
        symbol=fund_code,
        indicator="单位净值走势",
    )


def validate_refresh_candidate(fund_df: pd.DataFrame) -> pd.DataFrame:
    """清洗并校验候选数据，失败时阻止其覆盖正式 CSV。"""
    if not isinstance(fund_df, pd.DataFrame) or fund_df.empty:
        raise ValueError("基金数据源返回空数据")

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in fund_df.columns
    ]
    if missing_columns:
        raise ValueError(f"基金数据缺少必要字段：{missing_columns}")

    candidate = fund_df.loc[:, list(REQUIRED_COLUMNS)].copy()
    candidate["净值日期"] = pd.to_datetime(
        candidate["净值日期"],
        errors="coerce",
        format="mixed",
    )
    candidate["单位净值"] = pd.to_numeric(
        candidate["单位净值"],
        errors="coerce",
    )
    candidate["日增长率"] = pd.to_numeric(
        candidate["日增长率"],
        errors="coerce",
    )

    missing_counts = candidate.isnull().sum()
    if int(missing_counts.sum()) > 0:
        raise ValueError(
            "基金候选数据存在缺失或无法解析的字段："
            f"{missing_counts[missing_counts > 0].to_dict()}"
        )

    if int((candidate["单位净值"] <= 0).sum()) > 0:
        raise ValueError("基金候选数据存在非正净值")

    if len(candidate) < 21:
        raise ValueError(f"基金候选数据不足21条，当前只有{len(candidate)}条")

    duplicate_date_count = int(candidate["净值日期"].duplicated().sum())
    if duplicate_date_count > 0:
        raise ValueError(f"基金候选数据存在{duplicate_date_count}个重复日期")

    return candidate.sort_values("净值日期").reset_index(drop=True)


def refresh_fund_sample(
    fund_code: str = SUPPORTED_FUND_CODE,
    destination: Path | str = DEFAULT_DATA_PATH,
) -> pd.DataFrame:
    """校验新数据后原子更新本地 CSV，并返回已校验的数据。"""
    if fund_code != SUPPORTED_FUND_CODE:
        raise ValueError(f"当前版本只支持基金{SUPPORTED_FUND_CODE}")

    destination = Path(destination)
    candidate = validate_refresh_candidate(fetch_fund_nav_data(fund_code))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(f"{destination.suffix}.tmp")

    try:
        candidate.to_csv(
            temporary_path,
            index=False,
            encoding="utf-8-sig",
            date_format="%Y-%m-%d",
        )
        temporary_path.replace(destination)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return candidate


def main() -> int:
    """安全刷新正式基金 CSV，并显示更新后的数据结构。"""
    try:
        fund_df = refresh_fund_sample()
    except Exception as exc:
        print(f"基金 CSV 刷新失败：{exc}")
        return 1

    print("\n每列缺失值数量：")
    print(fund_df.isnull().sum())
    print("\n重复日期数量：")
    print(fund_df["净值日期"].duplicated().sum())
    show_fund_data(fund_df)
    print(f"\n基金 CSV 已安全更新：{DEFAULT_DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
