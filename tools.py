from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from statistics import fmean
from time import sleep
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LOOKBACK_DAYS = 14
USD_AMOUNT = 20.0
LOW_POSITION_CUTOFF = 30.0
HIGH_POSITION_CUTOFF = 70.0
TREND_THRESHOLD_PERCENT = 0.3
CROSS_CHECK_TOLERANCE_PERCENT = 0.5
HTTP_TIMEOUT_SECONDS = 15
HTTP_MAX_ATTEMPTS = 3
HTTP_RETRY_DELAY_SECONDS = 0.5

FRANKFURTER_API_URL = "https://api.frankfurter.dev/v2/rates"
FRANKFURTER_DOCS_URL = "https://frankfurter.dev/"
BOC_RATES_URL = "https://www.boc.cn/sourcedb/whpj/"


class DataSourceError(RuntimeError):
    """Raised when an exchange-rate source cannot provide valid data."""


@dataclass(frozen=True)
class RatePoint:
    date: str
    rate: float
    providers: tuple[str, ...] = ()


@dataclass(frozen=True)
class BocUsdQuote:
    spot_buy: float
    cash_buy: float
    spot_sell: float
    cash_sell: float
    conversion_rate: float
    published_date: str
    published_time: str


def _request_json(url: str) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MorningBriefAgent/1.0",
        },
    )
    for attempt in range(HTTP_MAX_ATTEMPTS):
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError):
            if attempt == HTTP_MAX_ATTEMPTS - 1:
                raise
            sleep(HTTP_RETRY_DELAY_SECONDS * (2**attempt))

    raise RuntimeError("HTTP重试流程异常结束")


def _request_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "MorningBriefAgent/1.0",
        },
    )
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def build_frankfurter_url(reference_date: date | None = None) -> str:
    end_date = reference_date or date.today()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS - 1)
    query = urlencode(
        {
            "base": "USD",
            "quotes": "CNY",
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "expand": "providers",
        }
    )
    return f"{FRANKFURTER_API_URL}?{query}"


def fetch_frankfurter_history(
    reference_date: date | None = None,
    request_json: Callable[[str], Any] = _request_json,
) -> tuple[list[RatePoint], str]:
    source_url = build_frankfurter_url(reference_date)
    try:
        payload = request_json(source_url)
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        raise DataSourceError(f"Frankfurter请求失败：{exc}") from exc

    if not isinstance(payload, list):
        raise DataSourceError("Frankfurter返回格式不是列表")

    points_by_date: dict[str, RatePoint] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("base") != "USD" or item.get("quote") != "CNY":
            continue

        item_date = item.get("date")
        raw_rate = item.get("rate")
        if not isinstance(item_date, str) or not isinstance(raw_rate, (int, float)):
            continue

        rate = float(raw_rate)
        if not math.isfinite(rate) or rate <= 0:
            continue

        raw_providers = item.get("providers") or []
        providers = tuple(
            str(provider)
            for provider in raw_providers
            if isinstance(provider, (str, int, float))
        )
        points_by_date[item_date] = RatePoint(item_date, rate, providers)

    points = sorted(points_by_date.values(), key=lambda point: point.date)
    if len(points) < 6:
        raise DataSourceError(
            f"Frankfurter有效数据不足：需要至少6条，实际{len(points)}条"
        )
    return points, source_url


class _TableRowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_parts is not None:
            text = " ".join("".join(self._cell_parts).split())
            if self._row is not None:
                self._row.append(text)
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _boc_rate(value: str) -> float:
    try:
        rate = float(value) / 100
    except ValueError as exc:
        raise DataSourceError(f"中国银行牌价格式无效：{value}") from exc
    if not math.isfinite(rate) or rate <= 0:
        raise DataSourceError(f"中国银行牌价不是正数：{value}")
    return rate


def parse_boc_usd_quote(html: str) -> BocUsdQuote:
    parser = _TableRowParser()
    parser.feed(html)

    for row in parser.rows:
        cells = [" ".join(cell.split()) for cell in row]
        if not cells or cells[0].replace(" ", "") != "美元":
            continue
        if len(cells) < 8:
            raise DataSourceError("中国银行美元牌价字段数量不足")
        return BocUsdQuote(
            spot_buy=_boc_rate(cells[1]),
            cash_buy=_boc_rate(cells[2]),
            spot_sell=_boc_rate(cells[3]),
            cash_sell=_boc_rate(cells[4]),
            conversion_rate=_boc_rate(cells[5]),
            published_date=cells[6].split()[0],
            published_time=cells[7],
        )

    raise DataSourceError("中国银行页面中未找到美元牌价")


def fetch_boc_usd_quote(
    request_text: Callable[[str], str] = _request_text,
) -> BocUsdQuote:
    try:
        html = request_text(BOC_RATES_URL)
    except (OSError, TimeoutError, UnicodeDecodeError) as exc:
        raise DataSourceError(f"中国银行请求失败：{exc}") from exc
    return parse_boc_usd_quote(html)


def calculate_rank_percentile(rates: list[float]) -> float:
    _validate_rates(rates)
    if len(rates) == 1:
        return 50.0

    latest = rates[-1]
    less_count = sum(rate < latest for rate in rates)
    equal_count = sum(rate == latest for rate in rates)
    average_rank = less_count + (equal_count - 1) / 2
    return average_rank / (len(rates) - 1) * 100


def calculate_trend_change_percent(rates: list[float]) -> float:
    _validate_rates(rates)
    if len(rates) < 6:
        raise ValueError("趋势计算至少需要6条汇率")
    previous_average = fmean(rates[-6:-3])
    recent_average = fmean(rates[-3:])
    return (recent_average - previous_average) / previous_average * 100


def _validate_rates(rates: list[float]) -> None:
    if not rates:
        raise ValueError("汇率列表不能为空")
    if any(not math.isfinite(rate) or rate <= 0 for rate in rates):
        raise ValueError("汇率必须是有效正数")


def classify_position(percentile: float) -> tuple[str, str]:
    if percentile <= LOW_POSITION_CUTOFF:
        return "近期低位", "现在充比较划算"
    if percentile >= HIGH_POSITION_CUTOFF:
        return "近期高位", "当前偏贵，可以观察"
    return "近期中位", "差异不大，按需充值"


def classify_trend(change_percent: float) -> str:
    if change_percent <= -TREND_THRESHOLD_PERCENT:
        return "人民币成本短期下降"
    if change_percent >= TREND_THRESHOLD_PERCENT:
        return "人民币成本短期上升"
    return "短期震荡"


def analyze_rates(points: list[RatePoint]) -> dict[str, Any]:
    if len(points) < 6:
        raise ValueError("汇率分析至少需要6条数据")

    ordered_points = sorted(points, key=lambda point: point.date)
    rates = [point.rate for point in ordered_points]
    _validate_rates(rates)

    latest = ordered_points[-1]
    percentile = calculate_rank_percentile(rates)
    trend_change = calculate_trend_change_percent(rates)
    position_label, recommendation = classify_position(percentile)

    return {
        "effective_date": latest.date,
        "usd_cny_rate": round(latest.rate, 6),
        "usd_amount": USD_AMOUNT,
        "cny_cost": round(latest.rate * USD_AMOUNT, 2),
        "lookback_calendar_days": LOOKBACK_DAYS,
        "observation_count": len(ordered_points),
        "position_percentile": round(percentile, 1),
        "position_label": position_label,
        "trend_change_percent": round(trend_change, 3),
        "trend_label": classify_trend(trend_change),
        "base_recommendation": recommendation,
        "recent_rates": [asdict(point) for point in ordered_points],
    }


def build_exchange_brief(
    reference_date: date | None = None,
    history_fetcher: Callable[
        [date | None], tuple[list[RatePoint], str]
    ] = fetch_frankfurter_history,
    boc_fetcher: Callable[[], BocUsdQuote] = fetch_boc_usd_quote,
) -> dict[str, Any]:
    points, frankfurter_url = history_fetcher(reference_date)
    brief = analyze_rates(points)
    warnings: list[str] = [
        "汇率是参考数据，不包含礼品卡溢价、支付手续费或发卡行换汇费用。",
        "短期趋势只是历史信号，不代表对未来汇率的预测。",
    ]

    sources: list[dict[str, Any]] = [
        {
            "name": "Frankfurter API",
            "url": frankfurter_url,
            "data_date": brief["effective_date"],
            "status": "ok",
        }
    ]

    try:
        boc_quote = boc_fetcher()
        difference = abs(
            boc_quote.spot_sell - float(brief["usd_cny_rate"])
        ) / float(brief["usd_cny_rate"]) * 100
        cross_check_status = (
            "ok" if difference <= CROSS_CHECK_TOLERANCE_PERCENT else "warning"
        )
        if cross_check_status == "warning":
            warnings.append(
                f"Frankfurter与中行现汇卖出价相差{difference:.2f}%，超过"
                f"{CROSS_CHECK_TOLERANCE_PERCENT:.1f}%核对阈值。"
            )
        brief["cross_check"] = {
            "status": cross_check_status,
            "boc_conversion_rate": round(boc_quote.conversion_rate, 6),
            "boc_spot_sell_rate": round(boc_quote.spot_sell, 6),
            "boc_twenty_usd_spot_sell_cost": round(
                boc_quote.spot_sell * USD_AMOUNT, 2
            ),
            "difference_percent": round(difference, 3),
            "published_date": boc_quote.published_date,
            "published_time": boc_quote.published_time,
        }
        sources.append(
            {
                "name": "中国银行外汇牌价",
                "url": BOC_RATES_URL,
                "data_date": boc_quote.published_date,
                "status": cross_check_status,
            }
        )
    except DataSourceError as exc:
        brief["cross_check"] = {
            "status": "unavailable",
            "error": str(exc),
        }
        warnings.append(f"中国银行交叉验证不可用：{exc}")
        sources.append(
            {
                "name": "中国银行外汇牌价",
                "url": BOC_RATES_URL,
                "data_date": None,
                "status": "unavailable",
            }
        )

    brief["report_date"] = (reference_date or date.today()).isoformat()
    brief["warnings"] = warnings
    brief["sources"] = sources
    return brief
