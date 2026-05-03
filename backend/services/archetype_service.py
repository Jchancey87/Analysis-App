from database import get_connection


def get_archetype_stats() -> list[dict]:
    """
    For each unique pattern tag, compute: count, avg_gain, avg_float_m, avg_rvol, avg_cleanliness.
    Returns list of dicts sorted by count desc.
    Tags are stored as JSON arrays; we explode them with multiple queries.
    """
    from services.chart_service import VALID_TAGS
    import json

    results = []

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT tags, cleanliness_score FROM chart_captures "
            "WHERE tags IS NOT NULL AND tags != '[]'"
        ).fetchall()

        # Build per-tag lists of cleanliness scores
        tag_scores: dict[str, list] = {t: [] for t in VALID_TAGS}
        for row in rows:
            try:
                tags = json.loads(row['tags'])
            except Exception:
                continue
            for tag in tags:
                if tag in tag_scores and row['cleanliness_score'] is not None:
                    tag_scores[tag].append(row['cleanliness_score'])

        # Join with daily_gainers for gain data
        gainer_rows = conn.execute(
            "SELECT cc.tags, dg.gap_pct, dg.float_shares, dg.rvol_15m "
            "FROM chart_captures cc "
            "LEFT JOIN daily_gainers dg ON cc.ticker = dg.ticker AND cc.capture_date = dg.date "
            "WHERE cc.tags IS NOT NULL AND cc.tags != '[]'"
        ).fetchall()

    tag_gains:   dict[str, list] = {t: [] for t in VALID_TAGS}
    tag_floats:  dict[str, list] = {t: [] for t in VALID_TAGS}
    tag_rvols:   dict[str, list] = {t: [] for t in VALID_TAGS}

    for row in gainer_rows:
        try:
            tags = json.loads(row['tags'])
        except Exception:
            continue
        for tag in tags:
            if tag not in VALID_TAGS:
                continue
            if row['gap_pct']      is not None: tag_gains[tag].append(row['gap_pct'])
            if row['float_shares'] is not None: tag_floats[tag].append(row['float_shares'] / 1e6)
            if row['rvol_15m']     is not None: tag_rvols[tag].append(row['rvol_15m'])

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else None

    for tag in VALID_TAGS:
        count = len(tag_scores[tag]) + (len(tag_gains[tag]) - len(tag_scores[tag]))
        count = max(len(tag_scores[tag]), len(tag_gains[tag]))
        if count == 0:
            continue
        results.append({
            'tag':              tag,
            'count':            count,
            'avg_gap_pct':      avg(tag_gains[tag]),
            'avg_float_m':      avg(tag_floats[tag]),
            'avg_rvol':         avg(tag_rvols[tag]),
            'avg_cleanliness':  avg(tag_scores[tag]),
        })

    return sorted(results, key=lambda x: x['count'], reverse=True)
