import os
import functions_framework
import json
import requests

# --- Notification Function ---
def send_slack_notification(text: str):
    """Calls the reporting agent to send a notification to Slack."""
    print(f"Requesting to send Slack notification: {text}")
    try:
        reporting_agent_url = os.environ.get("REPORTING_AGENT_URL")
        if not reporting_agent_url:
            raise ValueError("REPORTING_AGENT_URL environment variable is not set.")

        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={reporting_agent_url}'
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token = token_response.text
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        
        payload = {"slack_message": text}
        
        response = requests.post(reporting_agent_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print("Successfully requested Slack notification.")
    except Exception as e:
        print(f"ERROR: Failed to request Slack notification: {e}")

@functions_framework.http
def job_status_notifier_http(request):
    """
    Triggered by an HTTP POST from Eventarc. This function parses the event
    from Vertex AI and sends a Slack notification.
    """
    print("Job status notifier (HTTP) triggered.")
    try:
        # The event payload is the entire request body as JSON
        event_data = request.get_json()
        if not event_data:
            print("Request body is empty or not valid JSON.")
            return "Bad Request", 400

        # Extract relevant details from the Vertex AI event payload
        # The structure is slightly different for direct HTTP events from Eventarc
        job_state = event_data.get("data", {}).get("resource", {}).get("state", "UNKNOWN_STATE")
        job_name = event_data.get("data", {}).get("resource", {}).get("displayName", "Unknown Job")
        error_message = event_data.get("data", {}).get("resource", {}).get("error", {}).get("message", "No error details.")

        print(f"Received status '{job_state}' for job '{job_name}'.")

        if job_state == "JOB_STATE_SUCCEEDED":
            slack_message = f"✅ *【Orion】Alpha Generation Loopが正常に完了しました。*\n> Job Name: `{job_name}`"
        elif job_state == "JOB_STATE_FAILED":
            slack_message = f":x: *【Orion】Alpha Generation Loopが失敗しました。*\n> Job Name: `{job_name}`\n> Error: ```{error_message}```"
        else:
            print(f"Ignoring non-terminal job state: {job_state}")
            return "OK", 200

        send_slack_notification(slack_message)
        return "OK", 200

    except Exception as e:
        print(f"ERROR: Failed to process job status event: {e}")
        send_slack_notification(f":warning: *【Orion】ジョブ完了通知の処理に失敗しました。*\n> Error: ```{e}```")
        return "OK", 200 # Return 200 to prevent Eventarc from retrying