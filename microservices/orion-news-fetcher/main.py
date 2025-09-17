import os
import functions_framework
import finnhub
import json
from google.cloud import firestore, pubsub_v1
from datetime import datetime, timezone, timedelta

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
OUTPUT_TOPIC_ID = "filtered-urls-for-analysis"
FIRESTORE_COLLECTION = "orion-news-fetcher-state"
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")

# --- Clients ---
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC_ID)
finnhub_client = finnhub.Client(api_key=MARKET_DATA_API_KEY) if MARKET_DATA_API_KEY else None

# --- Main Logic ---
def get_last_checked_timestamp(symbol: str) -> datetime:
    """Gets the last checked timestamp for a given symbol from Firestore."""
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(symbol)
    doc = doc_ref.get()
    if doc.exists:
        # Firestore stores timestamps as datetime objects with UTC timezone
        return doc.to_dict().get('last_checked_utc')
    # If no record, check news from the last hour to avoid initial flood
    return datetime.now(timezone.utc) - timedelta(hours=1)

def set_last_checked_timestamp(symbol: str, timestamp: datetime):
    """Sets the last checked timestamp for a given symbol in Firestore."""
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(symbol)
    doc_ref.set({'last_checked_utc': timestamp})

def fetch_and_publish_news(symbol: str):
    """Fetches news from Finnhub for a symbol and publishes new articles."""
    print(f"Fetching news for {symbol}...")
    last_checked = get_last_checked_timestamp(symbol)
    latest_news_time = last_checked

    # Finnhub uses date strings (YYYY-MM-DD), not timestamps, for the news endpoint
    # We fetch news for the last 7 days to be safe and filter by timestamp in our code
    _from = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    _to = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        company_news = finnhub_client.company_news(symbol, _from=_from, to=_to)
    except Exception as e:
        print(f"  - Error fetching news for {symbol} from Finnhub: {e}")
        return

    if not company_news:
        print(f"No news found for {symbol} in the last 7 days.")
        set_last_checked_timestamp(symbol, datetime.now(timezone.utc))
        return

    published_count = 0
    for news_item in sorted(company_news, key=lambda x: x['datetime']):
        news_time = datetime.fromtimestamp(news_item['datetime'], tz=timezone.utc)

        if news_time > last_checked:
            title = news_item['headline']
            url = news_item['url']
            print(f"  - Found new article: {title} ({news_time})")

            message_payload = {"url": url, "title": title}
            message_data = json.dumps(message_payload).encode('utf-8')
            
            future = publisher.publish(output_topic_path, data=message_data)
            future.get(timeout=30)
            published_count += 1

        if news_time > latest_news_time:
            latest_news_time = news_time

    if published_count > 0:
        print(f"Published {published_count} new articles for {symbol}.")
    else:
        print(f"No new articles found for {symbol} since {last_checked}.")

    set_last_checked_timestamp(symbol, latest_news_time)

@functions_framework.http
def news_fetcher_http(request):
    """HTTP-triggered function to fetch news for all portfolio companies."""
    print("Orion News Fetcher activated...")
    if not finnhub_client:
        return "MARKET_DATA_API_KEY is not set.", 500

    try:
        positions = db.collection("orion-portfolio-positions").stream()
        portfolio_symbols = {pos.to_dict().get('symbol') for pos in positions if pos.to_dict().get('symbol')}

        for symbol in portfolio_symbols:
            fetch_and_publish_news(symbol)
        
        return "News Fetcher finished successfully.", 200

    except Exception as e:
        print(f"ERROR: An unexpected error occurred in News Fetcher: {e}")
        return "Internal Server Error", 500
