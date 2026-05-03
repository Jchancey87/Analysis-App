from config import Config
from routes.analysis import _fetch_intraday_polygon
import os

df = _fetch_intraday_polygon("TSLA", "2024-04-15")
print(f"Data shape: {df.shape}")
if not df.empty:
    print(df.head())
else:
    print("Empty dataframe returned by Polygon")
