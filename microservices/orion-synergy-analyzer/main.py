import os
import json
import base64
import functions_framework
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from datetime import datetime, timedelta, timezone

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
LOCATION = "asia-northeast1"
INSIGHTS_COLLECTION = "orion-atomic-insights"
REPORTS_COLLECTION = "orion-analysis-reports"

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client()
# Use a powerful model capable of complex reasoning and following structured prompts
model = GenerativeModel("gemini-1.5-pro-001")

# --- Data Fetching ---
def fetch_insight(insight_id: str) -> dict:
    doc_ref = db.collection(INSIGHTS_COLLECTION).document(insight_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise FileNotFoundError(f"Insight with id {insight_id} not found.")
    insight = doc.to_dict()
    insight['insight_id'] = doc.id # Ensure the ID is part of the dict
    return insight

def fetch_related_insights(symbol: str, new_insight_id: str) -> list:
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    query = db.collection(INSIGHTS_COLLECTION).where('relevant_tickers', 'array_contains', symbol).where('extracted_at', '>=', seven_days_ago.isoformat()).limit(10)
    insights = []
    for doc in query.stream():
        if doc.id != new_insight_id:
            insight = doc.to_dict()
            insight['insight_id'] = doc.id
            insights.append(insight)
    return insights

# --- Advanced Prompt Construction ---
def build_synergy_prompt(new_insight: dict, historical_insights: list) -> str:
    # Role-based Prompting
    system_instruction = """
    あなたは、M&Aのシナジー評価を専門とする、経験豊富なシニアファイナンシャルアナリストです。
    あなたの任務は、定量的データと定性的なニュースセンチメントの間に存在する複雑な関係を解き明かし、
    矛盾する情報を特定・分析し、最終的に客観的でデータに基づいた評価を下すことです。
    思考のプロセスを段階的に説明し、最終的な結論は指定されたJSONスキーマに厳密に従って出力してください。
    """

    # Chain-of-Thought (CoT) and Contradiction Analysis
    human_message = f"""
    **分析対象:**
    以下の新しいインサイトと、それに関連する過去のインサイトを統合的に分析してください。

    **新しいインサイト:**
    ```json
    {json.dumps(new_insight, indent=2, ensure_ascii=False)}
    ```

    **関連する過去のインサイト（直近7日間）:**
    ```json
    {json.dumps(historical_insights, indent=2, ensure_ascii=False)}
    ```

    **思考連鎖 (Chain-of-Thought) の指示:**
    1.  **シナジーの特定:** 新しいインサイトと過去のインサイトが、互いの信頼性を高めたり、同じ方向性を示唆したりする点（相乗効果）を全てリストアップしてください。
    2.  **矛盾の特定:** 新しいインサイトと過去のインサイトが、互いに矛盾したり、相反するシグナルを発したりしている点（矛盾点）を全てリストアップしてください。
    3.  **総合評価:** 上記のシナジーと矛盾を考慮した上で、この一連の情報が示す、最終的な投資判断への示唆を導き出してください。

    **出力指示:**
    あなたの分析と思考プロセスに基づき、以下のJSONスキーマに従って、最終的な分析結果のみを出力してください。
    思考プロセスは出力に含めないでください。
    """
    
    # The full prompt is constructed by the model call which includes the schema
    return human_message

# --- Main Logic (Pub/Sub Triggered) ---
@functions_framework.cloud_event
def synergy_analyzer_v4(cloud_event):
    print("Orion Synergy Analyzer v4 (Advanced Prompting) activated...")
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

        prompt = build_synergy_prompt(new_insight, historical_insights)
        
        # --- Structured Output Definition ---
        output_schema = {
            "type": "object",
            "properties": {
                "synergy_rating": {"type": "number", "description": "情報が互いに強め合う度合い (0.0-1.0)"},
                "contradiction_rating": {"type": "number", "description": "情報が互いに矛盾する度合い (0.0-1.0)"},
                "synergy_summary": {"type": "string", "description": "相乗効果の簡潔な要約"},
                "contradiction_summary": {"type": "string", "description": "矛盾点の簡潔な要約"},
                "final_assessment": {"type": "string", "description": "総合的な最終評価と投資判断への示唆"}
            },
            "required": ["synergy_rating", "contradiction_rating", "synergy_summary", "contradiction_summary", "final_assessment"]
        }
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=output_schema
        )

        print("Generating synergy analysis with Gemini 1.5 Pro...")
        analysis_response = model.generate_content(prompt, generation_config=generation_config)
        synergy_data = json.loads(analysis_response.text)

        # --- Store Report ---
        report_data = {
            "type": "synergy_analysis_v4",
            "created_at": firestore.SERVER_TIMESTAMP,
            "primary_insight_id": new_insight_id,
            "primary_symbol": primary_symbol,
            "synergy_result": synergy_data,
            "source_insights": [new_insight] + historical_insights # For audit trail
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        print("Successfully stored synergy analysis report.")

    except FileNotFoundError as e:
        print(f"ERROR: Could not find the triggering insight document: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in synergy analyzer: {e}")