import os
import requests
import pandas as pd
import finnhub
from io import StringIO
from datetime import datetime
from flask import Flask
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel
import yaml

app = Flask(__name__)

# ... (Helper functions remain the same) ...

@app.route('/', methods=['POST'])
def analyze_sentiment_http():
    # ... (The core logic from the original analyze_sentiment_http function goes here) ...
    return "Successfully stored market sentiment analysis report.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))