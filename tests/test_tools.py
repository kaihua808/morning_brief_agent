from __future__ import annotations

import unittest

from tools import (
    BocUsdQuote,
    DataSourceError,
    RatePoint,
    analyze_rates,
    build_exchange_brief,
    calculate_rank_percentile,
    calculate_trend_change_percent,
    classify_position,
    classify_trend,
    parse_boc_usd_quote,
)


class RateCalculationTests(unittest.TestCase):
    def test_low_position_is_good_for_recharge(self) -> None:
        percentile = calculate_rank_percentile([7.20, 7.18, 7.16, 7.14, 7.12, 7.10])
        self.assertEqual(percentile, 0.0)
        self.assertEqual(classify_position(percentile)[1], "现在充比较划算")

    def test_middle_position_is_on_demand(self) -> None:
        percentile = calculate_rank_percentile([7.10, 7.20, 7.30, 7.40, 7.50, 7.30])
        self.assertGreater(percentile, 30)
        self.assertLess(percentile, 70)
        self.assertEqual(classify_position(percentile)[1], "差异不大，按需充值")

    def test_high_position_is_expensive(self) -> None:
        percentile = calculate_rank_percentile([7.10, 7.12, 7.14, 7.16, 7.18, 7.20])
        self.assertEqual(percentile, 100.0)
        self.assertEqual(classify_position(percentile)[1], "当前偏贵，可以观察")

    def test_trend_uses_two_three_day_averages(self) -> None:
        falling = calculate_trend_change_percent(
            [7.30, 7.30, 7.30, 7.20, 7.20, 7.20]
        )
        self.assertLess(falling, -0.3)
        self.assertEqual(classify_trend(falling), "人民币成本短期下降")

    def test_twenty_dollar_cost(self) -> None:
        points = [
            RatePoint(f"2026-08-{day:02d}", rate)
            for day, rate in zip(
                range(1, 7),
                [7.10, 7.12, 7.14, 7.16, 7.18, 7.20],
                strict=True,
            )
        ]
        result = analyze_rates(points)
        self.assertEqual(result["usd_amount"], 20.0)
        self.assertEqual(result["cny_cost"], 144.0)


class BocParserTests(unittest.TestCase):
    def test_parse_usd_row(self) -> None:
        html = """
        <table>
          <tr><th>货币名称</th><th>现汇买入价</th></tr>
          <tr>
            <td>美元</td><td>713.00</td><td>711.00</td><td>716.00</td>
            <td>717.00</td><td>714.50</td><td>2026/08/14</td><td>09:31:00</td>
          </tr>
        </table>
        """
        quote = parse_boc_usd_quote(html)
        self.assertEqual(quote.conversion_rate, 7.145)
        self.assertEqual(quote.spot_sell, 7.16)

    def test_missing_usd_row_raises(self) -> None:
        with self.assertRaises(DataSourceError):
            parse_boc_usd_quote("<table><tr><td>欧元</td></tr></table>")


class BriefIntegrationTests(unittest.TestCase):
    def test_cross_check_warning_is_preserved(self) -> None:
        points = [
            RatePoint(f"2026-08-{day:02d}", rate)
            for day, rate in zip(
                range(1, 7),
                [7.10, 7.11, 7.12, 7.13, 7.14, 7.15],
                strict=True,
            )
        ]

        def history_fetcher(_reference_date):
            return points, "https://example.test/frankfurter"

        def boc_fetcher() -> BocUsdQuote:
            return BocUsdQuote(
                spot_buy=7.20,
                cash_buy=7.20,
                spot_sell=7.22,
                cash_sell=7.22,
                conversion_rate=7.25,
                published_date="2026/08/14",
                published_time="09:31:00",
            )

        result = build_exchange_brief(
            history_fetcher=history_fetcher,
            boc_fetcher=boc_fetcher,
        )
        self.assertEqual(result["cross_check"]["status"], "warning")
        self.assertEqual(
            result["cross_check"]["boc_twenty_usd_spot_sell_cost"], 144.4
        )
        self.assertTrue(any("超过" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
