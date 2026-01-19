#!/usr/bin/env python3
"""Debug script to check raw Finnhub financial data"""

import json
from fetch_data import get_fetcher

fetcher = get_fetcher()

symbol = "NVDA"
print(f"\n{'='*80}")
print(f"Raw Finnhub Financial Data: {symbol}")
print(f"{'='*80}\n")

financials_reported = fetcher.get_financials_reported(symbol)

if financials_reported and 'data' in financials_reported:
    print(f"Total reports: {len(financials_reported['data'])}\n")

    for report in financials_reported['data'][-5:]:
        year = report.get('year')
        print(f"\nYear: {year}")
        print(f"Report keys: {list(report.keys())}")

        if 'report' in report:
            report_data = report['report']
            print(f"Report sections: {list(report_data.keys())}")

            for section in ['ic', 'is']:
                if section in report_data:
                    print(f"\n  {section.upper()} section ({len(report_data[section])} items):")
                    revenue_items = [item for item in report_data[section]
                                   if 'revenue' in item.get('concept', '').lower()]
                    for item in revenue_items[:3]:
                        concept = item.get('concept', 'Unknown')
                        value = item.get('value', 'None')
                        print(f"    - {concept}: {value}")
else:
    print("No financials_reported data available")

print("\n" + "="*80 + "\n")

basic_financials = fetcher.get_basic_financials(symbol)
if basic_financials and 'series' in basic_financials:
    annual_series = basic_financials['series'].get('annual', {})
    print(f"Basic Financials Annual Series metrics: {list(annual_series.keys())}\n")
