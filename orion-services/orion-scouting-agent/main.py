import os
from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def scouting_agent_http():
    print("Orion Scouting Agent activated...")
    # --- Actual scouting logic would go here ---
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))