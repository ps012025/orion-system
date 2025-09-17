import pandas as pd
import requests

def get_nasdaq100_tickers():
    """Scrapes the Nasdaq-100 tickers from the Wikipedia page with a proper User-Agent."""
    try:
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        # Use requests to fetch the HTML content with a User-Agent
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes
        
        # Pass the HTML content to pandas
        tables = pd.read_html(response.text)
        
        constituents_table = tables[4]
        tickers = constituents_table['Ticker'].tolist()
        print(",".join(tickers))
    except Exception as e:
        print(f"Error scraping tickers: {e}")
        return None

if __name__ == "__main__":
    get_nasdaq100_tickers()