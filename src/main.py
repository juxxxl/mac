# from providers.tidal import 
from search.searchhandler import searchHandler

version = "0.0.1"
ascii_art = rf"""
                       
  _ __ ___   __ _  ___ 
 | '_ ` _ \ / _` |/ __|
 | | | | | | (_| | (__ 
 |_| |_| |_|\__,_|\___|
                  v{version}
"""

# add argparse (maybe without -- argument, just raw text)

def print_logo(services):
    print(ascii_art)
    print("currently supported services:")
    print(", ".join(services) + "\n")


if __name__ == "__main__":
    services = ["spotify",  "yt-music", "tidal", "bandcamp", "deezer", "soundcloud"]
    print_logo(services)
    searchHandler()
