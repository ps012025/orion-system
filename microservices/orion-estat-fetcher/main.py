import os
import requests
import pandas as pd
from google.cloud import bigquery, secretmanager
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

# ... (Helper functions like get_estat_api_key, fetch_and_store_estat_series remain the same) ...

@app.route('/', methods=['POST'])
def estat_fetcher_http():
    print("Orion e-Stat Fetcher v2 activated...")
    # ... (The core logic from the original estat_fetcher_http function goes here) ...
    return "e-Stat Fetcher finished successfully.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
