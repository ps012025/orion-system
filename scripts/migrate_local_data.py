import os
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

def migrate_with_pandas():
    """
    GCS上のCSVをpandasで読み込み、不正な行をスキップした後、
    クリーンなDataFrameをBigQueryにロードする。
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    dataset_id = os.environ.get("BQ_DATASET_ID")
    table_id = os.environ.get("BQ_TABLE_ID")

    if not all([project_id, bucket_name, dataset_id, table_id]):
        print("エラー: 必要な環境変数が設定されていません。")
        return

    gcs_uri = f"gs://{bucket_name}/nasdaq100_ohlcv_1m_2018.csv"
    table_ref_str = f"{project_id}.{dataset_id}.{table_id}"

    print(f"Pandasを使用してGCSからCSVを読み込みます: {gcs_uri}")
    try:
        column_types = {
            'rtype': str, 'publisher_id': str,
            'instrument_id': str, 'symbol': str
        }
        df = pd.read_csv(gcs_uri, on_bad_lines='skip', dtype=column_types)
        df['ts_event'] = pd.to_datetime(df['ts_event'])
    except Exception as e:
        print(f"PandasでのCSV読み込み中にエラーが発生しました: {e}")
        return

    client = bigquery.Client(project=project_id)
    try:
        client.get_dataset(dataset_id)
    except NotFound:
        print(f"データセット '{dataset_id}' が存在しないため、作成します。")
        client.create_dataset(dataset_id)

    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("ts_event", "TIMESTAMP"),
            bigquery.SchemaField("rtype", "STRING"),
            bigquery.SchemaField("publisher_id", "STRING"),
            bigquery.SchemaField("instrument_id", "STRING"),
            bigquery.SchemaField("open", "FLOAT64"),
            bigquery.SchemaField("high", "FLOAT64"),
            bigquery.SchemaField("low", "FLOAT64"),
            bigquery.SchemaField("close", "FLOAT64"),
            bigquery.SchemaField("volume", "INT64"),
            bigquery.SchemaField("symbol", "STRING"),
        ],
        write_disposition="WRITE_APPEND",
    )

    print(f"クリーンなDataFrameをBigQueryテーブルにロードします: {table_ref_str}")
    load_job = client.load_table_from_dataframe(
        df, table_ref_str, job_config=job_config
    )
    load_job.result()
    destination_table = client.get_table(table_ref_str)
    print(f"ロード完了。テーブルには {destination_table.num_rows} 行のデータが存在します。")

if __name__ == "__main__":
    migrate_with_pandas()
