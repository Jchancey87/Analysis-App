"""
services/polygon_client.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Thin adapter around the official Massive Python client SDK (RESTClient).
Massive.com is the rebrand of Polygon.io (rebranded Oct 30, 2025).
All market-data REST calls in this project should go through this module
so that SDK method churn never leaks into business logic.

Install: pip install -U massive
GitHub:  https://github.com/massive-com/client-python
"""
import logging
from typing import Optional

from massive import RESTClient
from pydantic import TypeAdapter, ValidationError
from config import Config
from validation.external_schemas import (
    MassiveAgg,
    MassiveSnapshotTicker,
    MassiveTickerDetails,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton client — one per process
# ---------------------------------------------------------------------------

def _make_client(pagination: bool = True) -> RESTClient:
    if not Config.POLYGON_API_KEY:
        raise RuntimeError("POLYGON_API_KEY is not configured")
    return RESTClient(api_key=Config.POLYGON_API_KEY, pagination=pagination)


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

def get_gainers_snapshot(include_otc: bool = False) -> list[dict]:
    """
    Return the top-gainers snapshot list from Polygon.
    Each element is a dict with at minimum:
      ticker, todaysChangePerc, lastTrade.p, day.*, prevDay.*
    """
    client = _make_client()
    try:
        resp = client.get_snapshot_direction("stocks", "gainers", include_otc=include_otc)
        # SDK returns an iterable of TickerSnapshot objects
        tickers = []
        for snap in (resp or []):
            try:
                # Validate and dump to dict
                m = MassiveSnapshotTicker.model_validate(snap)
                tickers.append(m.model_dump())
            except ValidationError as exc:
                log.warning(f"[Polygon] gainer snapshot row validation failed: {exc}")
                continue
        return tickers
    except Exception as e:
        log.warning(f"[Polygon] gainers snapshot failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Grouped daily bars
# ---------------------------------------------------------------------------

def get_grouped_daily(date: str, adjusted: bool = True, include_otc: bool = False) -> dict[str, dict]:
    """
    Fetch the full grouped daily bars for *date* (YYYY-MM-DD).
    Returns a dict keyed by ticker symbol → bar dict with keys o/h/l/c/v/vw/t.
    Falls back to {} on any error.
    """
    client = _make_client()
    try:
        resp = client.get_grouped_daily_aggs(
            date,
            adjusted=adjusted,
            include_otc=include_otc,
        )
        results = resp.results if hasattr(resp, "results") else (resp or [])
        out = {}
        for bar in results:
            try:
                # The SDK grouped daily bars use ticker/T interchangeably;
                # MassiveAgg handles this via populate_by_name if we map it,
                # but for simplicity we just validate the OHLCV part.
                m = MassiveAgg.model_validate(bar)
                # Ticker is usually .ticker or .T
                sym = getattr(bar, "ticker", None) or getattr(bar, "T", None)
                if not sym and isinstance(bar, dict):
                    sym = bar.get("T") or bar.get("ticker")

                if sym:
                    d = m.model_dump()
                    d["T"] = sym
                    out[sym] = d
            except ValidationError:
                continue

        log.info(f"[Polygon] grouped daily {date}: {len(out)} bars")
        return out
    except Exception as e:
        log.warning(f"[Polygon] grouped daily failed for {date}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Minute / daily aggregate bars
# ---------------------------------------------------------------------------

def get_minute_bars(ticker: str, start: str, end: str, limit: int = 50_000) -> list[dict]:
    """OHLCV minute bars for *ticker* between *start* and *end* (YYYY-MM-DD)."""
    client = _make_client()
    bars = []
    for bar in client.list_aggs(
        ticker=ticker,
        multiplier=1,
        timespan="minute",
        from_=start,
        to=end,
        limit=limit,
    ):
        try:
            m = MassiveAgg.model_validate(bar)
            bars.append(m.model_dump())
        except ValidationError:
            continue
    return bars


def get_daily_bars(ticker: str, start: str, end: str, limit: int = 5_000) -> list[dict]:
    """OHLCV daily bars for *ticker* between *start* and *end* (YYYY-MM-DD)."""
    client = _make_client()
    bars = []
    for bar in client.list_aggs(
        ticker=ticker,
        multiplier=1,
        timespan="day",
        from_=start,
        to=end,
        limit=limit,
    ):
        try:
            m = MassiveAgg.model_validate(bar)
            bars.append(m.model_dump())
        except ValidationError:
            continue
    return bars


# ---------------------------------------------------------------------------
# Last trade / last quote
# ---------------------------------------------------------------------------

def get_last_trade(ticker: str) -> Optional[dict]:
    client = _make_client()
    try:
        t = client.get_last_trade(ticker=ticker)
        return t.__dict__ if t else None
    except Exception as e:
        log.warning(f"[Polygon] get_last_trade({ticker}) failed: {e}")
        return None


def get_last_quote(ticker: str) -> Optional[dict]:
    client = _make_client()
    try:
        q = client.get_last_quote(ticker=ticker)
        return q.__dict__ if q else None
    except Exception as e:
        log.warning(f"[Polygon] get_last_quote({ticker}) failed: {e}")
        return None


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def get_latest_headline(ticker: str) -> Optional[str]:
    """Return the most recent news headline for *ticker*, or None."""
    client = _make_client(pagination=False)  # we only want 1 result
    try:
        results = list(client.list_ticker_news(ticker, limit=1))
        if results:
            article = results[0]
            return getattr(article, "title", None) or (article.get("title") if isinstance(article, dict) else None)
    except Exception as e:
        log.debug(f"[Polygon] news for {ticker} failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Ticker details (reference)
# ---------------------------------------------------------------------------

def get_ticker_details(ticker: str) -> dict:
    """
    Fetch reference data for *ticker* (name, SIC description, exchange, etc.).
    Returns a normalised dict; empty dict on error or missing data.
    """
    client = _make_client()
    try:
        res = client.get_ticker_details(ticker.upper())
        if not res:
            return {}

        try:
            m = MassiveTickerDetails.model_validate(res)
        except ValidationError as exc:
            log.warning(f"[Polygon] ticker details validation failed for {ticker}: {exc}")
            return {}

        return {
            "ticker":             m.ticker,
            "company_name":       m.name,
            "sector":             m.sic_description,
            "industry":           m.sic_description,
            "description":        m.description,
            "market_cap":         None,   # not in reference endpoint
            "float_shares":       None,
            "shares_outstanding": m.weighted_shares_outstanding,
            "exchange":           m.primary_exchange,
            "_source":            "polygon",
        }
    except Exception as e:
        log.warning(f"[Polygon] get_ticker_details({ticker}) failed: {e}")
        return {}
