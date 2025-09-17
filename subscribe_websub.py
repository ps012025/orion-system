import requests

HUB_URL = "https://pubsubhubbub.appspot.com/"
CALLBACK_URL = "https://orion-websub-handler-fyhtcd2srq-an.a.run.app"

FEEDS_TO_SUBSCRIBE = {
    'youtube_bloomberg': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCIALMKvObZNtJ6AmdCLP7Lg',
    'youtube_cnbc': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCrp_UI8XtuYfpiqluWLD7Lw',
}

def subscribe_to_feed(feed_name, topic_url):
    """Sends a subscription request to the WebSub hub."""
    print(f"Attempting to subscribe to: {feed_name} ({topic_url})")
    
    data = {
        'hub.mode': 'subscribe',
        'hub.topic': topic_url,
        'hub.callback': CALLBACK_URL,
        'hub.verify': 'async' # Or 'sync'
    }
    
    try:
        response = requests.post(HUB_URL, data=data)
        
        # A 2xx status code means the request was accepted by the hub.
        if 200 <= response.status_code < 300:
            print(f"  > Subscription request for '{feed_name}' accepted by the hub (Status: {response.status_code}).")
            print("  > The hub will now verify the callback URL asynchronously.")
        else:
            print(f"  ! Subscription request for '{feed_name}' failed.")
            print(f"  ! Status: {response.status_code}")
            print(f"  ! Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"  ! An error occurred while trying to subscribe to '{feed_name}': {e}")

if __name__ == "__main__":
    print("Starting WebSub subscription process...")
    for name, url in FEEDS_TO_SUBSCRIBE.items():
        subscribe_to_feed(name, url)
    print("\nSubscription process finished.")
