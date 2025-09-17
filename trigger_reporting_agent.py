import requests
import os

def trigger_daily_report():
    """Manually triggers the orion-reporting-agent to generate and send a report."""
    
    reporting_agent_url = "https://orion-reporting-agent-100139368807.asia-northeast1.run.app"
    print(f"Attempting to trigger the daily report via POST request to: {reporting_agent_url}")

    try:
        # --- Get Identity Token for Authorization ---
        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={reporting_agent_url}'
        print("Fetching identity token from metadata server...")
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token_response.raise_for_status()
        token = token_response.text
        print("Successfully fetched identity token.")

        # Last attempt: Send a non-json request to bypass the `if request.is_json` block entirely.
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/plain"
        }
        
        print("Sending POST request with plain text content type...")
        response = requests.post(reporting_agent_url, headers=headers, data="trigger", timeout=60)
        response.raise_for_status()
        
        print("--- Trigger successful! ---")
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        print("The orion-reporting-agent should now be processing and sending the daily report.")

    except requests.exceptions.RequestException as e:
        print(f"--- Trigger failed! An error occurred during the request: {e} ---")
    except Exception as e:
        print(f"--- Trigger failed! An unexpected error occurred: {e} ---")

if __name__ == "__main__":
    trigger_daily_report()