import os
import yaml
import requests
from flask import Flask, jsonify
from google.cloud import run_v2

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
        
        health_results = []
        
        # Use the Cloud Run Admin API client to list services
        try:
            run_client = run_v2.ServicesClient()
            parent = f"projects/{project_id}/locations/{region}"
            request = run_v2.ListServicesRequest(parent=parent)
            deployed_services = run_client.list_services(request=request)
            deployed_service_names = {s.name.split('/')[-1] for s in deployed_services}
        except Exception as e:
            print(f"Warning: Could not list deployed Cloud Run services via API: {e}. Proceeding with static list.")
            deployed_service_names = set()

        print(f"Pinging {len(agents)} services defined in config...")

        for agent in agents:
            service_name = agent.get('serviceName')
            if not service_name:
                continue

            if service_name not in deployed_service_names:
                print(f"  - Skipping {service_name}: Not found as a deployed Cloud Run service.")
                continue

            url = f"https://{service_name}-{project_id}.{region}.run.app"
            status = ""
            status_code = 0
            
            try:
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
