"""
services/polygon_service.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Legacy shim — delegates to polygon_client (the official SDK adapter).
Kept for backwards-compat with any existing import sites.
"""
from services.polygon_client import get_ticker_details  # re-export

__all__ = ["get_ticker_details"]
