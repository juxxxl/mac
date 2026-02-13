from search.providers.spotify import search_spotify
from search.data import Results


def searchHandler():
    query = input("search@mac # ")
    if "@" in query:
        query, artist = query.split(sep="@")
    else:
        artist = None
    
    spotifyResponse = search_spotify(query, artist)
    print(f"Spotify{spotifyResponse}")
    return spotifyResponse
