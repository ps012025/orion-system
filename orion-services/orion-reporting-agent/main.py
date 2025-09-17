import os
import yaml
import json
import base64
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify
from google.cloud import firestore, secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- Initialization & Configuration ---
app = Flask(__name__)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Client Initialization (Lazy & Cached) ---
_gmail_service = None
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

def get_gmail_service():
    global _gmail_service
    if _gmail_service:
        return _gmail_service
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    client_secret_json_string = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    if not client_secret_json_string or not refresh_token:
        raise ValueError("FATAL: GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN env vars are not set.")
    client_config = json.loads(client_secret_json_string)
    credentials = Credentials(
        None, refresh_token=refresh_token,
        token_uri=client_config["installed"]["token_uri"],
        client_id=client_config["installed"]["client_id"],
        client_secret=client_config["installed"]["client_secret"],
        scopes=SCOPES
    )
    _gmail_service = build('gmail', 'v1', credentials=credentials)
    return _gmail_service

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

def send_email(recipient: str, subject: str, html_body: str):
    try:
        service = get_gmail_service()
        message = MIMEMultipart('alternative')
        message['to'] = recipient
        message['subject'] = subject
        message.attach(MIMEText(html_body, 'html'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}
        message = (service.users().messages().send(userId='me', body=body).execute())
        print(f"Message Id: {message['id']} sent to {recipient}")
    except Exception as e:
        print(f"An error occurred while sending email: {e}")

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
    perf_data = data.get('daily_performance')
    events = data.get('upcoming_events')
    report_lines = [f"*Orion Daily Report: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*\n"]

    # Performance Section
    report_lines.append("*ポートフォリオ分析*")
    if not perf_data:
        report_lines.append("> 本日のパフォーマンスデータは利用できません。(ドキュメント未検出)")
    elif perf_data.get('status') == 'ERROR':
        report_lines.append(f"> :warning: *データ生成エラー:* ```{perf_data.get('message', 'Unknown error')}```")
    elif perf_data.get('status') == 'SUCCESS':
        summary = perf_data.get('portfolio_summary', {})
        pl_sign = "+" if summary.get('daily_pl', 0) >= 0 else ""
        report_lines.append(f"> ポートフォリオ合計評価額: `${summary.get('current_value', 0):,.2f}`")
        report_lines.append(f"> 本日の評価損益: `{pl_sign}${summary.get('daily_pl', 0):,.2f}` (`{pl_sign}{summary.get('daily_pl_percent', 0):.2%}`)")
        
        # Add individual stock performance
        positions = perf_data.get('positions', [])
        if positions:
            report_lines.append("\n*個別銘柄のパフォーマンス:*")
            for pos in sorted(positions, key=lambda p: p.get('symbol', 'ZZZ')):
                pos_pl_sign = "+" if pos.get('daily_pl', 0) >= 0 else ""
                line = f"> *{pos.get('symbol', 'N/A')}*: `{pos_pl_sign}${pos.get('daily_pl', 0):,.2f}` (`{pos_pl_sign}{pos.get('daily_pl_percent', 0):.2%}`)"
                report_lines.append(line)
    else:
        report_lines.append("> 本日のパフォーマンスデータは利用できません。(不明なステータス)")
    
    report_lines.append("\n")
    report_lines.append("*今後の重要イベント*")
    if not events:
        report_lines.append("> 今後の重要イベントはありません。")
    else:
        for event in events:
            report_lines.append(f"- {event.get('summary', 'No summary')} ({event.get('start_time', 'N/A')})")
            
    return "\n".join(report_lines)

# --- Main HTTP Endpoints ---
@app.route("/", methods=["POST"])
def handle_main_request():
    try:
        data = request.get_json(silent=True) or {}
        if "slack_message" in data:
            print("Received ad-hoc Slack message request.")
            send_slack_notification(data["slack_message"])
            return jsonify({"status": "success", "message": "Slack message sent."}), 200
        if "alert_subject" in data and "alert_body" in data:
            print("Received CODE: RED alert. Sending to Email and Slack.")
            config = load_config()
            recipient = config.get('reportTemplate', {}).get('recipientEmail')
            if not recipient:
                raise ValueError("Recipient email not found for alert.")
            send_email(recipient, data["alert_subject"], data["alert_body"])
            send_slack_notification(f":rotating_light: *{data['alert_subject']}* :rotating_light:\n```{data['alert_body']}```")
            return jsonify({"status": "success", "message": "Alert sent to Email and Slack."}), 200

        print("Received daily report trigger. Sending to Slack.")
        daily_data = fetch_daily_data()
        slack_report = create_daily_slack_report(daily_data)
        send_slack_notification(slack_report)
        return jsonify({"status": "success", "message": "Daily report sent to Slack."}), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

@app.route("/handle-weekly-briefing", methods=["POST"])
def handle_weekly_briefing():
    envelope = request.get_json()
    if not envelope or "message" not in envelope or "data" not in envelope["message"]:
        return "Bad Request", 400
    try:
        weekly_briefing = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        print("Received weekly briefing. Sending to Email and Slack.")
        config = load_config()
        recipient = config.get('reportTemplate', {}).get('recipientEmail')
        if not recipient:
            raise ValueError("Recipient email not found.")
        subject = f"【ORION WEEKLY STRATEGIC BRIEFING】 - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        html_body = f'<h1>Orion Weekly Strategic Briefing</h1><hr><pre style="white-space: pre-wrap; font-family: sans-serif; font-size: 14px;">{weekly_briefing}</pre>'
        send_email(recipient, subject, html_body)
        send_slack_notification(f"*{subject}*\n\n```{weekly_briefing}```")
        return jsonify({"status": "success", "message": "Weekly briefing sent to Email and Slack."} ), 200
    except Exception as e:
        print(f"An unexpected error occurred while sending weekly briefing: {e}")
        return jsonify({"error": "Failed to send weekly briefing.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))