import os
import requests
import feedparser
import json
from google.cloud import firestore, pubsub_v1
from datetime import datetime, timezone, timedelta
import hashlib
import yaml
from flask import Flask, jsonify

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
OUTPUT_TOPIC_ID = "filtered-urls-for-analysis"
FIRESTORE_COLLECTION = "orion-sec-fetcher-state"
USER_AGENT = "Orion System v8.1 SEC Fetcher/1.0 (contact: ps012025@gmail.com)"

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
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(cik)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('last_checked_utc')
    return datetime.now(timezone.utc) - timedelta(days=1)

def set_last_checked_timestamp(cik: str, timestamp: datetime):
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(cik)
    doc_ref.set({'last_checked_utc': timestamp})

def fetch_and_publish_new_filings(cik: str, company_symbol: str):
    print(f"Fetching filings for {company_symbol} (CIK: {cik})...")
    last_checked = get_last_checked_timestamp(cik)
    latest_filing_time = last_checked

    feed_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=exclude&start=0&count=40&output=atom"
    headers = {'User-Agent': USER_AGENT}
    response = requests.get(feed_url, headers=headers, timeout=20)
    response.raise_for_status()
    
    feed = feedparser.parse(response.content)
    published_count = 0

    for entry in sorted(feed.entries, key=lambda x: x.published_parsed):
        filing_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        
        if filing_time > last_checked:
            form_type = entry.get('category', '').strip()
            if form_type in ['8-K', '10-Q', '10-K', '4', '13F-HR', '13D', '13G']:
                title = entry.title
                link = entry.link
                print(f"  - Found new filing: {title} ({filing_time})")

                message_payload = {"url": link, "title": f"[{company_symbol}] {title}"}
                message_data = json.dumps(message_payload).encode('utf-8')
                
                future = publisher.publish(output_topic_path, data=message_data)
                future.get(timeout=30)
                # Notify synergy analyzer
                publisher.publish(publisher.topic_path(PROJECT_ID, 'new-atomic-insight-created'), data=json.dumps({'insight_id': 'YOUR_INSIGHT_ID'}).encode('utf-8'))
                published_count += 1

            if filing_time > latest_filing_time:
                latest_filing_time = filing_time

    if published_count > 0:
        print(f"Published {published_count} new filings for {company_symbol}.")
    else:
        print(f"No new important filings found for {company_symbol} since {last_checked}.")

    set_last_checked_timestamp(cik, latest_filing_time)

@app.route("/", methods=["POST"])
def sec_fetcher_http(request):
    print("Orion SEC Fetcher v3 (Flask) activated...")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))