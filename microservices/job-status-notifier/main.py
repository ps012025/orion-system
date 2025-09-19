import os
import json
import base64
from flask import Flask, request
import requests

app = Flask(__name__)

# ... (Helper function send_slack_notification remains the same) ...

@app.route('/', methods=['POST'])
def job_status_notifier_http():
    """Triggered by a CloudEvent from Pub/Sub via an Eventarc trigger."""
    # ... (The core logic from the original job_status_notifier_pubsub function goes here) ...
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))