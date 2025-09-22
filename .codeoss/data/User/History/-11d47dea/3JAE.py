import databento as db
from google.cloud import bigquery
import pandas as pd
import os
from datetime import datetime, timezone, timedelta

def rebuild_datalake():
    """
    Databentoからデータを取得し、BigQueryテーブルを再構築する。
    """
    api_key = os.environ.get('DATABENTO_API_KEY')
    if not api_key:
        print("エラー: 環境変数 DATABENTO_API_KEY が設定されていません。")
        return

    client = db.Historical(key=api_key)

    print("Databentoから過去のデータを取得しています... これには時間がかかる場合があります。")

    # ★★★ あなたの情報に基づき、終了日を2024-12-31に最終修正 ★★★
    end_date_str = '2024-12-31T23:59:59Z'

    data = client.timeseries.get_range(
        dataset='XNAS.ITCH',
        symbols='NDX.v1', # NASDAQ 100
        schema='ohlcv-1m',
        start='2020-09-14T00:00:00Z',
        end=end_date_str,
    ).to_df()
    print(f"取得完了。{len(data)}行のデータを処理します。")

    data.rename(columns={'ts_event': 'timestamp'}, inplace=True)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data['symbol'] = 'AAPL'

    project_id = 'project-orion-admins'
    destination_table = 'orion_datalake.market_data_history_v2'
    print(f"処理したデータをBigQueryテーブル {destination_table} にアップロードしています...")

    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

    data.to_gbq(
        destination_table=destination_table,
        project_id=project_id,
        if_exists='replace',
        table_schema=[
            {'name': 'symbol', 'type': 'STRING'},
            {'name': 'timestamp', 'type': 'TIMESTAMP'},
            {'name': 'open', 'type': 'FLOAT64'},
            {'name': 'high', 'type': 'FLOAT64'},
            {'name': 'low', 'type': 'FLOAT64'},
            {'name': 'close', 'type': 'FLOAT64'},
            {'name': 'volume', 'type': 'INT64'},
        ]
    )
    print("データレイクの再構築が完了しました。")

if __name__ == '__main__':
    rebuild_datalake()