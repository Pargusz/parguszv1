"""
parguszv1 — Spotify Utils
Spotify link'lerini çözer ve track bilgisi alır.
"""
import re
import asyncio
import logging
from typing import Optional, List, Tuple

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import config

logger = logging.getLogger(__name__)

# ── Regex Patterns ────────────────────────────────────────────────────────────
SPOTIFY_TRACK_RE    = re.compile(r"spotify\.com/(?:[A-Za-z0-9_-]+/)?track/([A-Za-z0-9]+)")
SPOTIFY_PLAYLIST_RE = re.compile(r"spotify\.com/(?:[A-Za-z0-9_-]+/)?playlist/([A-Za-z0-9]+)")
SPOTIFY_ALBUM_RE    = re.compile(r"spotify\.com/(?:[A-Za-z0-9_-]+/)?album/([A-Za-z0-9]+)")
SPOTIFY_ARTIST_RE   = re.compile(r"spotify\.com/(?:[A-Za-z0-9_-]+/)?artist/([A-Za-z0-9]+)")

# ── Spotify Client ────────────────────────────────────────────────────────────

_sp: Optional[spotipy.Spotify] = None


def get_spotify_client() -> Optional[spotipy.Spotify]:
    """Spotify istemcisini döndürür, gerekirse oluşturur."""
    global _sp
    if _sp is None:
        if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
            logger.warning("Spotify credentials eksik. Spotify desteği devre dışı.")
            return None
        try:
            creds = SpotifyClientCredentials(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
            )
            _sp = spotipy.Spotify(auth_manager=creds)
            logger.info("✅ Spotify client hazır.")
        except Exception as e:
            logger.error(f"Spotify client oluşturulamadı: {e}")
            return None
    return _sp


# ── URL Tanıma ────────────────────────────────────────────────────────────────

def is_spotify_url(url: str) -> bool:
    return "spotify.com" in url or url.startswith("spotify:")


def detect_spotify_type(url: str) -> Optional[str]:
    """'track', 'playlist', 'album', 'artist' veya None döndürür."""
    if SPOTIFY_TRACK_RE.search(url):
        return "track"
    if SPOTIFY_PLAYLIST_RE.search(url):
        return "playlist"
    if SPOTIFY_ALBUM_RE.search(url):
        return "album"
    if SPOTIFY_ARTIST_RE.search(url):
        return "artist"
    return None


# ── Track Çözümleyici ─────────────────────────────────────────────────────────

def _format_track(track_data: dict) -> Tuple[str, int, str]:
    """
    Spotify track datasından (title_for_search, duration_ms, thumbnail) üretir.
    """
    name    = track_data.get("name", "Unknown")
    artists = ", ".join(a["name"] for a in track_data.get("artists", []))
    duration_ms = track_data.get("duration_ms", 0)

    images = (track_data.get("album") or {}).get("images", [])
    thumbnail = images[0]["url"] if images else ""

    search_query = f"{name} {artists}"
    return search_query, duration_ms // 1000, thumbnail


async def resolve_spotify_track(url: str) -> Optional[dict]:
    """
    Tek Spotify track → {'title': ..., 'search_query': ..., 'duration': ..., 'thumbnail': ...}
    """
    sp = get_spotify_client()
    if not sp:
        return None

    match = SPOTIFY_TRACK_RE.search(url)
    if not match:
        return None

    track_id = match.group(1)
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, sp.track, track_id)
        search_query, duration, thumbnail = _format_track(data)
        return {
            "title":        data.get("name", "Unknown"),
            "search_query": search_query,
            "duration":     duration,
            "thumbnail":    thumbnail,
            "source":       "spotify",
            "url":          url,
        }
    except Exception as e:
        logger.error(f"Spotify track çözümlenemedi: {e}")
        return None


async def resolve_spotify_playlist(url: str) -> List[dict]:
    """
    Spotify playlist → [{'search_query': ..., 'title': ..., ...}, ...]
    """
    sp = get_spotify_client()
    if not sp:
        return []

    match = SPOTIFY_PLAYLIST_RE.search(url)
    if not match:
        return []

    playlist_id = match.group(1)
    results = []

    try:
        loop = asyncio.get_event_loop()

        def fetch_all():
            items = []
            offset = 0
            while True:
                response = sp.playlist_items(
                    playlist_id,
                    offset=offset,
                    fields="items.track(name,artists,duration_ms,album(images)),next",
                    additional_types=["track"],
                )
                batch = response.get("items", [])
                items.extend(batch)
                if not response.get("next"):
                    break
                offset += len(batch)
            return items

        items = await loop.run_in_executor(None, fetch_all)

        for item in items:
            track = item.get("track")
            if not track:
                continue
            search_query, duration, thumbnail = _format_track(track)
            results.append({
                "title":        track.get("name", "Unknown"),
                "search_query": search_query,
                "duration":     duration,
                "thumbnail":    thumbnail,
                "source":       "spotify",
                "url":          url,
            })

        logger.info(f"Spotify playlist çözümlendi: {len(results)} şarkı")
        return results

    except Exception as e:
        logger.error(f"Spotify playlist çözümlenemedi: {e}")
        return []


async def resolve_spotify_album(url: str) -> List[dict]:
    """Spotify album → track listesi"""
    sp = get_spotify_client()
    if not sp:
        return []

    match = SPOTIFY_ALBUM_RE.search(url)
    if not match:
        return []

    album_id = match.group(1)
    results = []

    try:
        loop = asyncio.get_event_loop()

        def fetch():
            album_data = sp.album(album_id)
            tracks = album_data.get("tracks", {}).get("items", [])
            images = album_data.get("images", [])
            thumb = images[0]["url"] if images else ""
            return tracks, thumb

        tracks, thumb = await loop.run_in_executor(None, fetch)

        for track in tracks:
            search_query, duration, _ = _format_track({
                **track,
                "album": {"images": [{"url": thumb}]}
            })
            results.append({
                "title":        track.get("name", "Unknown"),
                "search_query": search_query,
                "duration":     duration,
                "thumbnail":    thumb,
                "source":       "spotify",
                "url":          url,
            })

        logger.info(f"Spotify album çözümlendi: {len(results)} şarkı")
        return results

    except Exception as e:
        logger.error(f"Spotify album çözümlenemedi: {e}")
        return []


async def resolve_spotify_url(url: str) -> Tuple[Optional[dict], List[dict]]:
    """
    Herhangi bir Spotify URL'sini çözer.
    Returns: (single_track_or_None, list_of_tracks)
    - Tek şarkı: (track_info, [])
    - Playlist/Album: (None, [tracks...])
    """
    stype = detect_spotify_type(url)

    if stype == "track":
        track = await resolve_spotify_track(url)
        return track, []

    elif stype == "playlist":
        tracks = await resolve_spotify_playlist(url)
        return None, tracks

    elif stype == "album":
        tracks = await resolve_spotify_album(url)
        return None, tracks

    return None, []
