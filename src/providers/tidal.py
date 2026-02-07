import requests
import json


def tidal_get_track_info(search):
    url = f"https://wolf.qqdl.site/search/?s={search}"
    search_result = requests.get(url)
    if search_result:
        return search_result.json()
    else:
        return("Error: Unable to fetch data from Tidal.")


def tidal_main(search):
    raw_data = tidal_get_track_info(search)

    if not raw_data or "data" not in raw_data:
        return None


    for item in raw_data["data"]["items"]:
        for bleh in item.values():           
            if bleh == search:
                return True


    


