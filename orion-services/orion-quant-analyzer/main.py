import os
import pandas as pd
import numpy as np
from google.cloud import firestore
from google.cloud import storage
from flask import Flask, jsonify

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "thinking-orb-438805-q7")
REPORTS_COLLECTION = "orion-analysis-reports"
# PORTFOLIO_COLLECTION is read from firestore, not needed here

# GCS_BUCKET_NAME is now read from an environment variable
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# --- Clients ---
db = firestore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

@app.route("/", methods=["POST"])
def analyze_portfolio_correlation():
    print("Quantitative analyzer v2 (dynamic bucket) activated.")
    
    if not GCS_BUCKET_NAME:
        error_message = "GCS_BUCKET_NAME environment variable is not set."
        print(f"FATAL: {error_message}")
        return jsonify({"error": error_message}), 500

    try:
        # This service reads the portfolio from orion-portfolio-positions, not orion-portfolio-holdings
        docs = db.collection("orion-portfolio-positions").stream()
        symbols = [doc.to_dict().get('symbol') for doc in docs if doc.to_dict().get('symbol')]
        
        if not symbols:
            print("No symbols in portfolio. Exiting.")
            return jsonify({"status": "success", "message": "No symbols in portfolio."} ), 200
        
        print(f"Analyzing symbols: {symbols}")

        blobs = storage_client.list_blobs(GCS_BUCKET_NAME, prefix="nasdaq100_ohlcv_1m_")
        
        df_list = []
        for blob in blobs:
            print(f"Loading data from gs://{GCS_BUCKET_NAME}/{blob.name}...")
            # Use pandas to read directly from GCS
            df = pd.read_csv(f"gs://{GCS_BUCKET_NAME}/{blob.name}")
            df_list.append(df)
        
        if not df_list:
            raise ValueError(f"No data files with prefix 'nasdaq100_ohlcv_1m_' found in bucket '{GCS_BUCKET_NAME}'.")

        combined_df = pd.concat(df_list, ignore_index=True)
        
        portfolio_df = combined_df[combined_df['symbol'].isin(symbols)]
        price_pivot = portfolio_df.pivot_table(index='ts_event', columns='symbol', values='close')
        price_pivot.index = pd.to_datetime(price_pivot.index)
        
        daily_returns = price_pivot.resample('D').last().pct_change().dropna()
        correlation_matrix = daily_returns.corr()
        
        print("Portfolio Correlation Matrix:\n", correlation_matrix)

        report_data = {
            "type": "quantitative_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
            "correlation_matrix": correlation_matrix.to_json(),
            "analyzed_symbols": symbols
        }
        db.collection(REPORTS_COLLECTION).add(report_data)

        print("Successfully stored quantitative analysis report.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"An error occurred in quant analyzer: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
