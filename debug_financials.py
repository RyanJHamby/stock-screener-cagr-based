#!/usr/bin/env python3
"""Debug script to check financial data extraction"""

import json
from fetch_data import get_fetcher
from price_data import build_financial_series

fetcher = get_fetcher()

symbol = "NVDA"
print(f"\n{'='*80}")
print(f"Financial Data Debug: {symbol}")
print(f"{'='*80}\n")

financials_reported = fetcher.get_financials_reported(symbol)
basic_financials = fetcher.get_basic_financials(symbol)

print(f"Financials Reported: {len(financials_reported.get('data', [])) if financials_reported else 0} reports")
print(f"Basic Financials: {'Yes' if basic_financials else 'No'}")

financials = build_financial_series(financials_reported, basic_financials)

print(f"\nBuilt Financial Series: {len(financials)} years\n")

for f in financials:
    year = f.get('year')
    revenue = f.get('revenue')
    margin = f.get('operating_margin')
    print(f"  {year}: Revenue={revenue}, Operating Margin={margin}")

if len(financials) >= 6:
    sorted_fin = sorted(financials, key=lambda x: x['year'])
    start_rev = sorted_fin[-6].get('revenue')
    end_rev = sorted_fin[-1].get('revenue')

    if start_rev and end_rev and start_rev > 0:
        revenue_cagr = ((end_rev / start_rev) ** (1/5) - 1) * 100
        print(f"\n5-Year Revenue CAGR: {revenue_cagr:.2f}%")
    else:
        print(f"\nCannot calculate CAGR: start_rev={start_rev}, end_rev={end_rev}")
else:
    print(f"\nInsufficient data for 5-year CAGR (need 6 years, have {len(financials)})")
