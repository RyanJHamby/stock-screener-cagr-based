"""Configuration management for the stock screener."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')

if not FINNHUB_API_KEY:
    raise ValueError("FINNHUB_API_KEY not found in environment variables. Please create a .env file.")

# Directory paths
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / 'cache'
OUTPUT_DIR = BASE_DIR / 'output'

# Create directories if they don't exist
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Cache settings (in seconds)
CACHE_EXPIRY = {
    'stock_list': 86400,  # 24 hours
    'financials': 86400,  # 24 hours
    'metrics': 43200,     # 12 hours
    'price': 3600,        # 1 hour
    'insider': 86400,     # 24 hours
    'estimates': 43200,   # 12 hours
}

# API rate limiting (free tier: 60 calls/minute)
API_CALLS_PER_MINUTE = 55  # Slightly below limit for safety
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 2  # seconds

# Scoring weights
SCORING_WEIGHTS = {
    'revenue_cagr': 0.30,
    'eps_cagr': 0.30,
    'fcf_margin_growth': 0.15,
    'roic_roe': 0.10,
    'insider_analyst': 0.10,
    'acceleration': 0.05,
}

# Moat proxy thresholds
MOAT_THRESHOLDS = {
    'high_roic': 15.0,      # ROIC > 15%
    'min_gross_margin': 30.0,  # Gross margin > 30%
    'min_revenue_cagr': 10.0,  # Revenue CAGR > 10%
}

# Stock universe filters
MIN_MARKET_CAP = 100_000_000  # $100M minimum
MIN_TRADING_VOLUME = 50000    # 50k shares daily average

# Historical data periods
HISTORICAL_YEARS = 5

# Thematic classification keywords
THEMATIC_KEYWORDS = {
    'AI': ['artificial intelligence', 'machine learning', 'ai', 'neural', 'deep learning'],
    'Semiconductors': ['semiconductor', 'chip', 'microchip', 'processor', 'gpu', 'cpu'],
    'Energy Infrastructure': ['energy', 'power', 'electricity', 'renewable', 'solar', 'wind', 'battery'],
}

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
