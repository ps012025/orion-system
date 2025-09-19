import os
import yaml
import json
import base64
import requests
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify
from google.cloud import firestore, secretmanager

# --- Initialization & Configuration ---
app = Flask(__name__)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Client Initialization (Lazy & Cached) ---
_slack_webhook_url = None

def load_config():
    config_path = os.path.join(_SCRIPT_DIR, 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_slack_webhook_url():
    global _slack_webhook_url
    if _slack_webhook_url:
        return _slack_webhook_url
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = "slack-webhook-url"
        project_id = os.environ.get("GCP_PROJECT", "project-orion-admins")
        resource_name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        print(f"Fetching secret: {secret_name}")
        response = client.access_secret_version(name=resource_name)
        _slack_webhook_url = response.payload.data.decode("UTF-8")
        print("Successfully fetched Slack Webhook URL.")
        return _slack_webhook_url
    except Exception as e:
        print(f"FATAL: Could not fetch Slack Webhook URL: {e}")
        return None

# --- Notification Functions ---
def send_slack_notification(text: str):
    webhook_url = get_slack_webhook_url()
    if not webhook_url:
        print("ERROR: Slack notification failed, Webhook URL is not available.")
        return
    try:
        payload = {"text": text}
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Successfully sent Slack notification.")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Slack notification failed: {e}")

# --- Data Fetching & Report Generation ---
def fetch_daily_data():
    db = firestore.Client()
    report_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    perf_doc = db.collection("orion-daily-performance").document(report_date).get()
    daily_performance = perf_doc.to_dict() if perf_doc.exists else None
    events_query = db.collection("orion-calendar-events").where('start_time', '>=', datetime.now(timezone.utc).isoformat()).limit(10)
    upcoming_events = [doc.to_dict() for doc in events_query.stream()]
    return {"daily_performance": daily_performance, "upcoming_events": upcoming_events}

def create_daily_slack_report(data: dict) -> str:
    # ... (This function remains the same)
    pass

# --- Main HTTP Endpoints ---
@app.route("/", methods=["POST"])
def handle_main_request():
    try:
        data = request.get_json(silent=True) or {}
        if "slack_message" in data:
            print("Received ad-hoc Slack message request.")
            send_slack_notification(data["slack_message"])
            return jsonify({"status": "success", "message": "Slack message sent."}), 200
        
        # Email functionality is disabled
        # if "alert_subject" in data and "alert_body" in data:
        #     ...

        print("Received daily report trigger. Sending to Slack.")
        daily_data = fetch_daily_data()
        slack_report = create_daily_slack_report(daily_data)
        send_slack_notification(slack_report)
        return jsonify({"status": "success", "message": "Daily report sent to Slack."}), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

# ... (handle_weekly_briefing can be simplified or disabled if it also sends emails) ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
