import os, json, base64
from google.cloud import pubsub_v1
publisher = pubsub_v1.PublisherClient()
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
NEXT_TOPIC_ID = os.environ.get("NEXT_TOPIC_ID")
TOPIC_PATH = publisher.topic_path(PROJECT_ID, NEXT_TOPIC_ID)
IRRELEVANT_KEYWORDS = ['sports', 'entertainment', 'celebrity', 'fashion', 'lifestyle']
def pre_filter_url(event, context):
    try:
        message_data_str = base64.b64decode(event["data"]).decode('utf-8')
        data = json.loads(message_data_str)
        url = data.get('url', '').lower()
        title = data.get('title', '').lower()
        if any(keyword in title or keyword in url for keyword in IRRELEVANT_KEYWORDS):
            print(f"IRRELEVANT: URL破棄: {url}")
            return
        future = publisher.publish(TOPIC_PATH, data=message_data_str.encode('utf-8'))
        print(f"RELEVANT: URL転送: {url} (Message ID: {future.result()})")
    except Exception as e:
        print(f"エラー: メッセージ処理に失敗しました: {e}")
