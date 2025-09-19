import os
import finnhub
import pandas as pd
from google.cloud import bigquery
from flask import Flask, request
from datetime import datetime, timedelta

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

@app.route("/", methods=["POST"])
def news_fetcher_http():
    """
    Cloud Runサービスのエントリーポイント。
    HTTP POSTリクエストを受け取り、Finnhubからニュースを取得してBigQueryに書き込む。
    Cloud Schedulerからの呼び出しを想定。
    """
    try:
        # --- 設定の読み込み ---
        project_id = os.environ.get("GCP_PROJECT", "project-orion-admins")
        dataset_id = "orion_datalake"
        table_id = "finnhub_news"
        finnhub_api_key = os.environ.get("FINNHUB_API_KEY")

        if not finnhub_api_key:
            print("ERROR: FINNHUB_API_KEY environment variable is not set.")
            return "Internal Server Error", 500

        # --- Finnhub APIからニュースを取得 ---
        print("Fetching news from Finnhub API...")
        finnhub_client = finnhub.Client(api_key=finnhub_api_key)
        
        # 過去24時間分のニュースを取得
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        news_list = finnhub_client.general_news('general', _from=start_date, to=end_date)
        
        if not news_list:
            print("No news found for the period.")
            return "No news found.", 204

        # --- データの整形 ---
        print(f"Successfully fetched {len(news_list)} news articles.")
        df = pd.DataFrame(news_list)
        df['datetime'] = pd.to_datetime(df['datetime'], unit='s', utc=True)
        
        # 必要なカラムのみに絞り込み、重複を除外
        required_columns = ['id', 'category', 'datetime', 'headline', 'source', 'summary', 'url']
        df = df[required_columns]
        df = df.drop_duplicates(subset=['id'])

        # --- BigQueryへの書き込み ---
        if not df.empty:
            print(f"Writing {len(df)} unique rows to BigQuery table: {dataset_id}.{table_id}...")
            client = bigquery.Client(project=project_id)
            table_ref = client.dataset(dataset_id).table(table_id)

            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            )
            
            job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()  # 処理の完了を待つ
            print("Successfully wrote data to BigQuery.")
        else:
            print("No new unique news to write.")

        return "Success", 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"Error: {e}", 500

if __name__ == "__main__":
    # ローカルでのテスト用に、開発用サーバーを起動
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))