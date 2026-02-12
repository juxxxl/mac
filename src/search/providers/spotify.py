from search.data import Track

import requests
import re

# Note: Spotify loves rate-limiting. If this fails, it's spotify's fault, not mine.


def get_spotify_token():
    url = "https://open.spotify.com/embed/track/25QRktKOfGxndY4k3LoAGx" # fetch embed page to generate token (GOATED SONG)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0"
    }
    response = requests.get(url, headers=headers)
    
    # extract access token from page source
    token = re.search(r'"accessToken":"([^"]+)"', response.text) # thanks claude
    if token:
        return token.group(1)
    
    raise Exception("Could not find access token")

def search_spotify(query, artist = None):
    token = get_spotify_token()
    
    url = "https://api.spotify.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}"
    } # from spotify docs

    search_query = f"{query} {artist}" if artist else query
    parameters = {
        "q": search_query,
        "type": "track"
    }
    
    response = requests.get(url, headers=headers, params=parameters)
    if response.status_code == 429:
        print("Spotify Ratelimits Exceeded. Please try again later, or search manually.")
        return []
    elif response.status_code != 200:
        Exception(f"Error in spotify request: {response.status_code}")
        return []
    data = response.json()

    # tracks: list[Track] = []

    for item in data["tracks"]["items"]:
        if artist is None:
            search_match = item["name"].lower() in query.lower()
        else:
            search_match = any(
                artist.lower() in track_artist["name"].lower()
                for track_artist in item["artists"]
            )

        title = item["name"]
        track_artists = [a["name"] for a in item["artists"]]
        track_url = item["external_urls"]["spotify"]

        if search_match:
            return [Track(
                title=title,
                artist=track_artists,
                url=track_url
            )]
    
    return []

