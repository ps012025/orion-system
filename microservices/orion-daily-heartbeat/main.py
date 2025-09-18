import os
import yaml
import requests
from flask import Flask, jsonify
from google.cloud import run_v2, functions_v2
from datetime import datetime

# --- Initialization ---
app = Flask(__name__)

# --- Configuration Loading ---
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Notification Function ---
def send_slack_notification(text: str):
    """Calls the reporting agent to send a notification to Slack."""
    print(f"Requesting to send Slack notification...")
    try:
        reporting_agent_url = os.environ.get("REPORTING_AGENT_URL")
        if not reporting_agent_url:
            raise ValueError("REPORTING_AGENT_URL environment variable is not set.")

        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={reporting_agent_url}'
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token = token_response.text
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        
        payload = {"slack_message": text}
        
        response = requests.post(reporting_agent_url, json=payload, timeout=30)
        response.raise_for_status()
        print("Successfully requested Slack notification.")
    except Exception as e:
        print(f"ERROR: Failed to request Slack notification: {e}")

# --- Core Health Check Logic ---
@app.route("/", methods=["POST"])
def handle_request():
    print("Received request to perform system-wide health check.")
    
    try:
        config = load_config()
        agents = config.get('aiFleetAgents', [])
        
        project_id = os.environ.get("GCP_PROJECT")
        if not project_id:
            return jsonify({"error": "GCP_PROJECT environment variable not set."}), 500

        region = "asia-northeast1"
        parent = f"projects/{project_id}/locations/{region}"
        
        # --- Get all deployed services (Cloud Run & Cloud Functions) ---
        deployed_service_urls = {}
        try:
            # Cloud Run services
            run_client = run_v2.ServicesClient()
            run_request = run_v2.ListServicesRequest(parent=parent)
            for service in run_client.list_services(request=run_request):
                service_name = service.name.split('/')[-1]
                deployed_service_urls[service_name] = service.uri
            
            # Cloud Functions services
            func_client = functions_v2.FunctionServiceClient()
            func_request = functions_v2.ListFunctionsRequest(parent=parent)
            for func in func_client.list_functions(request=func_request):
                # The service name in Cloud Run is the same as the function name
                service_name = func.name.split('/')[-1]
                deployed_service_urls[service_name] = func.service_config.uri
        except Exception as e:
            print(f"Warning: Could not list all deployed services via API: {e}. Health check may be incomplete.")

        print(f"Found {len(deployed_service_urls)} deployed services. Pinging...")

        health_results = []
        for agent in agents:
            service_name = agent.get('serviceName')
            if not service_name or service_name not in deployed_service_urls:
                continue

            url = deployed_service_urls[service_name]
            status, status_code = "", 0
            
            try:
                # Use a HEAD request for a lightweight health check
                response = requests.head(url, timeout=10, allow_redirects=True)
                status_code = response.status_code
                status = "OK" # Any response means the service is up
            except requests.exceptions.Timeout:
                status, status_code = "TIMEOUT", -1
            except requests.exceptions.ConnectionError:
                status, status_code = "CONNECTION_ERROR", -2
            except Exception as e:
                status, status_code = f"UNKNOWN_ERROR", -3

            result = {"serviceName": service_name, "status": status, "http_code": status_code, "url": url}
            print(f"  - {result}")
            health_results.append(result)

        unhealthy_services = [s for s in health_results if s['status'] != "OK"]
        
        slack_message_lines = [f"*Orion System Health Check Report: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"]
        if unhealthy_services:
            slack_message_lines.append(f":warning: *{len(unhealthy_services)} サービスが異常を報告しました。*\n")
            for s in unhealthy_services:
                slack_message_lines.append(f"> :x: *{s['serviceName']}*: {s['status']} (HTTP: {s['http_code']}) - <{s['url']}|Link>\n")
        else:
            slack_message_lines.append("✅ *全てのサービスが正常に稼働しています。*\n")
        
        send_slack_notification("\n".join(slack_message_lines))

        return jsonify({"status": "success", "results": health_results}), 200

    except Exception as e:
        print(f"An unexpected error occurred during health check: {e}")
        send_slack_notification(f":x: *【Orion】ヘルスチェック実行中にエラーが発生しました。*\n> Error: ```{e}```")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))