#!/bin/bash
# Helper script to run the stock screener with the virtual environment

# Activate virtual environment
source venv/bin/activate

# Run the screener with any arguments passed to this script
python main.py "$@"
