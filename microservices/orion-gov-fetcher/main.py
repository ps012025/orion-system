import os
import requests
import feedparser
import json
import hashlib
from google.cloud import firestore, pubsub_v1
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

# ... (Helper functions like get_last_seen_id, set_last_seen_id remain the same) ...

@app.route('/', methods=['POST'])
def gov_fetcher_http():
    """HTTP-triggered function to fetch updates from government RSS feeds."""
    print("Orion Gov Fetcher activated...")
    # ... (The core logic from the original gov_fetcher_http function goes here) ...
    return "Gov Fetcher finished successfully.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))