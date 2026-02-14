from search.data import Track

import requests
import re
import time
import json
import os
import hashlib
import hmac
import struct
import base64


_CACHE_FILE = os.path.join(os.path.dirname(__file__), ".spotify_cache.json")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"


_TOTP_SECRETS = {
    59: [123,105,79,70,110,59,52,125,60,49,80,70,89,75,80,86,63,53,123,37,117,49,52,93,77,62,47,86,48,104,68,72],
    60: [79,109,69,123,90,65,46,74,94,34,58,48,70,71,92,85,122,63,91,64,87,87],
    61: [44,55,47,42,70,40,34,114,76,74,50,111,120,97,75,76,94,102,43,69,49,120,118,80,64,78],
}
_TOTP_VERSION = 61


def _generate_totp():
    secret_list = _TOTP_SECRETS[_TOTP_VERSION]

    transformed = bytes(b ^ ((i % 33) + 9) for i, b in enumerate(secret_list))

    joined = "".join(str(b) for b in transformed)
    hex_str = joined.encode().hex()
    hex_bytes = bytes.fromhex(hex_str)

    secret_b32 = base64.b32encode(hex_bytes).decode().rstrip("=")

    key = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8), casefold=True)
    counter = int(time.time()) // 30
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    totp_code = str(code % 10**6).zfill(6)

    return totp_code, _TOTP_VERSION

def _load_cache():
    try:
        with open(_CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache):
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass


class SpotifyClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.access_token = None
        self.client_token = None
        self.client_id = None
        self.device_id = None
        self.client_version = None
        self._page_html = None
        self._load_from_cache()

    def _load_from_cache(self):
        cache = _load_cache()
        if cache.get("access_token") and time.time() < cache.get("token_expiry", 0) - 300:
            self.access_token = cache["access_token"]
            self.client_token = cache.get("client_token")
            self.client_id = cache.get("client_id")
            self.device_id = cache.get("device_id")
            self.client_version = cache.get("client_version")

    def _save_to_cache(self, expiry):
        _save_cache({
            "access_token": self.access_token,
            "client_token": self.client_token,
            "client_id": self.client_id,
            "device_id": self.device_id,
            "client_version": self.client_version,
            "token_expiry": expiry,
        })

    def _get_session_info(self):
        resp = self.session.get("https://open.spotify.com")
        if resp.status_code != 200:
            raise Exception(f"Spotify session init failed: HTTP {resp.status_code}")

        self._page_html = resp.text

        for cookie in resp.cookies:
            if cookie.name == "sp_t":
                self.device_id = cookie.value

        match = re.search(
            r'<script id="appServerConfig" type="text/plain">([^<]+)</script>',
            resp.text
        )
        if match:
            try:
                cfg = json.loads(base64.b64decode(match.group(1)))
                self.client_version = cfg.get("clientVersion", "")
            except Exception:
                pass

        if not self.client_version:
            ver_match = re.search(r'"clientVersion":"([^"]+)"', resp.text)
            if ver_match:
                self.client_version = ver_match.group(1)

    _SEARCH_HASH = "e0ec36bbc74e39d1787cbe8ee2939cf6ef55edd3535572521bc62b3e4159ba0d"

    def _get_access_token(self):
        totp_code, version = _generate_totp()

        resp = self.session.get("https://open.spotify.com/api/token", params={
            "reason": "init",
            "productType": "web-player",
            "totp": totp_code,
            "totpVer": str(version),
            "totpServer": totp_code,
        })

        if resp.status_code != 200:
            raise Exception(f"Spotify access token request failed: HTTP {resp.status_code}")

        data = resp.json()
        self.access_token = data.get("accessToken")
        self.client_id = data.get("clientId")

        expiry_ms = data.get("accessTokenExpirationTimestampMs", 0)
        expiry = expiry_ms / 1000 if expiry_ms else time.time() + 3600

        for cookie in resp.cookies:
            if cookie.name == "sp_t":
                self.device_id = cookie.value

        return expiry

    def _get_client_token(self):
        if not self.client_id or not self.device_id or not self.client_version:
            self._get_session_info()
            self._get_access_token()

        payload = {
            "client_data": {
                "client_version": self.client_version,
                "client_id": self.client_id,
                "js_sdk_data": {
                    "device_brand": "unknown",
                    "device_model": "unknown",
                    "os": "windows",
                    "os_version": "NT 10.0",
                    "device_id": self.device_id,
                    "device_type": "computer",
                },
            }
        }

        resp = self.session.post(
            "https://clienttoken.spotify.com/v1/clienttoken",
            json=payload,
            headers={
                "Authority": "clienttoken.spotify.com",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        if resp.status_code != 200:
            raise Exception(f"Spotify client token request failed: HTTP {resp.status_code}")

        data = resp.json()
        if data.get("response_type") != "RESPONSE_GRANTED_TOKEN_RESPONSE":
            raise Exception(f"Invalid client token response: {data.get('response_type')}")

        self.client_token = data["granted_token"]["token"]

    def initialize(self):
        self._get_session_info()
        expiry = self._get_access_token()
        self._get_client_token()
        self._save_to_cache(expiry)

    def _partner_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Token": self.client_token,
            "Spotify-App-Version": self.client_version or "",
            "Content-Type": "application/json",
        }

    def search(self, query, limit=10):
        if not self.access_token or not self.client_token:
            self.initialize()

        result = self._search_partner(query, limit)
        if result is not None:
            return result

        return self._search_standard(query, limit)

    def _search_partner(self, query, limit=10):
        payload = {
            "operationName": "searchSuggestions",
            "variables": {"query": query},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": self._SEARCH_HASH,
                }
            }
        }

        resp = self.session.post(
            "https://api-partner.spotify.com/pathfinder/v2/query",
            json=payload,
            headers=self._partner_headers(),
        )

        if resp.status_code == 401:
            self.initialize()
            resp = self.session.post(
                "https://api-partner.spotify.com/pathfinder/v2/query",
                json=payload,
                headers=self._partner_headers(),
            )

        if resp.status_code != 200:
            return None 

        data = resp.json()
        if data.get("errors"):
            return None

        return self._convert_partner_response(data)

    def _convert_partner_response(self, data):
        items = (data.get("data", {})
                     .get("searchV2", {})
                     .get("topResultsV2", {})
                     .get("itemsV2", []))

        converted = []
        for item in items:
            wrapper = item.get("item", {})
            if wrapper.get("__typename") != "TrackResponseWrapper":
                continue

            track = wrapper.get("data", {})
            name = track.get("name", "")
            if not name:
                continue

            artist_items = track.get("artists", {}).get("items", [])
            artists = []
            for a in artist_items:
                aname = a.get("profile", {}).get("name", "")
                if aname:
                    artists.append({"name": aname})

            uri = track.get("uri", "")
            tid = uri.split(":")[-1] if ":" in uri else ""

            converted.append({
                "name": name,
                "artists": artists,
                "external_urls": {"spotify": f"https://open.spotify.com/track/{tid}"},
            })

        return {"tracks": {"items": converted}}

    def _search_standard(self, query, limit=10):
        resp = self.session.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": limit},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

        if resp.status_code == 401:
            self.initialize()
            resp = self.session.get(
                "https://api.spotify.com/v1/search",
                params={"q": query, "type": "track", "limit": limit},
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

        if resp.status_code != 200:
            raise Exception(f"Spotify search failed: HTTP {resp.status_code}")

        return resp.json()



_client = None

def _get_client():
    global _client
    if _client is None:
        _client = SpotifyClient()
    return _client



def search_spotify(query, artist=None):
    client = _get_client()

    search_query = f"{query} {artist}" if artist else query

    try:
        data = client.search(search_query)
    except Exception as e:
        print(f"Spotify: {e}")
        return []

    items = data.get("tracks", {}).get("items", [])

    def _normalize(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())

    for item in items:
        title = item.get("name", "")
        if not title:
            continue

        track_artists = [a["name"] for a in item.get("artists", [])]
        track_url = item.get("external_urls", {}).get("spotify", "")

        if artist is None:
            search_match = (
                _normalize(title) in _normalize(query)
                or _normalize(query) in _normalize(title)
            )
        else:
            norm_artist = _normalize(artist)
            search_match = any(
                norm_artist in _normalize(a) or _normalize(a) in norm_artist
                for a in track_artists
            )

        if search_match:
            return [Track(title=title, artist=track_artists, url=track_url)]

    if items:
        item = items[0]
        title = item.get("name", "")
        track_artists = [a["name"] for a in item.get("artists", [])]
        track_url = item.get("external_urls", {}).get("spotify", "")
        if title:
            return [Track(title=title, artist=track_artists, url=track_url)]

    return []

