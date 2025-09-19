import os
import yaml
import json
import base64
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from google.cloud import firestore, secretmanager

app = Flask(__name__)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_slack_webhook_url = None

def get_slack_webhook_url():
    global _slack_webhook_url
    if _slack_webhook_url: return _slack_webhook_url
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = "slack-webhook-url"
        project_id = os.environ.get("GCP_PROJECT", "project-orion-admins")
        resource_name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        print(f"DEBUG: Fetching secret: {resource_name}")
        response = client.access_secret_version(name=resource_name)
        _slack_webhook_url = response.payload.data.decode("UTF-8")
        print("DEBUG: Successfully fetched Slack Webhook URL.")
        return _slack_webhook_url
    except Exception as e:
        print(f"FATAL_DEBUG: Could not fetch Slack Webhook URL: {e}")
        raise

def send_slack_notification(text: str):
    print("DEBUG: Entering send_slack_notification function.")
    try:
        webhook_url = get_slack_webhook_url()
        if not webhook_url:
            print("ERROR_DEBUG: Slack webhook URL is None or empty.")
            return
        payload = {"text": text}
        print(f"DEBUG: Sending payload to Slack...")
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("DEBUG: Successfully sent Slack notification.")
    except Exception as e:
        print(f"ERROR_DEBUG: Slack notification failed: {e}")
        raise

def fetch_daily_data():
    print("DEBUG: Entering fetch_daily_data function.")
    try:
        db = firestore.Client()
        report_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        print(f"DEBUG: Fetching Firestore doc: orion-daily-performance/{report_date}")
        perf_doc = db.collection("orion-daily-performance").document(report_date).get()
        daily_performance = perf_doc.to_dict() if perf_doc.exists else None
        print(f"DEBUG: Daily performance data: {daily_performance}")
        return {"daily_performance": daily_performance, "upcoming_events": []} # Simplified for debug
    except Exception as e:
        print(f"ERROR_DEBUG: Failed to fetch data from Firestore: {e}")
        raise

def create_daily_slack_report(data: dict) -> str:
    print("DEBUG: Entering create_daily_slack_report function.")
    # ... (logic is assumed to be correct, keeping it simple)
    return "DEBUG: This is a test report from the debug-injected agent."

@app.route("/", methods=["POST"])
def handle_main_request():
    print("--- DEBUG V3: Main request handler started ---")
    try:
        print("DEBUG: Fetching daily data...")
        daily_data = fetch_daily_data()
        
        print("DEBUG: Creating Slack report...")
        slack_report = create_daily_slack_report(daily_data)
        
        print("DEBUG: Sending Slack notification...")
        send_slack_notification(slack_report)
        
        print("--- DEBUG V3: Request processed successfully ---")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"FATAL_DEBUG: An unexpected error occurred in main handler: {e}")
        # Also send this fatal error to Slack if possible
        try:
            send_slack_notification(f":skull_and_crossbones: FATAL ERROR in reporting-agent: ```{e}```")
        except: pass
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))