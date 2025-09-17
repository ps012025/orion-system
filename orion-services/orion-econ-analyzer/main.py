import os
import yaml
import json
import uuid
from datetime import datetime, timezone, timedelta

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from flask import Flask, request, jsonify
from google.cloud import firestore

# --- Initialization ---
app = Flask(__name__)

# --- Configuration Loading ---
def load_config():
    """Loads the main configuration file from the script's directory."""
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Data Fetching (with Lazy Initialization) ---
def fetch_insight(insight_id: str) -> dict:
    db = firestore.Client()
    doc_ref = db.collection("orion-atomic-insights").document(insight_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise FileNotFoundError(f"Insight with id {insight_id} not found.")
    return doc.to_dict()

def fetch_calendar_events() -> list:
    db = firestore.Client()
    events = []
    now = datetime.now(timezone.utc)
    query = db.collection("orion-calendar-events").where('start_time', '>=', now).where('start_time', '<', now + timedelta(days=7)).order_by('start_time')
    for doc in query.stream():
        event = doc.to_dict()
        # Assuming start_time and end_time are already datetime objects from Firestore
        # If they are strings, they need to be parsed first.
        if 'start_time' in event and hasattr(event['start_time'], 'isoformat'):
             event['start_time'] = event['start_time'].isoformat()
        if 'end_time' in event and hasattr(event['end_time'], 'isoformat'):
            event['end_time'] = event['end_time'].isoformat()
        events.append(event)
    return events

# --- Core Analysis Logic (with Lazy Initialization) ---
def generate_analysis_report(config: dict, new_insight_json: str, calendar_events_json: str) -> dict:
    """Uses Vertex AI SDK to generate a macroeconomic analysis report."""
    # Lazy initialization of Vertex AI
    project_id = os.environ.get('GCP_PROJECT', 'thinking-orb-438805-q7')
    location = "asia-northeast1"
    vertexai.init(project=project_id, location=location)

    agent_config = next((agent for agent in config.get('aiFleetAgents', []) if agent['serviceName'] == 'orion-econ-analyzer'), None)
    if not agent_config:
        raise ValueError("Configuration for 'orion-econ-analyzer' not found.")
    
    prompt_template = agent_config['cliPromptTemplate']
    final_prompt = prompt_template.format(NEW_INSIGHT_JSON=new_insight_json, CALENDAR_EVENTS_JSON=calendar_events_json)

    try:
        model_name = config.get('systemConfig', {}).get('model', 'gemini-1.5-pro')
        model = GenerativeModel(model_name)
        generation_config = GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(final_prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error during analysis generation: {e}")
        return None

def save_report(report: dict):
    db = firestore.Client()
    collection_name = "orion-analysis-reports"
    doc_id = report['analysis_id']
    db.collection(collection_name).document(doc_id).set(report)
    print(f"Successfully saved report {doc_id} to Firestore collection {collection_name}.")

# --- Flask Web Server ---
@app.route("/", methods=["POST"])
def handle_request():
    """Main entry point. Expects a POST request with an insight_id."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # Handle both direct POST and Pub/Sub messages
    if "message" in data and "data" in data["message"]:
        from base64 import b64decode
        payload_str = b64decode(data["message"]["data"]).decode("utf-8")
        payload = json.loads(payload_str)
    else:
        payload = data

    insight_id = payload.get("insight_id")
    if not insight_id:
        return jsonify({"error": "Missing 'insight_id' in payload"}), 400

    print(f"Received request to analyze economic context for insight: {insight_id}")
    
    try:
        config = load_config()
        insight_doc = fetch_insight(insight_id)
        calendar_events = fetch_calendar_events()

        report = generate_analysis_report(
            config=config,
            new_insight_json=json.dumps(insight_doc, ensure_ascii=False),
            calendar_events_json=json.dumps(calendar_events, ensure_ascii=False)
        )
        if not report:
            return jsonify({"error": "Failed to generate analysis report."}), 500

        report['analysis_id'] = str(uuid.uuid4())
        report['original_insight_id'] = insight_id
        report['generated_by'] = 'orion-econ-analyzer'
        report['generated_at'] = datetime.now(timezone.utc).isoformat()
        save_report(report)
        
        print("Economic context analysis completed and saved successfully.")
        return jsonify({"status": "success", "analysis_id": report['analysis_id']}), 201

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
