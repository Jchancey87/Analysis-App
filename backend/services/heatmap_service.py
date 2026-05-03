import pandas as pd
from database import get_connection

FLOAT_BINS   = [0, 5e6, 10e6, 50e6, float('inf')]
FLOAT_LABELS = ['<5M', '5–10M', '10–50M', '50M+']

RVOL_BINS    = [0, 3, 5, 10, float('inf')]
RVOL_LABELS  = ['<3x', '3–5x', '5–10x', '10x+']


def build_heatmap_spec() -> dict:
    """
    Query daily_gainers, bucket float and RVOL, compute average gap_pct per cell.
    Returns a Plotly-compatible figure dict ready to JSON-serialize.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT float_shares, rvol_15m, gap_pct FROM daily_gainers "
            "WHERE float_shares IS NOT NULL AND rvol_15m IS NOT NULL AND gap_pct IS NOT NULL"
        ).fetchall()

    if not rows:
        return _empty_heatmap()

    df = pd.DataFrame([dict(r) for r in rows])
    df['float_bucket'] = pd.cut(df['float_shares'], bins=FLOAT_BINS, labels=FLOAT_LABELS, right=False)
    df['rvol_bucket']  = pd.cut(df['rvol_15m'],     bins=RVOL_BINS,  labels=RVOL_LABELS,  right=False)

    pivot = (
        df.groupby(['rvol_bucket', 'float_bucket'], observed=True)['gap_pct']
        .mean()
        .unstack(fill_value=None)
        .reindex(index=RVOL_LABELS[::-1], columns=FLOAT_LABELS)
    )

    z      = pivot.values.tolist()
    x      = FLOAT_LABELS
    y      = RVOL_LABELS[::-1]

    return {
        'data': [{
            'type':        'heatmap',
            'z':           z,
            'x':           x,
            'y':           y,
            'colorscale':  [
                [0.0,  '#c0392b'],
                [0.4,  '#f39c12'],
                [0.7,  '#27ae60'],
                [1.0,  '#1a5e36'],
            ],
            'colorbar': {'title': 'Avg Gap %'},
            'hovertemplate': 'Float: %{x}<br>RVOL: %{y}<br>Avg Gap: %{z:.1f}%<extra></extra>',
        }],
        'layout': {
            'title': 'Float × RVOL Avg Gap % Heatmap',
            'xaxis': {'title': 'Float Size'},
            'yaxis': {'title': 'RVOL at 15-min'},
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor':  'rgba(0,0,0,0)',
            'font': {'color': '#e2e8f0'},
        },
    }


def _empty_heatmap() -> dict:
    return {
        'data': [{'type': 'heatmap', 'z': [], 'x': FLOAT_LABELS, 'y': RVOL_LABELS}],
        'layout': {'title': 'No data yet — run the ingestion job first'},
    }
