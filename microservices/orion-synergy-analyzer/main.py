import os
import json
import base64
import functions_framework
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel
from datetime import datetime, timedelta, timezone

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
LOCATION = "asia-northeast1"
INSIGHTS_COLLECTION = "orion-atomic-insights"
REPORTS_COLLECTION = "orion-analysis-reports"

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client()
model = GenerativeModel("gemini-1.5-flash-001")

# --- Data Fetching ---
def fetch_insight(insight_id: str) -> dict:
    # ... (logic remains the same)
    pass

def fetch_related_insights(symbol: str) -> list:
    # ... (logic remains the same)
    pass

# --- Main Logic (Pub/Sub Triggered) ---
@functions_framework.cloud_event
def analyze_synergy_pubsub(cloud_event):
    print("Orion Synergy Analyzer (Pub/Sub Function) activated...")
    try:
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode('utf-8')
        message_data = json.loads(pubsub_message)
        new_insight_id = message_data.get('insight_id')

        if not new_insight_id:
            print("Invalid message: missing insight_id")
            return

        new_insight = fetch_insight(new_insight_id)
        primary_symbol = new_insight.get('relevant_tickers', [None])[0]
        if not primary_symbol:
            return

        # ... (The rest of the synergy analysis logic remains the same) ...

        print("Synergy analysis completed.")

    except FileNotFoundError as e:
        print(f"ERROR: Could not find the triggering insight document: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in synergy analyzer: {e}")