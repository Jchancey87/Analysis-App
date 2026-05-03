"""
catalyst_service.py — Data gatherer for the Catalyst Analysis feature.

Aggregates signals from:
  - Polygon.io: recent news headlines (last 30 days)
  - SEC EDGAR: 8-K filings (FDA events, earnings, contracts, press releases)
  - yfinance: upcoming earnings calendar, analyst upgrades/downgrades
  - Existing LLM: classify_news_fresh() for freshness scoring
"""
import logging
import requests
from datetime import datetime, timedelta
from config import Config

log = logging.getLogger(__name__)


def build_catalyst_payload(ticker: str, date: str | None = None) -> dict:
    """
    Gather all signals needed for a Catalyst Analysis LLM report.

    Args:
        ticker: Stock ticker symbol.
        date:   The date of the gainer event (YYYY-MM-DD). Used to anchor news search.
                Defaults to today if not provided.

    Returns:
        Structured dict for the LLM prompt.
    """
    if not date:
        import pytz
        date = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')

    payload = {
        'ticker':        ticker,
        'event_date':    date,
        'polygon_news':  _get_polygon_news(ticker, date),
        'sec_8k_filings': _get_sec_8k_filings(ticker, date),
        'earnings_calendar': _get_earnings_calendar(ticker),
        'analyst_activity':  _get_analyst_activity(ticker),
        'news_freshness':    _score_news_freshness(ticker, date),
    }
    return payload


# ---------------------------------------------------------------------------
# Individual signal collectors
# ---------------------------------------------------------------------------

def _get_polygon_news(ticker: str, anchor_date: str, n: int = 15) -> list[dict]:
    """
    Fetch the most recent news articles from Polygon.io for the ticker.
    Anchored around anchor_date ± 7 days for context.
    """
    if not Config.POLYGON_API_KEY:
        log.warning('[Catalyst] POLYGON_API_KEY not set, skipping news fetch.')
        return []

    try:
        dt   = datetime.strptime(anchor_date, '%Y-%m-%d')
        from_date = (dt - timedelta(days=14)).strftime('%Y-%m-%d')
        to_date   = (dt + timedelta(days=1)).strftime('%Y-%m-%d')

        url = 'https://api.polygon.io/v2/reference/news'
        params = {
            'ticker':     ticker,
            'published_utc.gte': from_date,
            'published_utc.lte': to_date,
            'order':      'desc',
            'limit':      n,
            'apiKey':     Config.POLYGON_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get('results', [])

        return [
            {
                'title':       a.get('title', ''),
                'published':   a.get('published_utc', '')[:10],
                'author':      a.get('author', ''),
                'description': (a.get('description') or '')[:400],
                'publisher':   a.get('publisher', {}).get('name', ''),
            }
            for a in results
        ]
    except Exception as e:
        log.warning(f'[Catalyst] Polygon news fetch failed: {e}')
        return []


def _get_sec_8k_filings(ticker: str, anchor_date: str, days_back: int = 60) -> list[dict]:
    """
    Return 8-K filings from SEC EDGAR near the event date.
    8-K items of interest: 1.01 (contracts), 2.02 (earnings), 8.01 (other/FDA)
    """
    try:
        from services.sec_service import get_recent_filings
        return get_recent_filings(ticker, forms=['8-K'], days_back=days_back, n=15)
    except Exception as e:
        log.warning(f'[Catalyst] SEC 8-K fetch failed: {e}')
        return []


def _get_earnings_calendar(ticker: str) -> dict:
    """Return the upcoming earnings date and EPS estimates from yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        cal = t.calendar

        if isinstance(cal, dict):
            return {k: str(v) for k, v in cal.items()}
        elif hasattr(cal, 'to_dict'):
            result = {}
            for col in cal.columns:
                for idx in cal.index:
                    result[f'{col}_{idx}'] = str(cal.at[idx, col])
            return result
        return {}
    except Exception as e:
        log.warning(f'[Catalyst] Earnings calendar fetch failed: {e}')
        return {}


def _get_analyst_activity(ticker: str, n: int = 8) -> list[dict]:
    """Return recent analyst upgrades/downgrades from yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.upgrades_downgrades
        if df is None or df.empty:
            return []

        df = df.sort_index(ascending=False).head(n)
        return df.reset_index().to_dict(orient='records')
    except Exception as e:
        log.warning(f'[Catalyst] Analyst activity fetch failed: {e}')
        return []


def _score_news_freshness(ticker: str, anchor_date: str) -> dict:
    """
    Use the existing LLM classifier to score freshness of top headlines.
    Returns a dict: {headline: 'FRESH'|'STALE', ...}
    """
    try:
        from llm.llm_client import classify_news_fresh
        news = _get_polygon_news(ticker, anchor_date, n=5)
        if not news:
            return {}

        scores = {}
        for article in news:
            title = article.get('title', '')
            if title:
                scores[title[:80]] = 'FRESH' if classify_news_fresh(title) else 'STALE'
        return scores
    except Exception as e:
        log.warning(f'[Catalyst] News freshness scoring failed: {e}')
        return {}
