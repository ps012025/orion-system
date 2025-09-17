import os
import json
import base64
from flask import Flask, request, jsonify
from google.cloud import firestore
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
LOCATION = "asia-northeast1"
INSIGHTS_COLLECTION = "orion-atomic-insights"
REPORTS_COLLECTION = "orion-analysis-reports"

# Vector Search Configuration
INDEX_ENDPOINT_ID = "3249188801473413120"
DEPLOYED_INDEX_ID = "orion_v1"

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client()
model = GenerativeModel("gemini-1.5-pro-001")
index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=INDEX_ENDPOINT_ID)

# --- Main Logic ---
@app.route("/", methods=["POST"])
def handle_synergy_analysis():
    print("Orion Synergy Analyzer activated...")
    envelope = request.get_json()
    if not envelope or "message" not in envelope:
        return "Bad Request: invalid Pub/Sub message format", 400

    try:
        # 1. Get the new insight
        payload_str = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        payload = json.loads(payload_str)
        new_insight_id = payload.get('insight_id')
        if not new_insight_id:
            raise ValueError("insight_id not found in payload")

        print(f"Analyzing synergies for new insight: {new_insight_id}")
        new_insight_ref = db.collection(INSIGHTS_COLLECTION).document(new_insight_id)
        new_insight = new_insight_ref.get().to_dict()
        if not new_insight or 'embedding' not in new_insight:
            raise ValueError("Insight or its embedding not found.")

        # 2. Find related insights using Vector Search
        print("Finding related insights via Vector Search...")
        response = index_endpoint.find_neighbors(
            deployed_index_id=DEPLOYED_INDEX_ID,
            queries=[new_insight['embedding']],
            num_neighbors=5
        )
        
        historical_insights = []
        if response and response[0]:
            for neighbor in response[0]:
                if neighbor.id != new_insight_id: # Exclude the new insight itself
                    doc = db.collection(INSIGHTS_COLLECTION).document(neighbor.id).get()
                    if doc.exists:
                        historical_insights.append(doc.to_dict())
            print(f"Found {len(historical_insights)} related historical insights.")

        # 3. Synthesize with Gemini Pro
        if not historical_insights:
            print("No related insights found. No synergy analysis needed.")
            return "OK", 204

        prompt = f"""... (Construct a detailed prompt with the new insight and historical ones) ..."""
        
        print("Generating synergy analysis with Gemini Pro...")
        analysis_response = model.generate_content(prompt)

        # 4. Save the report
        report_data = {
            "type": "synergy_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
            "new_insight_id": new_insight_id,
            "related_insight_ids": [h['insight_id'] for h in historical_insights],
            "analysis_summary": analysis_response.text
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        print("Successfully created and stored synergy analysis report.")

        return "OK", 200

    except Exception as e:
        print(f"ERROR: An unexpected error occurred in Synergy Analyzer: {e}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
