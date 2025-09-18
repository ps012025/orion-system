import os
import functions_framework
import finnhub
import json
import pandas as pd
from google.cloud import firestore, pubsub_v1, bigquery
from datetime import datetime, timezone, timedelta

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
OUTPUT_TOPIC_ID = "filtered-urls-for-analysis"
FIRESTORE_COLLECTION = "orion-news-fetcher-state"
BQ_DATASET = "orion_datalake"
BQ_NEWS_TABLE = "finnhub_news"
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")

# --- Clients ---
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
bq_client = bigquery.Client()
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC_ID)
finnhub_client = finnhub.Client(api_key=MARKET_DATA_API_KEY) if MARKET_DATA_API_KEY else None

# --- Main Logic ---
def get_last_checked_timestamp(symbol: str) -> datetime:
    # ... (logic remains the same)
    pass

def set_last_checked_timestamp(symbol: str, timestamp: datetime):
    # ... (logic remains the same)
    pass

def save_news_to_bigquery(news_data: list):
    if not news_data:
        return
    df = pd.DataFrame(news_data)
    df['datetime'] = pd.to_datetime(df['datetime'], unit='s', utc=True)
    table_ref = bq_client.dataset(BQ_DATASET).table(BQ_NEWS_TABLE)
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    job = bq_client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Successfully saved {len(df)} news articles to BigQuery.")

def fetch_and_process_news(symbol: str):
    print(f"Fetching news for {symbol}...")
    last_checked = get_last_checked_timestamp(symbol)
    latest_news_time = last_checked
    new_news_for_bq = []

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
            new_news_for_bq.append(news_item)
            # ... (publish to pub/sub logic remains the same) ...
            published_count += 1

        if news_time > latest_news_time:
            latest_news_time = news_time

    if new_news_for_bq:
        save_news_to_bigquery(new_news_for_bq)

    if published_count > 0:
        print(f"Published {published_count} new articles for {symbol}.")
    else:
        print(f"No new articles found for {symbol} since {last_checked}.")

    set_last_checked_timestamp(symbol, latest_news_time)

@functions_framework.http
def news_fetcher_http(request):
    # ... (logic remains the same, but calls fetch_and_process_news)
    pass