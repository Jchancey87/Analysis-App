import sys
import json
import os
from pprint import pprint

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.fmp_service import (
    get_company_profile,
    get_key_metrics,
    get_earnings_calendar,
    get_income_statement,
    get_insider_transactions,
    get_cash_position,
    get_stock_news
)

def test_fmp(ticker):
    print(f"--- Testing FMP Data for {ticker} ---\n")
    
    print("1. Company Profile:")
    profile = get_company_profile(ticker)
    print(json.dumps(profile, indent=2))
    print("\n")
    
    print("2. Key Metrics (TTM):")
    metrics = get_key_metrics(ticker)
    print(json.dumps(metrics, indent=2))
    print("\n")
    
    print("3. Income Statement (Last 4 Quarters):")
    income = get_income_statement(ticker)
    print(json.dumps(income, indent=2))
    print("\n")
    
    print("4. Cash Position (Last Quarter):")
    cash = get_cash_position(ticker)
    print(json.dumps(cash, indent=2))
    print("\n")
    
    print("5. Earnings Calendar:")
    earnings = get_earnings_calendar(ticker)
    print(json.dumps(earnings, indent=2))
    print("\n")

if __name__ == "__main__":
    test_fmp('LUNR')
