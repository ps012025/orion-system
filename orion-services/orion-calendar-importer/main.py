import os
import json
import yaml
import requests
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import firestore

# --- Initialization & Configuration ---
app = Flask(__name__)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config():
    """Loads the YAML configuration file for this service."""
    config_path = os.path.join(_SCRIPT_DIR, 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Alerting Function ---
def trigger_alert(error_details: str):
    """Triggers a high-priority alert email via the reporting agent."""
    print(f"Attempting to trigger a system alert for a critical failure...")
    try:
        reporting_agent_url = "https://orion-reporting-agent-100139368807.asia-northeast1.run.app"
        email_subject = f"【!!! ORION SYSTEM ALERT !!!】 Calendar Importer Failure - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
        email_body = f"""<h1>Orion System Alert: Critical Failure</h1>
            <p>The <strong>orion-calendar-importer</strong> service has failed.</p>
            <p>This means upcoming economic events will NOT be updated in the system, and daily reports may be missing crucial context.</p>
            <p><strong>Reason:</strong></p>
            <pre>{error_details}</pre>
            <p><strong>Immediate action is required to check the service logs and potentially refresh the Google Calendar API authentication tokens.</strong></p>
        """
        
        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={reporting_agent_url}'
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token = token_response.text
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        
        payload = {"alert_subject": email_subject, "alert_body": email_body}
        response = requests.post(reporting_agent_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print("Successfully triggered alert email via reporting agent.")
    except Exception as e:
        print(f"CRITICAL: Failed to trigger alert email. The original error was: {error_details}. The alerting error was: {e}")

# --- Google Calendar Authentication ---
def get_calendar_service():
    """Authenticates with Google Calendar API using credentials from environment variables."""
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    client_secret_json_string = os.environ.get("ORION_CALENDAR_CLIENT_SECRET")
    refresh_token = os.environ.get("ORION_CALENDAR_REFRESH_TOKEN")

    if not client_secret_json_string or not refresh_token:
        raise ValueError("FATAL: ORION_CALENDAR_CLIENT_SECRET and/or ORION_CALENDAR_REFRESH_TOKEN environment variables are not set.")

    try:
        client_config = json.loads(client_secret_json_string)
    except json.JSONDecodeError:
        raise ValueError("FATAL: ORION_CALENDAR_CLIENT_SECRET is not a valid JSON string.")

    credentials = Credentials(
        None, refresh_token=refresh_token,
        token_uri=client_config["installed"]["token_uri"],
        client_id=client_config["installed"]["client_id"],
        client_secret=client_config["installed"]["client_secret"],
        scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

# --- Core Logic ---
def import_events(config: dict):
    """Fetches events from multiple Google Calendars and saves them to Firestore."""
    db = firestore.Client()
    print("Attempting to authenticate with Google Calendar...")
    service = get_calendar_service()
    print("Authentication successful. Fetching events...")

    calendar_ids = config.get('calendar_importer_config', {}).get('calendar_ids', [])
    if not calendar_ids:
        raise ValueError("No calendar IDs found in the configuration file.")

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=30)).isoformat()
    
    all_items = []
    print(f"Fetching events from {len(calendar_ids)} calendars...")
    for cal_id in calendar_ids:
        try:
            events_result = service.events().list(
                calendarId=cal_id, timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy='startTime'
            ).execute()
            items = events_result.get('items', [])
            print(f"  - Found {len(items)} events in calendar: {cal_id}")
            all_items.extend(items)
        except Exception as e:
            print(f"  - Error fetching from calendar {cal_id}: {e}")
            continue

    if not all_items:
        print("No upcoming events found in any of the specified calendars.")
        return 0

    print(f"Found a total of {len(all_items)} events. Preparing to save to Firestore...")
    batch = db.batch()
    collection_ref = db.collection('orion-calendar-events')
    count = 0
    for item in all_items:
        doc_id = item['id']
        event_data = {
            'summary': item.get('summary'),
            'start_time': item['start'].get('dateTime') or item['start'].get('date'),
            'end_time': item['end'].get('dateTime') or item['end'].get('date'),
            'description': item.get('description'),
            'location': item.get('location'),
            'source': 'google_calendar',
            'calendar_id': item.get('organizer', {}).get('email'),
            'imported_at': now.isoformat()
        }
        doc_ref = collection_ref.document(doc_id)
        batch.set(doc_ref, event_data, merge=True)
        count += 1
    batch.commit()
    print(f"Successfully imported/updated {count} events into 'orion-calendar-events' collection.")
    return count

# --- Flask Web Server ---
@app.route("/", methods=["POST"])
def handle_request():
    """Main entry point for the service. A simple POST request triggers the import."""
    print("Received request to import calendar events.")
    try:
        config = load_config()
        num_imported = import_events(config)
        return jsonify({"status": "success", "message": f"Imported/updated {num_imported} events."}), 200
    except Exception as e:
        error_message = f"An unexpected error occurred in orion-calendar-importer: {e}"
        print(error_message)
        trigger_alert(error_message)
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
