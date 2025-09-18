import os
import requests
import feedparser
import json
from google.cloud import firestore, pubsub_v1
from datetime import datetime, timezone, timedelta
import hashlib
import yaml
import functions_framework

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
OUTPUT_TOPIC_ID = "filtered-urls-for-analysis"
FIRESTORE_COLLECTION = "orion-sec-fetcher-state"
USER_AGENT = "Orion System v8.0 SEC Fetcher/1.0 (contact: ps012025@gmail.com)"

# --- Clients ---
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC_ID)

# --- Configuration Loading ---
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Main Logic ---
def get_last_checked_timestamp(cik: str) -> datetime:
    # ... (logic remains the same)
    pass

def set_last_checked_timestamp(cik: str, timestamp: datetime):
    # ... (logic remains the same)
    pass

def fetch_and_publish_new_filings(cik: str, company_symbol: str):
    # ... (logic remains the same)
    pass

@functions_framework.http
def sec_fetcher_http(request):
    print("Orion SEC Fetcher v3 (Function) activated...")
    try:
        config = load_config()
        ticker_to_cik = config.get('sec_fetcher_config', {}).get('ticker_to_cik', {})
        if not ticker_to_cik:
            print("Warning: Ticker-to-CIK mapping not found in config. Exiting.")
            return "No CIK mapping configured.", 200

        positions = db.collection("orion-portfolio-positions").stream()
        portfolio_symbols = {pos.to_dict().get('symbol') for pos in positions}

        for symbol in portfolio_symbols:
            if symbol in ticker_to_cik:
                fetch_and_publish_new_filings(ticker_to_cik[symbol], symbol)
            else:
                print(f"Warning: No CIK found for symbol: {symbol}. Skipping.")
        
        return "SEC Fetcher finished successfully.", 200

    except Exception as e:
        print(f"ERROR: An unexpected error occurred in SEC Fetcher: {e}")
        return "Internal Server Error", 500