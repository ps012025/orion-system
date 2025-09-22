import databento as db
from google.cloud import bigquery
import pandas as pd
import os
from datetime import datetime, timezone, timedelta

def rebuild_datalake():
    api_key = os.environ.get('DATABENTO_API_KEY')
    if not api_key:
        print("エラー: 環境変数 DATABENTO_API_KEY が設定されていません。")
        return

    client = db.Historical(key=api_key)

    print("Databentoから過去のデータを取得しています... これには時間がかかる場合があります。")

    end_date_str = '2024-12-31T23:59:59Z'

    data = client.timeseries.get_range(
        dataset='XNAS.ITCH',
        symbols='QQQ', # <-- ★★★ シンボルをNDX.v1からQQQに修正 ★★★
        schema='ohlcv-1m',
        start='2020-09-14T00:00:00Z',
        end=end_date_str,
    ).to_df()
    print(f"取得完了。{len(data)}行のデータを処理します。")

    if data.empty:
        print("データが0行です。処理を中断します。")
        return

    data.rename(columns={'ts_event': 'timestamp'}, inplace=True)
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # to_gbqはsymbolカラムを要求しないため、ここで追加する必要はない
    # data['symbol'] = 'QQQ'

    project_id = 'project-orion-admins'
    destination_table = 'orion_datalake.market_data_history_v2'
    print(f"処理したデータをBigQueryテーブル {destination_table} にアップロードしています...")

    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

    data.to_gbq(
        destination_table=destination_table,
        project_id=project_id,
        if_exists='replace',
        # to_gbqはDataFrameのスキーマを自動的に使用するため、ここで定義する必要はない
    )
    print("データレイクの再構築が完了しました。")

if __name__ == '__main__':
    rebuild_datalake()