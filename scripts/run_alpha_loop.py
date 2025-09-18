#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA
import warnings
import logging
import pyarrow.dataset as ds
from datetime import date

warnings.filterwarnings('ignore')

# --- 構造化ロギングの設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- 設定項目 ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
PARQUET_DATA_PATH = "gs://project-orion-admins-orion-raw-storage/finnhub-datasets/"
CONFIG_COLLECTION = "orion_system_config"
CORE_THESIS_DOC_ID = "dynamic_core_thesis"

# --- クライアント初期化 ---
try:
    vertexai.init(project=PROJECT_ID, location="asia-northeast1")
    db = firestore.Client()
except Exception as e:
    logging.critical("Failed to initialize GCP clients.", exc_info=True)
    raise

def load_market_data_from_gcs(gcs_path: str, year: int, month: int) -> pd.DataFrame:
    """述語プッシュダウンを利用してGCS上のParquetデータセットから効率的にデータを読み込む"""
    try:
        logging.info(f"Loading data for {year}-{month:02d} from {gcs_path}")
        dataset = ds.dataset(gcs_path, format='parquet', partitioning=['year', 'month'])
        filter_expression = (ds.field('year') == year) & (ds.field('month') == month)
        table = dataset.scanner(filter=filter_expression).to_table()
        df = table.to_pandas()
        
        df.rename(columns={
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }, inplace=True)
        
        df['timestamp'] = pd.to_datetime(df['ts_event'])
        df.set_index('timestamp', inplace=True)

        logging.info(f"Successfully loaded {len(df)} rows for {len(df['symbol'].unique())} symbols.")
        return df
    except Exception:
        logging.error(
            "Failed to load market data from Parquet dataset. Check bucket name, path, and IAM permissions.", 
            exc_info=True,
            extra={'gcs_path': gcs_path, 'year': year, 'month': month}
        )
        raise

def run_alpha_generation_pilot():
    """alpha生成ループを最適化されたデータソースで実行する"""
    logging.info("Starting Alpha Generation Pilot Run (Optimized v2)...")

    # --- Step A: Load Optimized Data from GCS ---
    try:
        analysis_year = 1992
        analysis_month = 1
        df_full = load_market_data_from_gcs(PARQUET_DATA_PATH, analysis_year, analysis_month)
        
        if df_full.empty:
            logging.error(f"No data found for {analysis_year}-{analysis_month:02d}. Aborting pilot run.")
            return
            
        df = df_full[df_full['symbol'] == 'AAPL'].copy()
        if df.empty:
            first_symbol = df_full['symbol'].unique()[0]
            logging.warning(f"AAPL data not found. Using first available symbol: {first_symbol}")
            df = df_full[df_full['symbol'] == first_symbol].copy()

    except Exception as e:
        logging.critical(f"Data loading step failed. Aborting job. Error: {e}")
        return

    # --- Step B: Run Backtest ---
    logging.info(f"Running backtest on {len(df)} rows of data...")
    class SmaCross(Strategy):
        n1, n2 = 10, 20
        def init(self):
            self.sma1 = self.I(SMA, self.data.Close, self.n1)
            self.sma2 = self.I(SMA, self.data.Close, self.n2)
        def next(self):
            if crossover(self.sma1, self.sma2): self.buy()
            elif crossover(self.sma2, self.sma1): self.sell()

    bt = Backtest(df, SmaCross, cash=100000, commission=.002)
    stats = bt.run()
    logging.info(f"Backtest complete. Stats:\n{stats}")

    # --- Step C: Distill Strategy with Gemini & Measure Tokens ---
    logging.info("Distilling strategy with Gemini (gemini-1.5-flash-001)...")
    model = GenerativeModel("gemini-1.5-flash-001")
    prompt = f"""... (prompt remains the same)..."""
    
    response = model.generate_content(prompt)
    usage_metadata = response.usage_metadata
    
    input_tokens = usage_metadata.prompt_token_count
    output_tokens = usage_metadata.candidates_token_count
    total_tokens = usage_metadata.total_token_count
    
    logging.info(
        "Token Usage Measured", 
        extra={'input': input_tokens, 'output': output_tokens, 'total': total_tokens}
    )
    print("--- TOKEN USAGE ---")
    print(f"Input Tokens: {input_tokens}")
    print(f"Output Tokens: {output_tokens}")
    print(f"Total Tokens: {total_tokens}")
    print("---------------------")

    new_core_thesis = response.text
    logging.info(f"Generated New Core Thesis:\n{new_core_thesis}")

    # --- Step D: Update Core Thesis in Firestore ---
    logging.info("Updating core thesis in Firestore...")
    doc_ref = db.collection(CONFIG_COLLECTION).document(CORE_THESIS_DOC_ID)
    doc_ref.set({
        'thesis_text': new_core_thesis,
        'last_updated': firestore.SERVER_TIMESTAMP,
        'source': 'alpha_generation_pilot_run_optimized_v3',
        'token_usage': {'input': input_tokens, 'output': output_tokens, 'total': total_tokens}
    })
    logging.info("Firestore update complete.")
    logging.info("Pilot run finished successfully!")

if __name__ == "__main__":
    run_alpha_generation_pilot()