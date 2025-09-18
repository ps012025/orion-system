import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import pandas as pd
from google.cloud import firestore
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel
import yaml

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
LOCATION = "asia-northeast1"
BQ_DATASET = "orion_datalake"
MARKET_TABLE = "market_data_history"
MACRO_TABLE = "macro_data_history"
REPORTS_COLLECTION = "orion-analysis-reports"

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
bq_client = bigquery.Client(project=PROJECT_ID)
db = firestore.Client(project=PROJECT_ID)
model = GenerativeModel("gemini-1.5-flash-001")

# --- Configuration Loading ---
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Data Fetching from Data Lake ---
def fetch_data_from_datalake(config: dict) -> pd.DataFrame:
    print("Fetching data from BigQuery data lake...")

    macro_series_ids = config.get('macro_analyzer_config', {}).get('fred_series_ids', [])
    market_symbols = config.get('macro_analyzer_config', {}).get('market_symbols', [])
    if not macro_series_ids or not market_symbols:
        raise ValueError("No series or symbols defined in config.")

    days_to_fetch = 365 * 2
    start_date = (datetime.now() - timedelta(days=days_to_fetch)).strftime('%Y-%m-%d')

    market_query = f"""
        SELECT timestamp, symbol, close
        FROM `{PROJECT_ID}.{BQ_DATASET}.{MARKET_TABLE}`
        WHERE symbol IN ('{"', '".join(market_symbols)}')
        AND DATE(timestamp) >= '{start_date}'
    """
    macro_query = f"""
        SELECT timestamp, series_id, value
        FROM `{PROJECT_ID}.{BQ_DATASET}.{MACRO_TABLE}`
        WHERE series_id IN ('{"', '".join(macro_series_ids)}')
        AND DATE(timestamp) >= '{start_date}'
    """

    print(f"Running market query: {market_query}")
    print(f"Running macro query: {macro_query}")

    market_df = bq_client.query(market_query).to_dataframe()
    macro_df = bq_client.query(macro_query).to_dataframe()

    if market_df.empty or macro_df.empty:
        raise ValueError("Could not retrieve sufficient data from the data lake.")

    market_pivot = market_df.pivot(index='timestamp', columns='symbol', values='close')
    macro_pivot = market_df.pivot(index='timestamp', columns='series_id', values='value')

    combined_df = pd.concat([market_pivot, macro_pivot], axis=1).ffill().dropna()
    print(f"Successfully fetched and combined {len(combined_df)} rows of data.")
    return combined_df

@app.route("/", methods=["POST"])
def analyze_macro_environment_v5():
    try:
        print("Macro analyzer v5 (Configurable & Data Lake Native) activated...")
        config = load_config()
        combined_df = fetch_data_from_datalake(config)

        daily_returns = combined_df.pct_change().dropna()
        correlation_matrix = daily_returns.corr()
        print("Correlation Matrix:\n", correlation_matrix)

        prompt = f"""

あなたはシニアマクロ経済アナリストです。以下の最新マクロ経済指標と市場データの相関行列を分析してください。

        相関行列:
          {correlation_matrix.to_string()}

    1 
    2         
      この分析に基づき、以下の項目について、プロフェッショナルな視点から簡潔なインサイトを生成してください。
    3         1.  現在の市場センチメント
    4         2.  注目すべき相関の変化
    5         3.  ポートフォリオへの戦略的示唆
    6         """
        analysis_response = model.generate_content(prompt)
        print("AI analysis generated.")

        report_data = {
            "type": "macro_analysis_v5",
            "created_at": firestore.SERVER_TIMESTAMP,
            "correlation_matrix": correlation_matrix.to_json(),
            "analysis_summary": analysis_response.text,
            "data_sources": [f"bigquery:{MARKET_TABLE}", f"bigquery:{MACRO_TABLE}"]
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        
        print("Successfully stored data lake-native macro analysis report.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"An error occurred in macro analyzer: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
