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

def fetch_historical_insights(tickers: list) -> list:
    db = firestore.Client()
    if not tickers:
        return []
    historical_insights = []
    ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
    for ticker in tickers:
        query = db.collection("orion-atomic-insights").where('relevant_tickers', 'array_contains', ticker).where('extracted_at', '>=', ninety_days_ago.isoformat()).order_by('extracted_at', direction=firestore.Query.DESCENDING).limit(10)
        for doc in query.stream():
            historical_insights.append(doc.to_dict())
    unique_insights = {v['insight_id']:v for v in historical_insights}.values()
    return sorted(list(unique_insights), key=lambda x: x['extracted_at'], reverse=True)

# --- Core Analysis Logic (with Lazy Initialization) ---
def generate_analysis_report(config: dict, portfolio_def_json: str, new_insight_json: str, historical_insights_json: str) -> dict:
    """Uses Vertex AI SDK to generate a synergy and risk analysis report."""
    # Lazy initialization of Vertex AI
    project_id = os.environ.get('GCP_PROJECT', 'thinking-orb-438805-q7')
    location = "asia-northeast1"
    vertexai.init(project=project_id, location=location)

    agent_config = next((agent for agent in config.get('aiFleetAgents', []) if agent['serviceName'] == 'orion-synergy-analyzer'), None)
    if not agent_config:
        raise ValueError("Configuration for 'orion-synergy-analyzer' not found.")
    
    prompt_template = agent_config['cliPromptTemplate']
    final_prompt = prompt_template.format(PORTFOLIO_DEFINITION_JSON=portfolio_def_json, NEW_INSIGHT_JSON=new_insight_json, HISTORICAL_INSIGHTS_JSON_LIST=historical_insights_json)

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

    print(f"Received request to analyze synergy/risk for insight: {insight_id}")
    
    try:
        config = load_config()
        portfolio_def = config.get('portfolioDefinition', {})
        new_insight = fetch_insight(insight_id)
        historical_insights = fetch_historical_insights(new_insight.get('relevant_tickers', []))

        report = generate_analysis_report(
            config=config,
            portfolio_def_json=json.dumps(portfolio_def, ensure_ascii=False),
            new_insight_json=json.dumps(new_insight, ensure_ascii=False),
            historical_insights_json=json.dumps(historical_insights, ensure_ascii=False)
        )
        if not report:
            return jsonify({"error": "Failed to generate analysis report."}), 500

        report['analysis_id'] = str(uuid.uuid4())
        report['original_insight_id'] = insight_id
        report['generated_by'] = 'orion-synergy-analyzer'
        report['generated_at'] = datetime.now(timezone.utc).isoformat()
        save_report(report)
        
        print("Synergy/risk analysis completed and saved successfully.")
        return jsonify({"status": "success", "analysis_id": report['analysis_id']}), 201

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))