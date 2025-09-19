import os
import finnhub
import pandas as pd
from google.cloud import bigquery
from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route("/", methods=["POST"])
def news_fetcher_http():
    try:
        project_id = os.environ.get("GCP_PROJECT", "project-orion-admins")
        dataset_id = "orion_datalake"
        table_id = "finnhub_news"
        finnhub_api_key = os.environ.get("FINNHUB_API_KEY")

        if not finnhub_api_key:
            print("ERROR: FINNHUB_API_KEY environment variable is not set.")
            return "Internal Server Error: FINNHUB_API_KEY not set", 500

        print("Fetching news from Finnhub API...")
        finnhub_client = finnhub.Client(api_key=finnhub_api_key)
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        news_list = finnhub_client.general_news('general', _from=start_date, to=end_date)
        
        if not news_list:
            print("No news found for the period.")
            return "No news found.", 204

        print(f"Successfully fetched {len(news_list)} news articles.")
        df = pd.DataFrame(news_list)
        df['datetime'] = pd.to_datetime(df['datetime'], unit='s', utc=True)
        
        required_columns = ['id', 'category', 'datetime', 'headline', 'source', 'summary', 'url']
        df = df[required_columns]
        df = df.drop_duplicates(subset=['id'])

        if not df.empty:
            print(f"Writing {len(df)} unique rows to BigQuery table...")
            client = bigquery.Client(project=project_id)
            table_ref = client.dataset(dataset_id).table(table_id)

            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            
            job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()
            print("Successfully wrote data to BigQuery.")
        else:
            print("No new unique news to write.")

        return "Success", 200

    except Exception as e:
        print(f"FATAL ERROR in news_fetcher_http: {e}")
        # Return a more detailed error message to help debugging
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
