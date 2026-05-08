#!/usr/bin/env python3
"""
Post-close gainer ingestion job.
Triggered by cron at 4:15 PM ET Mon–Fri:
  15 16 * * 1-5 /opt/trading-journal/venv/bin/python /opt/trading-journal/backend/jobs/ingest_gainers.py

Can also be run manually:
  python ingest_gainers.py --date 2026-05-01
  python ingest_gainers.py --dry-run

Data source strategy:
  - Polygon Snapshot API  → top gainers ticker list (incl. extended hours)
  - Polygon Grouped Daily → OHLCV, volume, gap calculation
  - Polygon News API      → news headline
  - FMP /profile          → float_shares, sector (250 calls/day; cached 7 days)
  - yfinance              → float fallback ONLY if FMP returns None
"""
import sys
import os
import argparse
import logging
from datetime import date as date_cls, datetime, timedelta

# Allow imports from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Screening criteria constants
# ---------------------------------------------------------------------------
MIN_GAP_PCT    = 10.0   # > 10% gap
MAX_FLOAT_M    = 50.0   # < 50M shares (wider net; filter further in UI)
MIN_RVOL       = 2.0    # > 2x RVOL (hard filter at ingest)
MAX_MARKET_CAP = 500e6  # < $500M

POLYGON_SNAPSHOT_LIMIT = 50   # tickers to pull from Polygon gainers snapshot


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def main():
    import pytz
    eastern = pytz.timezone('US/Eastern')
    ny_now  = datetime.now(eastern)

    parser = argparse.ArgumentParser(description='Ingest daily top gainers')
    parser.add_argument('--date',    default=ny_now.strftime('%Y-%m-%d'), help='YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true', help='Fetch data but do not write to DB')
    args = parser.parse_args()

    target_date = args.date
    dry_run     = args.dry_run

    log.info(f"Starting ingestion for {target_date} (NY Time: {ny_now.strftime('%Y-%m-%d %H:%M:%S %Z')})")

    gainers = fetch_gainers(target_date)
    log.info(f"Found {len(gainers)} qualified gainers")

    if not gainers:
        log.warning("No gainers met criteria — exiting")
        return

    if dry_run:
        for g in gainers:
            log.info(f"  DRY RUN: {g}")
        return

    inserted, skipped = write_gainers(gainers, target_date)
    log.info(f"Done — inserted={inserted}, skipped (duplicate)={skipped}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def fetch_gainers(target_date: str) -> list[dict]:
    """
    Full enrichment pipeline:
      1. Polygon Snapshot → ticker list
      2. Polygon Grouped Daily → OHLCV for all tickers in one call
      3. FMP profile → float, sector (yfinance fallback for float)
      4. Polygon News → headline
      5. Filter and return qualified gainers
    """
    # Step 1 — ticker candidates from Polygon snapshot
    raw_snapshot = _get_polygon_snapshot()
    if not raw_snapshot:
        log.error("Polygon snapshot returned no tickers — aborting")
        return []

    log.info(f"Polygon snapshot: {len(raw_snapshot)} tickers")

    # Step 2 — grouped daily OHLCV (single Polygon call for whole market)
    grouped = _get_polygon_grouped_daily(target_date)
    log.info(f"Polygon grouped daily: {len(grouped)} bars for {target_date}")

    # Step 3–5 — enrich each ticker
    gainers = []
    for snap in raw_snapshot:
        result = _enrich_ticker(snap, grouped, target_date)
        if result:
            gainers.append(result)

    # Sort descending by gap
    gainers.sort(key=lambda x: x['gap_pct'], reverse=True)
    return gainers


# ---------------------------------------------------------------------------
# Step 1 — Polygon Snapshot (top gainers, extended hours aware)
# ---------------------------------------------------------------------------

def _get_polygon_snapshot() -> list[dict]:
    """Fetch top gainers from Polygon Snapshot API (Standard tier includes AH)."""
    if not Config.POLYGON_API_KEY:
        log.error("POLYGON_API_KEY not configured")
        return []
    try:
        url = (
            f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
            f"?include_otc=false&apiKey={Config.POLYGON_API_KEY}"
        )
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        tickers = resp.json().get('tickers', [])
        return tickers[:POLYGON_SNAPSHOT_LIMIT]
    except Exception as e:
        log.warning(f"Polygon snapshot failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Step 2 — Polygon Grouped Daily (single call for all OHLCV)
# ---------------------------------------------------------------------------

def _get_polygon_grouped_daily(date: str) -> dict[str, dict]:
    """
    Fetch the full grouped daily bars for a given date.
    Returns a dict keyed by ticker symbol for O(1) lookups.
    Falls back to empty dict on failure (enrichment will skip OHLCV).
    """
    if not Config.POLYGON_API_KEY:
        return {}
    try:
        url = (
            f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date}"
            f"?adjusted=true&include_otc=false&apiKey={Config.POLYGON_API_KEY}"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        return {r['T']: r for r in results if r.get('T')}
    except Exception as e:
        log.warning(f"Polygon grouped daily failed for {date}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Step 3 — Per-ticker enrichment
# ---------------------------------------------------------------------------

def _enrich_ticker(snap: dict, grouped: dict[str, dict], target_date: str) -> dict | None:
    """
    Build a fully enriched gainer row from:
      - Polygon snapshot   (live price, prev close, volume)
      - Polygon grouped daily (authoritative EOD OHLCV: O/H/L/C/V/VWAP)
      - SPY bar from grouped daily (RS vs SPY — zero extra API calls)
      - FMP profile        (float, sector, avg_volume — yfinance float fallback)
      - Polygon news       (latest headline)
    Returns None if the ticker doesn't meet screening criteria.
    """
    ticker = snap.get('ticker', '')
    if not ticker or len(ticker) > 5:
        return None

    # ── Price & Gap from Snapshot ──────────────────────────────────────────
    day        = snap.get('day', {})
    prevDay    = snap.get('prevDay', {})
    last_trade = snap.get('lastTrade', {}) or {}

    prev_close = prevDay.get('c') or prevDay.get('vw')
    last_price = last_trade.get('p') or day.get('c') or day.get('vw')

    if not prev_close or not last_price or prev_close <= 0:
        return None

    gap_pct = round(((last_price - prev_close) / prev_close) * 100, 2)
    if gap_pct < MIN_GAP_PCT:
        return None

    # ── OHLCV from Grouped Daily (authoritative EOD bars) ─────────────────
    bar       = grouped.get(ticker, {})
    open_px   = bar.get('o') or day.get('o') or prev_close
    high_px   = bar.get('h') or day.get('h')
    low_px    = bar.get('l') or day.get('l')
    vwap      = bar.get('vw') or day.get('vw')
    volume    = bar.get('v') or day.get('v') or 0

    # ── FMP Profile → float, sector, avg_volume, shares_outstanding ────────
    float_shares, sector, market_cap, shares_out, avg_vol = _get_profile(ticker)

    if float_shares and float_shares > MAX_FLOAT_M * 1e6:
        return None
    if market_cap and market_cap > MAX_MARKET_CAP:
        return None

    # ── RVOL — use FMP avg_volume if available, else prev-day proxy ────────
    prev_vol = prevDay.get('v') or 0
    rvol_base = avg_vol or prev_vol or 0
    rvol = round(volume / rvol_base, 2) if rvol_base > 0 else None
    if rvol is not None and rvol < MIN_RVOL:
        return None

    # ── Derived fields ─────────────────────────────────────────────────────
    dollar_volume = round(last_price * volume, 0) if volume else None

    # Close location: where in the day's range did it close? (1.0 = HOD, 0.0 = LOD)
    if high_px and low_px and high_px > low_px:
        close_location = round((last_price - low_px) / (high_px - low_px), 3)
    else:
        close_location = None

    # RS vs SPY: stock's move minus SPY's move on the same day (zero extra calls)
    spy_bar = grouped.get('SPY', {})
    if spy_bar and spy_bar.get('o') and spy_bar.get('c') and spy_bar['o'] > 0:
        spy_return = ((spy_bar['c'] - spy_bar['o']) / spy_bar['o']) * 100
        rs_vs_spy  = round(gap_pct - spy_return, 2)
    else:
        rs_vs_spy = None

    # ── News headline from Polygon ─────────────────────────────────────────
    headline   = _get_polygon_news_headline(ticker)
    news_fresh = _classify_news(headline)

    return {
        'ticker':               ticker,
        'gap_pct':              gap_pct,
        'float_shares':         float_shares,
        'rvol_15m':             rvol,
        'sector':               sector,
        'market_cap':           market_cap,
        'news_headline':        headline,
        'news_fresh':           news_fresh,
        'close_price':          round(last_price, 4),
        'open_price':           round(open_px, 4),
        # new enrichment fields
        'high_price':           round(high_px, 4) if high_px else None,
        'low_price':            round(low_px, 4) if low_px else None,
        'prev_close':           round(prev_close, 4),
        'vwap':                 round(vwap, 4) if vwap else None,
        'dollar_volume':        dollar_volume,
        'close_location':       close_location,
        'rs_vs_spy':            rs_vs_spy,
        'shares_outstanding':   shares_out,
        'avg_volume':           avg_vol,
    }


# ---------------------------------------------------------------------------
# Profile — FMP primary, yfinance fallback for float
# ---------------------------------------------------------------------------

def _get_profile(ticker: str) -> tuple[float | None, str | None, float | None, float | None, float | None]:
    """
    Return (float_shares, sector, market_cap, shares_outstanding, avg_volume).

    Priority:
      1. FMP /profile  — primary source, covers most fields
      2. yfinance      — float fallback ONLY if FMP returns None for floatShares
      3. None          — store null, display '—' in UI
    """
    from services.fmp_service import get_company_profile

    profile = get_company_profile(ticker)

    float_shares        = profile.get('float_shares')
    sector              = profile.get('sector') or profile.get('industry')
    market_cap          = profile.get('market_cap')
    shares_outstanding  = profile.get('shares_outstanding')
    avg_volume          = profile.get('avg_volume')

    # Float fallback: yfinance if FMP returned nothing
    if float_shares is None:
        float_shares = _yf_float_fallback(ticker)
        if float_shares:
            log.debug(f"[{ticker}] FMP float=None → yfinance fallback: {float_shares:,.0f}")

    return float_shares, sector, market_cap, shares_outstanding, avg_volume


def _yf_float_fallback(ticker: str) -> float | None:
    """
    Lightweight yfinance call for float shares only.
    Used exclusively as a fallback when FMP returns None.
    """
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        return info.get('floatShares')
    except Exception as e:
        log.debug(f"[{ticker}] yfinance float fallback failed: {e}")
        return None


# ---------------------------------------------------------------------------
# News — Polygon News API (replaces yfinance/Yahoo news)
# ---------------------------------------------------------------------------

def _get_polygon_news_headline(ticker: str) -> str | None:
    """Fetch the most recent news headline for a ticker from Polygon."""
    if not Config.POLYGON_API_KEY:
        return None
    try:
        url = (
            f"https://api.polygon.io/v2/reference/news"
            f"?ticker={ticker}&limit=1&apiKey={Config.POLYGON_API_KEY}"
        )
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        if results:
            return results[0].get('title')
    except Exception as e:
        log.debug(f"[{ticker}] Polygon news failed: {e}")
    return None


# ---------------------------------------------------------------------------
# News freshness classification (LLM)
# ---------------------------------------------------------------------------

def _classify_news(headline: str | None) -> bool:
    """Call LLM to classify news freshness. Returns False if LLM unavailable."""
    if not headline:
        return False
    try:
        from llm.llm_client import classify_news_fresh
        return classify_news_fresh(headline)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Database write
# ---------------------------------------------------------------------------

def write_gainers(gainers: list[dict], target_date: str) -> tuple[int, int]:
    from database import get_connection

    inserted = 0
    skipped  = 0

    with get_connection() as conn:
        for g in gainers:
            try:
                conn.execute(
                    """INSERT INTO daily_gainers
                       (date, ticker, gap_pct, float_shares, rvol_15m, sector,
                        market_cap, news_headline, news_fresh, close_price, open_price,
                        high_price, low_price, prev_close, vwap,
                        dollar_volume, close_location, rs_vs_spy,
                        shares_outstanding, avg_volume)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        target_date,
                        g['ticker'],
                        g['gap_pct'],
                        g['float_shares'],
                        g['rvol_15m'],
                        g['sector'],
                        g['market_cap'],
                        g['news_headline'],
                        g['news_fresh'],
                        g['close_price'],
                        g['open_price'],
                        g.get('high_price'),
                        g.get('low_price'),
                        g.get('prev_close'),
                        g.get('vwap'),
                        g.get('dollar_volume'),
                        g.get('close_location'),
                        g.get('rs_vs_spy'),
                        g.get('shares_outstanding'),
                        g.get('avg_volume'),
                    ),
                )
                inserted += 1
            except Exception as e:
                if 'unique' in str(e).lower():
                    skipped += 1
                else:
                    log.error(f"DB error for {g['ticker']}: {e}")

    return inserted, skipped


if __name__ == '__main__':
    main()
