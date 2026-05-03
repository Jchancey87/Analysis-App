# Force non-interactive matplotlib backend before any other imports
import matplotlib
matplotlib.use('Agg')

from services.chart_service_research import build_session_chart
import yfinance as yf
import os

df = yf.download("TSLA", period="1d", interval="5m")
if not df.empty:
    df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    print(f"Data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(df.head(3))
    try:
        path = build_session_chart("TSLA", "2026-05-02", df, "testjob2", "/tmp")
        print(f"Success: {path}")
        print(f"File exists: {os.path.exists(path)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed: {e}")
else:
    print("Empty dataframe")
