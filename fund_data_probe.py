"""获取并观察单只基金的历史单位净值数据。"""
import akshare as ak
import pandas as pd

def show_fund_data(fund_df):
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


def main():
    fund_df = ak.fund_open_fund_info_em(
       symbol="006131",
       indicator="单位净值走势"
   )

    fund_df["净值日期"] = pd.to_datetime(
        fund_df["净值日期"],
        errors="coerce"
    )

    fund_df = fund_df.sort_values("净值日期").reset_index(drop=True)

    print("\n每列缺失值数量：")
    print(fund_df.isnull().sum())
    print("\n重复日期数量：")
    print(fund_df["净值日期"].duplicated().sum())

    fund_df.to_csv(
        "data/006131_unit_nav_sample.csv",
        index=False,
        encoding="utf-8-sig"
    )

    show_fund_data(fund_df)


if __name__ == "__main__":
    main()
