import os
import functions_framework
import requests
import feedparser
from google.cloud import firestore, storage
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import hashlib
import yaml

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
TARGET_BUCKET = os.environ.get("TARGET_GCS_BUCKET")
FIRESTORE_COLLECTION = "orion-hr-fetcher-state"
USER_AGENT = "Orion System v8.0 HR Fetcher/1.0 (contact: ps012025@gmail.com)"

# --- Clients ---
db = firestore.Client()
storage_client = storage.Client()

# --- Configuration Loading ---
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

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

def get_job_description(url: str) -> str:
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        job_div = soup.find('div', class_=lambda x: x and 'job' in x and 'description' in x) or \
                  soup.find('div', id=lambda x: x and 'job' in x and 'description' in x)
        if job_div:
            return job_div.get_text(separator='\n', strip=True)
        return soup.body.get_text(separator='\n', strip=True)
    except Exception as e:
        print(f"  - Failed to scrape job description from {url}: {e}")
        return None

def save_text_to_gcs(text: str, filename: str):
    bucket = storage_client.bucket(TARGET_BUCKET)
    blob = bucket.blob(filename)
    blob.upload_from_string(text, content_type='text/plain')
    print(f"  - Successfully saved job description to gs://{TARGET_BUCKET}/{filename}")

@functions_framework.http
def hr_fetcher_http(request):
    print("Orion HR Fetcher v2 (Configurable) activated...")
    if not TARGET_BUCKET:
        return "TARGET_GCS_BUCKET environment variable is not set.", 500

    config = load_config()
    job_rss_feeds = config.get('hr_fetcher_config', {}).get('job_rss_feeds', {})
    if not job_rss_feeds:
        print("Warning: No job RSS feeds configured. Exiting.")
        return "No feeds configured.", 200

    try:
        for feed_name, feed_url in job_rss_feeds.items():
            print(f"Processing feed: {feed_name} ({feed_url})")
            feed = feedparser.parse(feed_url)
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
                new_entries = feed.entries[:5]
            
            if not new_entries:
                print("  - No new job postings found.")
                continue

            print(f"  - Found {len(new_entries)} new job postings.")
            for entry in reversed(new_entries):
                job_text = get_job_description(entry.link)
                if job_text:
                    file_id = hashlib.md5(entry.id.encode()).hexdigest()
                    filename = f"{feed_name}_{file_id}.txt"
                    save_text_to_gcs(job_text, filename)
                    # Notify synergy analyzer
                    publisher.publish(publisher.topic_path(PROJECT_ID, 'new-atomic-insight-created'), data=json.dumps({'insight_id': 'YOUR_INSIGHT_ID'}).encode('utf-8'))
            
            set_last_seen_id(feed_url, new_entries[0].id)

        return "HR Fetcher finished successfully.", 200

    except Exception as e:
        print(f"ERROR: An unexpected error occurred in HR Fetcher: {e}")
        return "Internal Server Error", 500