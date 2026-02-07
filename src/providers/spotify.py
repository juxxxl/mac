import requests
from bs4 import BeautifulSoup
import json

def spotify_search_scrape(query):
    # Format query for URL
    search_url = f"https://open.spotify.com/search/{query.replace(' ', '%20')}/tracks"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Spotify lädt Daten als JSON im <script> tag
    scripts = soup.find_all('script', {'id': 'session'})
    
    for script in scripts:
        if 'searchResults' in script.string:
            # Extract JSON data
            data = json.loads(script.string)
            return data
    
    return None
print("aa")
results = spotify_search_scrape("what we did in the desert")
print(results)
