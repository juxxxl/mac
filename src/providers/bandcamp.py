import asyncio
from bandcamp_async_api import BandcampAPIClient

async def bandcamp_available(query: str):
    try:
        async with BandcampAPIClient() as client:

            # Search for the track
            results = await client.search(query)
            

            # Find first track result
            track_result = next((r for r in results if r.type == "track"), None)

            if not track_result:
                return False

            track_id = track_result.id
            artist_id = track_result.artist_id 
            # Get track details using the URL
            track = await client.get_track(artist_id, track_id)
            
            if track_result.name != query:
                return False

            print(track)

            return True
    except Exception as e:
        print(e)
        print("aaa")
        return False 

# function currently not working (pasted straight from docs lol), and not used, leaving it here for future changes e.g: also loading metadata when checking availability

# async def bandcamp_search_song(query: str):
#     async with BandcampAPIClient(identity_token='7%09optional_identity_token%7D') as client:
#         # Search for music
#         results = await client.get_track()
#
#
#
#         # Get album details
#         if results:
#             album_result = next(r for r in results if r.type == "album")
#             album = await client.get_album(album_result.artist_id, album_result.id)
#             print(f"Album: {album.title} by {album.artist.name}")
#
#         # Get artist information
#         artist_result = next(r for r in results if r.type == "artist")
#         artist = await client.get_artist(artist_result.id)
#         print(f"Artist: {artist.name} - {artist.bio}")




