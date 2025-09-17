import os
import pandas as pd
from google.cloud import firestore, bigquery
import vertexai
from vertexai.generative_models import GenerativeModel
from flask import Flask, jsonify
from datetime import datetime, timedelta
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

    market_query = f"""SELECT timestamp, symbol, close FROM `{PROJECT_ID}.{BQ_DATASET}.{MARKET_TABLE}` WHERE symbol IN ('{str(market_symbols)[1:-1]}') AND DATE(timestamp) >= '{start_date}'"""
    macro_query = f"""SELECT timestamp, series_id, value FROM `{PROJECT_ID}.{BQ_DATASET}.{MACRO_TABLE}` WHERE series_id IN ('{str(macro_series_ids)[1:-1]}') AND DATE(timestamp) >= '{start_date}'"""

    market_df = bq_client.query(market_query).to_dataframe()
    macro_df = bq_client.query(macro_query).to_dataframe()

    if market_df.empty or macro_df.empty:
        raise ValueError("Could not retrieve sufficient data from the data lake.")

    market_pivot = market_df.pivot(index='timestamp', columns='symbol', values='close')
    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

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

        prompt = f"..." # Prompt remains the same
        analysis_response = model.generate_content(prompt)

        report_data = {
            "type": "macro_analysis_v5",
            "created_at": firestore.SERVER_TIMESTAMP,
            "correlation_matrix": correlation_matrix.to_json(),
            "analysis_summary": analysis_response.text,
            "data_sources": [f"bigquery:{MARKET_TABLE}", f"bigquery:{MACRO_TABLE}"]
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"An error occurred in macro analyzer: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
