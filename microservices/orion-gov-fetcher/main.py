import os
import functions_framework
import requests
import feedparser
import json
from google.cloud import firestore, pubsub_v1
from datetime import datetime, timezone
import hashlib

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
OUTPUT_TOPIC_ID = "filtered-urls-for-analysis"
FIRESTORE_COLLECTION = "orion-gov-fetcher-state"
USER_AGENT = "Orion System v8.0 Gov Fetcher/1.0 (contact: ps012025@gmail.com)"

# --- Clients ---
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC_ID)

# List of government RSS feeds to monitor
GOV_RSS_FEEDS = {
    "WHITE_HOUSE_BRIEFINGS": "https://www.whitehouse.gov/briefing-room/statements-and-releases/feed/",
    "FED_PRESS_RELEASES": "https://www.federalreserve.gov/feeds/press_releases.xml",
    "TREASURY_PRESS_RELEASES": "https://home.treasury.gov/news/press-releases/feed",
    "ECB_PRESS_RELEASES": "https://www.ecb.europa.eu/press/rss/press.en.xml"
}

# --- Main Logic ---
def get_last_seen_id(feed_url: str) -> str:
    doc_id = hashlib.md5(feed_url.encode()).hexdigest()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('last_seen_entry_id')
    return None

def set_last_seen_id(feed_url: str, entry_id: str):
    doc_id = hashlib.md5(feed_url.encode()).hexdigest()
    doc_ref = db.collection(FIRESTORE_COLLECTION).document(doc_id)
    doc_ref.set({'last_seen_entry_id': entry_id, 'last_updated_utc': datetime.now(timezone.utc)})

@functions_framework.http
def gov_fetcher_http(request):
    """HTTP-triggered function to fetch updates from government RSS feeds."""
    print("Orion Gov Fetcher activated...")
    try:
        headers = {'User-Agent': USER_AGENT}
        
        for feed_name, feed_url in GOV_RSS_FEEDS.items():
            print(f"Processing feed: {feed_name}")
            response = requests.get(feed_url, headers=headers, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            if feed.bozo:
                print(f"  - Warning: Feed may be ill-formed: {feed.bozo_exception}")
                continue

            last_seen_id = get_last_seen_id(feed_url)
            new_entries = []
            if last_seen_id:
                for entry in feed.entries:
                    if entry.id == last_seen_id:
                        break
                    new_entries.append(entry)
            else:
                # On first run, process only the most recent 5 entries
                new_entries = feed.entries[:5]
            
            if not new_entries:
                print("  - No new announcements found.")
                continue

            print(f"  - Found {len(new_entries)} new announcements.")
            for entry in reversed(new_entries): # Process oldest first
                title = entry.title
                link = entry.link
                
                message_payload = {"url": link, "title": f"[{feed_name}] {title}"}
                message_data = json.dumps(message_payload).encode('utf-8')
                
                future = publisher.publish(output_topic_path, data=message_data)
                future.get(timeout=30)
                print(f"    - Published: {title}")
            
            # Update the last seen ID to the newest entry from this batch
            set_last_seen_id(feed_url, new_entries[0].id)

        return "Gov Fetcher finished successfully.", 200

    except Exception as e:
        print(f"ERROR: An unexpected error occurred in Gov Fetcher: {e}")
        return "Internal Server Error", 500
