import matplotlib
matplotlib.use('Agg')

import yfinance as yf
from datetime import datetime, timedelta
from services.chart_service_research import build_session_chart
import os

# Simulate what the backend does for today
date = "2026-05-02"
start_dt = datetime.strptime(date, '%Y-%m-%d')
end_dt = start_dt + timedelta(days=1)

print(f"Fetching yfinance 1m data for TSLA from {start_dt.date()} to {end_dt.date()}...")
yf_df = yf.download("TSLA", start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'), interval='1m', prepost=True, progress=False)
print(f"Raw shape: {yf_df.shape}")
print(f"Raw columns: {yf_df.columns.tolist()}")

if not yf_df.empty:
    # Handle MultiIndex columns from yfinance
    if hasattr(yf_df.columns, 'levels'):
        yf_df.columns = yf_df.columns.get_level_values(0)
    yf_df = yf_df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    print(f"Processed shape: {yf_df.shape}, rows: {len(yf_df)}")
    print(f"Columns: {yf_df.columns.tolist()}")
    
    storage_dir = "/tmp/research_test"
    os.makedirs(storage_dir, exist_ok=True)
    try:
        path = build_session_chart("TSLA", date, yf_df, "yftest", storage_dir)
        print(f"Chart saved: {path}, size: {os.path.getsize(path)} bytes")
    except Exception as e:
        import traceback
        traceback.print_exc()
