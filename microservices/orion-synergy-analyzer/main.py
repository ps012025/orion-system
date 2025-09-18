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
    doc_ref = db.collection(INSIGHTS_COLLECTION).document(insight_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise FileNotFoundError(f"Insight with id {insight_id} not found.")
    return doc.to_dict()

def fetch_related_insights(symbol: str, new_insight_id: str) -> list:
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    query = db.collection(INSIGHTS_COLLECTION).where('relevant_tickers', 'array_contains', symbol).where('extracted_at', '>=', seven_days_ago.isoformat()).limit(10)
    insights = [doc.to_dict() for doc in query.stream() if doc.id != new_insight_id]
    return insights

# --- Main Logic (Pub/Sub Triggered) ---
@functions_framework.cloud_event
def analyze_synergy_pubsub(cloud_event):
    print("Orion Synergy Analyzer (Pub/Sub Function) v2 activated...")
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

        historical_insights = fetch_related_insights(primary_symbol, new_insight_id)
        if not historical_insights:
            print(f"No other recent insights for {primary_symbol}. No synergy analysis needed.")
            return

        prompt = f"..."
        analysis_response = model.generate_content(prompt)
        synergy_data = json.loads(analysis_response.text)

        report_data = {
            "type": "synergy_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
            "primary_insight_id": new_insight_id,
            "primary_symbol": primary_symbol,
            "synergy_result": synergy_data
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        print("Successfully stored synergy analysis report.")

    except FileNotFoundError as e:
        print(f"ERROR: Could not find the triggering insight document: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in synergy analyzer: {e}")