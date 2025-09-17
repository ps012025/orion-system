#!/usr/bin/env python
# coding: utf-8

# # Orion Alpha Generation Loop
# このスクリプトは、BigQueryの市場データレイクを分析し、
# 最適な投資戦略を導き出し、その結果をリアルタイム分析エンジン
# (`orion-insight-wrangler`)の「コアテーゼ」として自動更新します。

import os
import pandas as pd
from google.cloud import bigquery, firestore
import vertexai
from vertexai.generative_models import GenerativeModel
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA
import warnings
warnings.filterwarnings('ignore')

def run_alpha_generation():
    """Main function to execute the entire alpha generation loop."""
    # --- 設定 ---
    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
    BQ_DATASET_ID = "orion_datalake"
    BQ_TABLE_ID = "market_data_history"
    CONFIG_COLLECTION = "orion_system_config"
    CORE_THESIS_DOC_ID = "dynamic_core_thesis"

    if not PROJECT_ID:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")

    vertexai.init(project=PROJECT_ID, location="asia-northeast1")
    bq_client = bigquery.Client(project=PROJECT_ID)
    db = firestore.Client()

    # ### ステップA: データレイクから履歴データを取得
    print("BigQueryデータレイクから市場データをロードしています...")
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM `{PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}`
        WHERE symbol = 'AAPL' -- バックテスト対象をAAPLに限定
        ORDER BY timestamp
    """
    df = bq_client.query(query).to_dataframe()
    if df.empty:
        print("Warning: No data found in BigQuery. Exiting loop.")
        return

    df.set_index('timestamp', inplace=True)
    df.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    }, inplace=True)

    print(f"{len(df)}行のデータをロードしました。")

    # ### ステップB: バックテストの実行
    print("バックテストを実行しています...")
    class SmaCross(Strategy):
        n1 = 10
        n2 = 20
        def init(self):
            close = self.data.Close
            self.sma1 = self.I(SMA, close, self.n1)
            self.sma2 = self.I(SMA, close, self.n2)
        def next(self):
            if crossover(self.sma1, self.sma2):
                self.buy()
            elif crossover(self.sma2, self.sma1):
                self.sell()

    bt = Backtest(df, SmaCross, cash=100000, commission=.002)
    stats = bt.run()
    print("バックテスト結果:")
    print(stats)

    # ### ステップC: Geminiによる戦略の蒸留
    print("Geminiによる戦略の蒸留を開始... (using gemini-1.5-flash-001)")
    model = GenerativeModel("gemini-1.5-flash-001")

    prompt = f"""
    以下のバックテスト結果を分析し、この結果から導き出される最も効果的な投資戦略を、
    orion-insight-wranglerがリアルタイムニュース分析に利用するための「コアテーゼ」として、
    簡潔な自然言語の段落で要約・抽出してください。

    バックテスト結果:
    {stats}

    あなたの分析に基づいた新しいコアテーゼを生成してください:
    """

    response = model.generate_content(prompt)
    new_core_thesis = response.text
    print("\n生成された新しいコアテーゼ:")
    print(new_core_thesis)

    # ### ステップD: 動的再構成
    print("Firestoreのコアテーゼを更新しています...")
    doc_ref = db.collection(CONFIG_COLLECTION).document(CORE_THESIS_DOC_ID)
    doc_ref.set({
        'thesis_text': new_core_thesis,
        'last_updated': firestore.SERVER_TIMESTAMP,
        'source': 'alpha_generation_loop'
    })
    print("更新が完了しました。orion-insight-wranglerは次回の実行から新しい戦略を使用します。")

if __name__ == "__main__":
    run_alpha_generation()
