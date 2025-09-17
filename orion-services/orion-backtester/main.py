import os
import glob
import pandas as pd
from flask import Flask, jsonify

app = Flask(__name__)

# データソースをローカルファイルシステムからCloud Storageに変更
DATA_PATH = "gs://orion-market-data-lake/"

def load_and_preprocess_data():
    print("Starting data loading process from Cloud Storage...")
    # gsutilスタイルのワイルドカードを使用してGCS上のファイルパスを取得
    # この機能のためにgcsfsライブラリが必要
    all_files = glob.glob(os.path.join(DATA_PATH, "nasdaq100_ohlcv_1m_*.csv"))

    if not all_files:
        raise FileNotFoundError(f"No data CSVs found at GCS path: {DATA_PATH}")

    print(f"Found {len(all_files)} data files to load.")
    df_list = []
    for f in sorted(all_files):
        print(f"Loading file: {f}...")
        # pandasはgcsfsがインストールされていれば 'gs://' パスを直接読める
        df = pd.read_csv(f, low_memory=False)
        df_list.append(df)

    print("Concatenating all dataframes...")
    combined_df = pd.concat(df_list, ignore_index=True)
    print("Preprocessing data...")
    combined_df['ts_event'] = pd.to_datetime(combined_df['ts_event'])
    combined_df.set_index('ts_event', inplace=True)
    print("--- Data Loading and Preprocessing Complete ---")
    print(f"Total rows: {len(combined_df)}")
    print(f"Data time range: {combined_df.index.min()} to {combined_df.index.max()}")
    return combined_df

@app.route("/", methods=["GET"])
def handle_request():
    print("Received request to start backtester.")
    try:
        load_and_preprocess_data()
        return jsonify({"status": "success", "message": "Data loaded and preprocessed successfully from GCS."}), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
