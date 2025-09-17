import os
import yaml
import json
import uuid
from datetime import datetime, timezone

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import pubsub_v1

# --- Initialization ---
app = Flask(__name__)
db = firestore.Client()

# Project and location for Vertex AI
PROJECT_ID = os.environ.get('GCP_PROJECT', 'thinking-orb-438805-q7')
LOCATION = "asia-northeast1"
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Pub/Sub client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, 'orion-new-insight-topic')

# --- Configuration Loading ---
def load_config():
    """Loads the main configuration file from the script's directory."""
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Core Logic ---
def extract_insight(article_text: str, source_url: str) -> dict:
    """Uses the Vertex AI SDK to extract an atomic insight from article text."""
    config = load_config()
    agent_config = next((agent for agent in config.get('aiFleetAgents', []) if agent['serviceName'] == 'orion-insight-wrangler'), None)
    if not agent_config:
        raise ValueError("Configuration for 'orion-insight-wrangler' not found.")
    
    prompt_template = agent_config['cliPromptTemplate']
    output_json_schema = '''{
      "relevant_tickers": ["string (e.g., 'NVDA', 'IONQ') or null"],
      "summary": "string (A concise summary of the key insight in Japanese)",
      "sentiment": "string (Positive, Negative, Neutral)",
      "sentiment_reasoning": "string (Briefly why the sentiment was chosen, in Japanese)",
      "confidence_score": "number (0.0 to 1.0, representing confidence in the extraction)"
    }'''
    final_prompt = prompt_template.format(ARTICLE_TEXT=article_text, OUTPUT_JSON_SCHEMA=output_json_schema)

    # Initialize the model from config
    model_name = config.get('systemConfig', {}).get('model', 'gemini-1.5-pro') # Fallback for safety
    model = GenerativeModel(model_name)
    # Set generation config to ensure JSON output
    generation_config = GenerationConfig(response_mime_type="application/json")
    # Generate content
    response = model.generate_content(final_prompt, generation_config=generation_config)
    
    insight_data = json.loads(response.text)

    # Enrich and Finalize Insight
    insight_data['insight_id'] = str(uuid.uuid4())
    insight_data['source_url'] = source_url
    insight_data['extracted_at'] = datetime.now(timezone.utc).isoformat()
    insight_data['extracted_by'] = 'orion-insight-wrangler'
    return insight_data

def save_to_firestore(insight: dict):
    """Saves the extracted insight document to Firestore."""
    collection_name = "orion-atomic-insights"
    doc_id = insight['insight_id']
    db.collection(collection_name).document(doc_id).set(insight)
    print(f"Successfully saved insight {doc_id} to Firestore collection {collection_name}.")

def publish_insight_notification(insight_id: str):
    """Publishes a notification message with the insight_id to Pub/Sub."""
    try:
        message_data = json.dumps({'insight_id': insight_id}).encode('utf-8')
        future = publisher.publish(topic_path, data=message_data)
        message_id = future.get()
        print(f"Published message {message_id} to {topic_path} with insight_id: {insight_id}")
    except Exception as e:
        print(f"Error publishing to Pub/Sub: {e}")

# --- Flask Web Server ---
@app.route("/", methods=["POST"])
def handle_request():
    """Main entry point for the service."""
    print("--- RUNNING DIAGNOSTIC VERSION v1.0 ---")
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if "message" in data and "data" in data["message"]:
        from base64 import b64decode
        payload_str = b64decode(data["message"]["data"]).decode("utf-8")
        payload = json.loads(payload_str)
    else:
        payload = data

    article_text = payload.get("article_text")
    source_url = payload.get("source_url")

    if not article_text or not source_url:
        return jsonify({"error": "Missing 'article_text' or 'source_url' in payload"}), 400

    print(f"Received request to process article from: {source_url}")
    
    try:
        insight = extract_insight(article_text, source_url)
        if not insight:
            return jsonify({"error": "Failed to extract insight from article."}), 500
            
        save_to_firestore(insight)
        publish_insight_notification(insight['insight_id'])
        
        print("Insight extraction, storage, and notification completed successfully.")
        return jsonify({"status": "success", "insight_id": insight['insight_id']}), 201

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))