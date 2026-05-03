from services.chart_service_research import build_session_chart
import yfinance as yf
import os

df = yf.download("TSLA", period="1d", interval="1m")
if not df.empty:
    df.columns = df.columns.get_level_values(0)
    # yfinance columns are Open, High, Low, Close, Volume. We need lower case.
    df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    try:
        path = build_session_chart("TSLA", "today", df, "testjob", "/tmp")
        print(f"Success: {path}")
    except Exception as e:
        print(f"Failed: {e}")
else:
    print("Empty dataframe")
