import os
import pandas as pd
import numpy as np
from google.cloud import firestore, bigquery
from flask import Flask, jsonify
from datetime import datetime

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins") # Get from env
REPORTS_COLLECTION = "orion-analysis-reports"
BQ_DATASET = "orion_datalake"
MARKET_TABLE = "market_data_history"

# --- Clients ---
db = firestore.Client(project=PROJECT_ID)
bq_client = bigquery.Client(project=PROJECT_ID)

@app.route("/", methods=["POST"])
def analyze_portfolio_correlation_v3():
    print("Quantitative analyzer v3 (BigQuery Data Lake Native) activated.")
    
    try:
        docs = db.collection("orion-portfolio-positions").stream()
        symbols = [doc.to_dict().get('symbol') for doc in docs if doc.to_dict().get('symbol')]
        
        if not symbols:
            print("No symbols in portfolio. Exiting.")
            return jsonify({"status": "success", "message": "No symbols in portfolio."} ), 200
        
        print(f"Analyzing symbols: {symbols}")

        # --- Fetch data from BigQuery Data Lake ---
        ticker_list_str = ", ".join([f"'{s}'" for s in symbols])
        query = f"""
            SELECT timestamp, symbol, close
            FROM `{PROJECT_ID}.{BQ_DATASET}.{MARKET_TABLE}`
            WHERE symbol IN ({ticker_list_str})
            ORDER BY timestamp
        """
        combined_df = bq_client.query(query).to_dataframe()

        if combined_df.empty:
            raise ValueError("No historical data found for portfolio symbols in BigQuery.")

        # --- Process and Analyze ---
        price_pivot = combined_df.pivot_table(index='timestamp', columns='symbol', values='close')
        price_pivot.index = pd.to_datetime(price_pivot.index)
        
        daily_returns = price_pivot.resample('D').last().pct_change().dropna()
        correlation_matrix = daily_returns.corr()
        
        print("Portfolio Correlation Matrix:\n", correlation_matrix)

        report_data = {
            "type": "quantitative_analysis_v3",
            "created_at": firestore.SERVER_TIMESTAMP,
            "correlation_matrix": correlation_matrix.to_json(),
            "analyzed_symbols": symbols,
            "data_source": f"bigquery:{BQ_DATASET}.{MARKET_TABLE}"
        }
        db.collection(REPORTS_COLLECTION).add(report_data)

        print("Successfully stored quantitative analysis report.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"An error occurred in quant analyzer: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
