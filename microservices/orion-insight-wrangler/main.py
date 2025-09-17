import os
import base64
import json
import trafilatura
import spacy
import numpy as np
import yaml
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform
from pytube import YouTube
import mimetypes
from flask import Flask, request, jsonify

# --- Initialization ---
app = Flask(__name__)

# --- Client Initialization ---
db = firestore.Client()
vertexai.init(project=os.environ.get("GCP_PROJECT"), location="asia-northeast1")
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
nlp = spacy.load("en_core_web_sm")

# --- Dynamic & Static Configuration ---
CONFIG_COLLECTION = "orion_system_config"
CORE_THESIS_DOC_ID = "dynamic_core_thesis"
DEFAULT_CORE_THESIS = "我々は、企業のファンダメンタルズとマクロ経済の動向に注目し、特にM&A、決算発表、技術提携に関連するニュースを重視する。"

def load_wrangler_config():
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

wrangler_config = load_wrangler_config()
SIMILARITY_THRESHOLD = wrangler_config['filters']['semantic_similarity_threshold']
SEMANTIC_CACHE_THRESHOLD = wrangler_config['semantic_cache']['similarity_threshold']
NLP_ORG_THRESHOLD = wrangler_config['filters']['nlp_org_count_threshold']
NLP_MONEY_THRESHOLD = wrangler_config['filters']['nlp_money_count_threshold']
screener_model = GenerativeModel(wrangler_config['llm_cascade']['screener']['model'])
analyst_model = GenerativeModel(wrangler_config['llm_cascade']['analyst']['model'])
index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name="3249188801473413120")
DEPLOYED_INDEX_ID = "orion_v1"

def get_dynamic_core_thesis():
    try:
        doc_ref = db.collection(CONFIG_COLLECTION).document(CORE_THESIS_DOC_ID)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('thesis_text', DEFAULT_CORE_THESIS)
        else:
            return DEFAULT_CORE_THESIS
    except Exception as e:
        print(f"コアテーゼの読み込み中にエラーが発生しました: {e}。デフォルト値を使用します。")
        return DEFAULT_CORE_THESIS

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

@app.route("/", methods=["POST"])
def process_url_http():
    data = request.get_json()
    if not data or "message" not in data or "data" not in data["message"]:
        return jsonify({"error": "Invalid Pub/Sub message format"}), 400

    url = base64.b64decode(data["message"]["data"]).decode("utf-8")
    print(f"\n--- Insight Wrangler v3.2 (Corrected Full Pipeline) ---")
    print(f"Processing URL: {url}")

    core_thesis = get_dynamic_core_thesis()
    print(f"Current Core Thesis: {core_thesis}")
    core_thesis_vector = embedding_model.get_embeddings([core_thesis])[0].values

    article_text = ""
    is_video = "youtube.com" in url or "youtu.be" in url
    
    if is_video:
        print("Modality: Video detected.")
        downloaded_page = trafilatura.fetch_url(url)
        if not downloaded_page:
            print("[Exit] Failed to fetch video page.")
            return "OK", 204
        
        metadata_text = trafilatura.extract(downloaded_page, include_comments=False, include_tables=False, no_fallback=True)
        if not metadata_text:
            print("[Exit] Could not extract video metadata.")
            return "OK", 204
        
        metadata_vector = embedding_model.get_embeddings([metadata_text[:20000]])[0].values
        similarity = cosine_similarity(core_thesis_vector, metadata_vector)
        if similarity < SIMILARITY_THRESHOLD:
            print(f"[Exit] Failed Pre-transcription Filter. Similarity {similarity:.4f} < {SIMILARITY_THRESHOLD}.")
            return "OK", 204
        
        print("Passed Pre-transcription Filter. Proceeding to transcription.")
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream: return "OK", 204
        temp_audio_path = f"/tmp/{yt.video_id}.{audio_stream.mime_type.split('/')[1]}"
        audio_stream.download(output_path="/tmp", filename=f"{yt.video_id}.{audio_stream.mime_type.split('/')[1]}")
        audio_file = Part.from_uri(uri=f"file://{temp_audio_path}", mime_type=audio_stream.mime_type)
        transcription_response = screener_model.generate_content(["Transcribe this audio.", audio_file])
        article_text = transcription_response.text
        os.remove(temp_audio_path)
    else:
        print("Modality: Text article detected.")
        article_text = trafilatura.extract(trafilatura.fetch_url(url), favor_precision=True)

    if not article_text or len(article_text) < 100:
        print("[Exit] No meaningful text content to process.")
        return "OK", 204

    text_vector = embedding_model.get_embeddings([article_text[:20000]])[0].values

    if wrangler_config['semantic_cache']['enabled']:
        neighbors = index_endpoint.find_neighbors(deployed_index_id=DEPLOYED_INDEX_ID, queries=[text_vector], num_neighbors=1)
        if neighbors and neighbors[0] and neighbors[0][0].distance > SEMANTIC_CACHE_THRESHOLD:
            print(f"[Exit] Semantic cache hit. Skipping.")
            return "OK", 204

    doc = nlp(article_text)
    if len([ent for ent in doc.ents if ent.label_ == 'ORG']) < NLP_ORG_THRESHOLD and len([ent for ent in doc.ents if ent.label_ == 'MONEY']) < NLP_MONEY_THRESHOLD:
        return "OK", 204

    screener_prompt = wrangler_config['llm_cascade']['screener']['prompt'].format(ARTICLE_TEXT=article_text[:4000])
    screener_response_raw = screener_model.generate_content(screener_prompt).text
    try:
        screener_data = json.loads(screener_response_raw.strip().replace('```json', '').replace('```', ''))
        if not screener_data.get("is_high_priority"):
            return "OK", 204
    except json.JSONDecodeError:
        print("[Warning] Screener response not valid JSON. Escalating.")

    analyst_prompt = wrangler_config['llm_cascade']['analyst']['prompt'].format(ARTICLE_TEXT=article_text)
    analysis_response = analyst_model.generate_content(analyst_prompt)
    
    doc_id = url.replace("/", "::")
    insight_data = {
        "source_url": url, "processed_at": firestore.SERVER_TIMESTAMP,
        "analysis_result": analysis_response.text, "type": "video_insight" if is_video else "external_article_insight",
        "extractor_version": "v3.2",
    }
    db.collection("orion-analysis-reports").document(doc_id).set(insight_data)
    if wrangler_config['semantic_cache']['enabled']:
        index_endpoint.upsert_datapoints(index_id=DEPLOYED_INDEX_ID, datapoints=[{"datapoint_id": doc_id, "feature_vector": text_vector}])
    
    print(f"Successfully processed and stored insight for URL: {url}")
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))