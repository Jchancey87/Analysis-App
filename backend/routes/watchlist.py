import json
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from database import get_connection
from validation.decorators import validate_body
from validation.schemas import WatchlistAddBody, WatchlistUpdateBody

watchlist_bp = Blueprint('watchlist', __name__)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@watchlist_bp.route('/watchlist', methods=['GET'])
def list_watchlist():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist ORDER BY last_viewed_at DESC, added_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Add ticker
# ---------------------------------------------------------------------------

@watchlist_bp.route('/watchlist', methods=['POST'])
@validate_body(WatchlistAddBody)
def add_to_watchlist(data: WatchlistAddBody):
    ticker   = data.ticker
    sector   = data.sector
    notes    = data.notes
    tags_raw = data.tags

    # ── Automatic Enrichment ──────────────────────────────────────────
    # If key data is missing, fetch from FMP + supplement with AI
    if not sector or not notes or not tags_raw:
        from services.fmp_service import get_company_profile
        from llm.llm_client import get_ticker_enrichment

        profile = get_company_profile(ticker)
        if profile:
            if not sector:
                sector = profile.get('sector')

            # If notes or tags are still empty, use AI to summarize the profile
            if not notes or not tags_raw:
                enrich = get_ticker_enrichment(
                    ticker,
                    profile.get('sector', 'Unknown'),
                    profile.get('description') or f"A company in the {profile.get('sector', 'Unknown')} sector."
                )
                if not notes:
                    notes = enrich.get('notes')
                if not tags_raw:
                    tags_raw = enrich.get('tags') or []

    tags = json.dumps([str(t).strip() for t in tags_raw if str(t).strip()])

    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO watchlist (ticker, sector, notes, tags, added_at) VALUES (%s, %s, %s, %s, %s)",
                (ticker, sector, notes, tags, now),
            )
    except Exception as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': f'{ticker} is already on your watchlist'}), 409
        raise

    return jsonify({'ticker': ticker}), 201


# ---------------------------------------------------------------------------
# Update notes / tags / sector
# ---------------------------------------------------------------------------

@watchlist_bp.route('/watchlist/<ticker>', methods=['PUT'])
@validate_body(WatchlistUpdateBody)
def update_watchlist_item(data: WatchlistUpdateBody, ticker):
    ticker  = ticker.upper().strip()
    updates = {}

    if data.notes is not None:
        updates['notes'] = data.notes
    if data.sector is not None:
        updates['sector'] = data.sector
    if data.tags is not None:
        updates['tags'] = json.dumps(data.tags)

    set_clause = ', '.join(f'{k} = %s' for k in updates)
    values     = list(updates.values()) + [ticker]

    with get_connection() as conn:
        row = conn.execute("SELECT ticker FROM watchlist WHERE ticker = %s", (ticker,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        conn.execute(f"UPDATE watchlist SET {set_clause} WHERE ticker = %s", values)

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Touch last_viewed_at (called when research page opens for a ticker)
# ---------------------------------------------------------------------------

@watchlist_bp.route('/watchlist/<ticker>/viewed', methods=['POST'])
def mark_viewed(ticker):
    ticker = ticker.upper().strip()
    now    = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE watchlist SET last_viewed_at = %s WHERE ticker = %s", (now, ticker)
        )
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Remove ticker
# ---------------------------------------------------------------------------

@watchlist_bp.route('/watchlist/<ticker>', methods=['DELETE'])
def remove_from_watchlist(ticker):
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        row = conn.execute("SELECT ticker FROM watchlist WHERE ticker = %s", (ticker,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        conn.execute("DELETE FROM watchlist WHERE ticker = %s", (ticker,))
    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Batch live prices — returns Polygon snapshot price for each watchlist item
# ---------------------------------------------------------------------------

@watchlist_bp.route('/watchlist/prices', methods=['GET'])
def watchlist_prices():
    """
    Returns current Polygon price + % change for every watchlist ticker.
    Used by the dashboard to show if a watchlist stock is waking up.
    """
    import requests as _req
    from config import Config

    with get_connection() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist ORDER BY added_at DESC").fetchall()

    tickers = [r['ticker'] for r in rows]
    if not tickers:
        return jsonify({})

    polygon_key = getattr(Config, 'POLYGON_API_KEY', None)
    if not polygon_key:
        return jsonify({})

    results = {}
    for ticker in tickers:
        try:
            url = f'https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}'
            resp = _req.get(url, params={'apiKey': polygon_key}, timeout=5)
            if resp.ok:
                snap = resp.json().get('ticker', {})
                day  = snap.get('day', {})
                prev = snap.get('prevDay', {})
                price    = day.get('c') or snap.get('last', {}).get('price')
                prev_c   = prev.get('c')
                chg_pct  = round((price - prev_c) / prev_c * 100, 2) if price and prev_c else None
                results[ticker] = {
                    'price':   price,
                    'chg_pct': chg_pct,
                    'volume':  day.get('v'),
                }
        except Exception:
            results[ticker] = {'price': None, 'chg_pct': None, 'volume': None}

    return jsonify(results)

