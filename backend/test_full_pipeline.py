import matplotlib
matplotlib.use('Agg')

from config import Config
from routes.analysis import _fetch_intraday_polygon
from services.chart_service_research import build_session_chart
import os

print(f"POLYGON_API_KEY set: {bool(Config.POLYGON_API_KEY)}")
print(f"POLYGON_API_KEY (first 8 chars): {Config.POLYGON_API_KEY[:8]}...")

# Test Polygon fetch with a recent date that should have data
test_date = "2025-01-15"
print(f"\nFetching Polygon data for TSLA on {test_date}...")
df = _fetch_intraday_polygon("TSLA", test_date)
print(f"Result shape: {df.shape}")

if not df.empty:
    print(f"First row:\n{df.head(1)}")
    print(f"Time range: {df.index[0]} to {df.index[-1]}")
    storage_dir = "/tmp/research_test"
    os.makedirs(storage_dir, exist_ok=True)
    path = build_session_chart("TSLA", test_date, df, "fulltest", storage_dir)
    print(f"\nChart saved: {path}")
    print(f"File exists: {os.path.exists(path)}, Size: {os.path.getsize(path)} bytes")
else:
    print("Empty - Polygon likely returning 401 or no data for this date")
    print("Checking raw response...")
    import requests
    url = f"https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/minute/{test_date}/{test_date}"
    params = {'adjusted': 'true', 'sort': 'asc', 'limit': 5, 'apiKey': Config.POLYGON_API_KEY}
    r = requests.get(url, params=params)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
