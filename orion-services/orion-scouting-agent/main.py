import os
import asyncio
import aiohttp
import feedparser
import functions_framework
import hashlib
from datetime import datetime, timezone, timedelta
from google.cloud import pubsub_v1
from google.cloud import firestore

# --- 設定 ---
PROJECT_ID = "thinking-orb-438805-q7"
TOPIC_ID = "orion-url-to-process-topic"
PROCESSED_URLS_COLLECTION = "orion-processed-urls"
PROCESSED_HASHES_COLLECTION = "orion-processed-article-hashes" # 重複排除用
METADATA_COLLECTION = "orion-rss-feed-metadata"
URL_EXPIRATION_DAYS = 7

# WebSub非対応のフィードのみをポーリング対象とする
RSS_FEEDS = {
    "reuters_world": "https://cdn.feedcontrol.net/8/1115-TvWAhu4G064WT.xml",
    "reuters_front_page": "https://cdn.feedcontrol.net/8/1114-wioSIX3uu8MEj.xml",
    "reuters_investigations": "https://cdn.feedcontrol.net/8/1117-sj0Xoer9nTe0b.xml",
}

# --- クライアントの初期化 ---
publisher = pubsub_v1.PublisherClient()
db = firestore.Client(project=PROJECT_ID)
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

async def check_feed_change(session, feed_name, feed_url):
    """非同期で単一フィードの変更を軽量にチェックする"""
    metadata_ref = db.collection(METADATA_COLLECTION).document(feed_name)
    metadata = metadata_ref.get()
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    if metadata.exists:
        if 'etag' in metadata.to_dict():
            headers['If-None-Match'] = metadata.to_dict()['etag']
        if 'last_modified' in metadata.to_dict():
            headers['If-Modified-Since'] = metadata.to_dict()['last_modified']

    async with session.head(feed_url, headers=headers, timeout=10) as response:
        if response.status == 304: # Not Modified
            return None # 変更なし
        
        new_etag = response.headers.get('ETag')
        new_last_modified = response.headers.get('Last-Modified')
        return {
            "feed_name": feed_name,
            "feed_url": feed_url,
            "etag": new_etag,
            "last_modified": new_last_modified
        }

async def process_changed_feed(change_info):
    """変更が検知されたフィードを処理し、重複排除しつつ新しいURLを発行する"""
    feed_name = change_info["feed_name"]
    feed_url = change_info["feed_url"]
    print(f"  - Feed '{feed_name}' has changed. Parsing and deduplicating...")
    
    urls_published = 0
    feed = feedparser.parse(feed_url)
    
    for entry in feed.entries:
        # --- コンテンツハッシュによる重複排除 ---
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        content_to_hash = f"{title}{summary}"
        content_hash = hashlib.md5(content_to_hash.encode()).hexdigest()
        hash_ref = db.collection(PROCESSED_HASHES_COLLECTION).document(content_hash)

        if hash_ref.get().exists:
            continue # 重複記事のためスキップ

        # --- URLベースの重複排除（念のため） ---
        url = entry.link
        url_doc_id = url.replace("/", "::")
        url_ref = db.collection(PROCESSED_URLS_COLLECTION).document(url_doc_id)

        if url_ref.get().exists:
            continue # 重複URLのためスキップ

        # --- 新規記事の処理 ---
        message_data = url.encode("utf-8")
        future = publisher.publish(topic_path, data=message_data)
        future.result()

        now = datetime.now(timezone.utc)
        url_ref.set({"processed_at": now})
        hash_ref.set({"processed_at": now, "source_feed": feed_name})
        
        urls_published += 1
        print(f"    > Discovered unique article: {title}")

    # 新しいヘッダー情報を保存
    metadata_ref = db.collection(METADATA_COLLECTION).document(feed_name)
    update_data = {'updated_at': datetime.now(timezone.utc)}
    if change_info["etag"]:
        update_data['etag'] = change_info["etag"]
    if change_info["last_modified"]:
        update_data['last_modified'] = change_info["last_modified"]
    metadata_ref.set(update_data, merge=True)
    
    return urls_published

@functions_framework.cloud_event
def scout_and_publish_urls(cloud_event):
    """非同期HTTP HEADリクエストでRSSフィードの変更を効率的に検知し、新しい記事のみを発行する"""
    print("Scouting agent activated. Polling non-WebSub feeds...")
    
    async def main():
        async with aiohttp.ClientSession() as session:
            check_tasks = [check_feed_change(session, name, url) for name, url in RSS_FEEDS.items()]
            results = await asyncio.gather(*check_tasks)
            
            changed_feeds = [res for res in results if res is not None]
            
            if not changed_feeds:
                print("\nNo feeds have changed. Execution finished.")
                return 0
            
            print(f"\nDetected changes in {len(changed_feeds)} feed(s).")
            
            process_tasks = [process_changed_feed(info) for info in changed_feeds]
            publish_counts = await asyncio.gather(*process_tasks)
            
            return sum(publish_counts)

    total_new_urls = asyncio.run(main())
    
    print(f"\nScouting complete. Found and published {total_new_urls} unique new URLs from polled feeds.")
    
    if total_new_urls > 0:
        cleanup_old_urls()

    return "OK", 204

def cleanup_old_urls():
    """URL_EXPIRATION_DAYSより古いドキュメントをFirestoreから削除する。"""
    print("Cleaning up old URL and hash entries from Firestore...")
    # 古いURLを削除
    url_collection_ref = db.collection(PROCESSED_URLS_COLLECTION)
    expiration_time = datetime.now(timezone.utc) - timedelta(days=URL_EXPIRATION_DAYS)
    urls_to_delete = url_collection_ref.where("processed_at", "<", expiration_time).stream()
    deleted_count = 0
    for doc in urls_to_delete:
        doc.reference.delete()
        deleted_count += 1
    if deleted_count > 0:
        print(f"- Cleaned up {deleted_count} old URL entries.")

    # 古いハッシュを削除
    hash_collection_ref = db.collection(PROCESSED_HASHES_COLLECTION)
    hashes_to_delete = hash_collection_ref.where("processed_at", "<", expiration_time).stream()
    deleted_count = 0
    for doc in hashes_to_delete:
        doc.reference.delete()
        deleted_count += 1
    if deleted_count > 0:
        print(f"- Cleaned up {deleted_count} old hash entries.")
