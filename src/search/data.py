from dataclasses import dataclass
from typing import List

@dataclass
class Track:
    title: str
    artist: str
    url: str

@dataclass
class Results: # this will most likely not be used, or maybe for exporting the data as json?
    spotify: List[Track]
    soundcloud: List[Track]
    tidal: List[Track]
    bandcamp: List[Track]
    ytmusic: List[Track]
