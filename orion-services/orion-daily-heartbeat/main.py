import os
import yaml
import requests
from flask import Flask, jsonify

# --- Initialization ---
app = Flask(__name__)

# --- Configuration Loading ---
def load_config():
    """Loads the main configuration file from the script's directory."""
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Core Health Check Logic ---
@app.route("/", methods=["POST"])
def handle_request():
    """Main entry point to run the health check for all services."""
    print("Received request to perform system-wide health check.")
    
    try:
        config = load_config()
        agents = config.get('aiFleetAgents', [])
        # This unique part of the URL is consistent across your project's Cloud Run services
        project_hash = "100139368807"
        region = "asia-northeast1"
        
        health_results = []
        services_to_check = [agent for agent in agents if agent.get('serviceName') != 'daily-heartbeat-monitor']
        
        print(f"Pinging {len(services_to_check)} services...")

        for agent in services_to_check:
            service_name = agent.get('serviceName')
            if not service_name:
                continue

            url = f"https://{service_name}-{project_hash}.{region}.run.app"
            status = ""
            status_code = 0
            
            try:
                # We use a GET request with a short timeout. 
                # We don't expect a 200 OK on the root path for most services, 
                # but a 404/405 still means the server is up and responding.
                response = requests.get(url, timeout=10)
                status_code = response.status_code
                if 200 <= status_code < 500:
                    status = "OK"
                else:
                    status = "UNHEALTHY"
            except requests.exceptions.Timeout:
                status = "TIMEOUT"
                status_code = -1
            except requests.exceptions.ConnectionError:
                status = "CONNECTION_ERROR"
                status_code = -2
            except Exception as e:
                status = f"UNKNOWN_ERROR: {e}"
                status_code = -3

            result = {
                "serviceName": service_name,
                "status": status,
                "http_code": status_code,
                "url": url
            }
            print(f"  - {result}")
            health_results.append(result)

        unhealthy_services = [s for s in health_results if s['status'] != "OK"]
        
        if unhealthy_services:
            print(f"Warning: {len(unhealthy_services)} services reported non-OK status.")
            # In a full implementation, an alert would be sent here.
        else:
            print("All services reported OK status.")

        return jsonify({"status": "success", "results": health_results}), 200

    except Exception as e:
        print(f"An unexpected error occurred during health check: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))