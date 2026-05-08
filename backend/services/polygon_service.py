import requests
import logging
from config import Config

log = logging.getLogger(__name__)

def get_ticker_details(ticker: str) -> dict:
    """
    Fetch ticker details from Polygon v3 Reference API.
    Returns a dict with sector (sic_description), company name, and description.
    """
    if not Config.POLYGON_API_KEY:
        log.warning("[Polygon] No API key configured")
        return {}

    url = f"https://api.polygon.io/v3/reference/tickers/{ticker.upper()}?apiKey={Config.POLYGON_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 403:
             log.warning(f"[Polygon] 403 Forbidden for {ticker} — likely no reference access on this tier")
             return {}
        resp.raise_for_status()
        
        data = resp.json()
        res = data.get('results', {})
        if not res:
            return {}

        # sic_description is often "PHARMACEUTICAL PREPARATIONS" etc.
        # We'll use it as the 'sector' fallback.
        return {
            'ticker':             res.get('ticker'),
            'company_name':       res.get('name'),
            'sector':             res.get('sic_description'),
            'industry':           res.get('sic_description'),
            'description':        res.get('description'),
            'market_cap':         None,
            'float_shares':       None,
            'shares_outstanding': res.get('weighted_shares_outstanding'),
            'exchange':           res.get('primary_exchange'),
            '_source':            'polygon'
        }
    except Exception as e:
        log.warning(f"[Polygon] Request failed for {ticker}: {e}")
        return {}
