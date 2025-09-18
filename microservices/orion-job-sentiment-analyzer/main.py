import os
import yaml
import json
import uuid
from datetime import datetime, timezone
import functions_framework
from google.cloud import firestore, pubsub_v1, storage
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

# --- Initialization ---
PROJECT_ID = os.environ.get('GCP_PROJECT', 'project-orion-admins')
LOCATION = "asia-northeast1"

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
storage_client = storage.Client()
topic_path = publisher.topic_path(PROJECT_ID, 'orion-new-insight-topic')

# Initialize Vertex AI and the cost-effective model
vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel("gemini-1.5-flash-001")

# --- Configuration Loading ---
def load_config():
    # This assumes the config file is deployed with the function
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Core Logic (Refactored) ---
def extract_hr_insight(hr_text: str) -> dict:
    config = load_config()
    agent_config = next((agent for agent in config.get('aiFleetAgents', []) if agent['serviceName'] == 'orion-job-sentiment-analyzer'), None)
    if not agent_config:
        raise ValueError("Configuration for 'orion-job-sentiment-analyzer' not found.")
    
    prompt_template = agent_config['cliPromptTemplate']
    output_json_schema = '''{...}''' # Schema is defined in the prompt template itself
    final_prompt = prompt_template.format(HR_TEXT=hr_text, OUTPUT_JSON_SCHEMA=output_json_schema)

    try:
        # Use the SDK with a JSON response type for robust parsing
        generation_config = GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(final_prompt, generation_config=generation_config)
        # --- Token Count Logging ---
        usage_metadata = response.usage_metadata
        print(f"Vertex AI Token Usage: {usage_metadata.total_tokens} tokens (Prompt: {usage_metadata.prompt_token_count}, Output: {usage_metadata.candidates_token_count})")
        # --- End Token Count Logging ---
        insight_data = json.loads(response.text)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error during HR insight extraction with Vertex AI SDK: {e}")
        return None

    insight_data['insight_id'] = str(uuid.uuid4())
    insight_data['source_url'] = 'hr_intelligence'
    insight_data['extracted_at'] = datetime.now(timezone.utc).isoformat()
    insight_data['extracted_by'] = 'orion-job-sentiment-analyzer-v2' # Version bump
    return insight_data

def save_to_firestore(insight: dict):
    db.collection("orion-atomic-insights").document(insight['insight_id']).set(insight)
    print(f"Successfully saved HR insight {insight['insight_id']} to Firestore.")

def publish_insight_notification(insight_id: str):
    try:
        message_data = json.dumps({'insight_id': insight_id}).encode('utf-8')
        future = publisher.publish(topic_path, data=message_data)
        future.get()
        print(f"Successfully published insight notification for {insight_id}.")
    except Exception as e:
        print(f"Error publishing to Pub/Sub: {e}")

@functions_framework.cloud_event
def analyze_job_sentiment(cloud_event):
    """Triggered by a file upload to a GCS bucket."""
    file_data = cloud_event.data
    bucket_name = file_data["bucket"]
    file_name = file_data["name"]
    
    print(f"Job sentiment analyzer v2 activated for file: {file_name}")
    
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        hr_text = blob.download_as_text()

        insight = extract_hr_insight(hr_text[:20000]) # Truncate to manage token size
        if not insight:
            print(f"Failed to extract HR insight from {file_name}.")
            return "OK", 204

        save_to_firestore(insight)
        publish_insight_notification(insight['insight_id'])
        
        print(f"HR insight from {file_name} processed successfully.")
        return "OK", 204

    except Exception as e:
        print(f"Error processing HR text file {file_name}: {e}")
        return "OK", 204
