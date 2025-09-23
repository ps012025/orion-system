import os
import finnhub
import pandas as pd
from google.cloud import bigquery
from datetime import datetime, timedelta

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
DATASET_ID = "orion_datalake"
TABLE_ID = "finnhub_news"

# --- Main Logic for Cloud Run Job ---
def main():
    print("Orion News Fetcher v3 (Cloud Run Job) activated...")
    try:
        finnhub_api_key = os.environ.get("FINNHUB_API_KEY")

        if not finnhub_api_key:
            print("ERROR: FINNHUB_API_KEY environment variable is not set.")
            raise ValueError("FINNHUB_API_KEY not set")

        print("Fetching news from Finnhub API...")
        finnhub_client = finnhub.Client(api_key=finnhub_api_key)
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        news_list = finnhub_client.general_news('general', _from=start_date, to=end_date)
        
        if not news_list:
            print("No news found for the period.")
            return

        print(f"Successfully fetched {len(news_list)} news articles.")
        df = pd.DataFrame(news_list)
        df['datetime'] = pd.to_datetime(df['datetime'], unit='s', utc=True)
        
        required_columns = ['id', 'category', 'datetime', 'headline', 'source', 'summary', 'url']
        df = df[required_columns]
        df = df.drop_duplicates(subset=['id'])

        if not df.empty:
            print(f"Writing {len(df)} unique rows to BigQuery table...")
            client = bigquery.Client(project=PROJECT_ID)
            table_ref = client.dataset(DATASET_ID).table(TABLE_ID)

            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            
            job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()
            print("Successfully wrote data to BigQuery.")
        else:
            print("No new unique news to write.")

        print("Orion News Fetcher job finished successfully.")

    except Exception as e:
        print(f"FATAL ERROR in news_fetcher job: {e}")
        raise # Re-raise the exception so the job fails

if __name__ == "__main__":
    main()