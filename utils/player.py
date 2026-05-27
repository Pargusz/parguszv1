"""
parguszv1 — Music Player Engine
yt-dlp tabanlı ses akışı motoru
"""
import asyncio
import logging
import os
import re
import time
from typing import Optional, List

import discord
import yt_dlp

import config
from utils.queue import Track, MusicQueue

logger = logging.getLogger(__name__)

# FFmpeg tam yolu — PATH'e bağlı olmadan çalışır
FFMPEG_EXE = r"C:\ffmpeg\bin\ffmpeg.exe"
if not os.path.exists(FFMPEG_EXE):
    # Fallback: PATH'deki ffmpeg
    FFMPEG_EXE = "ffmpeg"
    logger.warning("C:\\ffmpeg\\bin\\ffmpeg.exe bulunamadi, PATH'deki ffmpeg kullanilacak.")

# ── YouTube URL Algılama ──────────────────────────────────────────────────────
YT_URL_RE = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|playlist\?list=|shorts/)|youtu\.be/)"
    r"[\w\-]+"
)
YT_PLAYLIST_RE = re.compile(r"[?&]list=([\w\-]+)")


def is_youtube_url(text: str) -> bool:
    return bool(YT_URL_RE.match(text))


def is_youtube_playlist(text: str) -> bool:
    return bool(YT_PLAYLIST_RE.search(text))


def is_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))


# ── YTDLSource ────────────────────────────────────────────────────────────────

class YTDLSource(discord.PCMVolumeTransformer):
    """
    discord.PCMVolumeTransformer ile sarılmış yt-dlp ses kaynağı.
    Volume kontrolü için PCMVolumeTransformer kullanıyoruz.
    """

    def __init__(self, source: discord.AudioSource, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume=volume)
        self.data      = data
        self.title     = data.get("title", "Unknown")
        self.url       = data.get("webpage_url", data.get("url", ""))
        self.thumbnail = data.get("thumbnail", "")
        self.duration  = data.get("duration", 0)
        self.uploader  = data.get("uploader", data.get("channel", "Unknown"))

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        loop: asyncio.AbstractEventLoop,
        volume: float = 0.5,
        ffmpeg_before_opts: str = "",
        ffmpeg_opts: str = "",
    ) -> "YTDLSource":
        """
        URL veya arama terimi alır, ses kaynağı döndürür.
        """
        ydl_opts = {**config.YTDL_FORMAT_OPTIONS, "noplaylist": True}

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Düz URL değilse YouTube araması yap
                query = url if is_url(url) else f"ytsearch:{url}"
                info = ydl.extract_info(query, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                return info

        data = await loop.run_in_executor(None, _extract)

        # En iyi ses formatının URL'sini al
        stream_url = data.get("url", "")

        before_opts = (
            "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin"
        )
        if ffmpeg_before_opts:
            before_opts = ffmpeg_before_opts

        opts = "-vn"
        if ffmpeg_opts:
            opts = ffmpeg_opts

        audio = discord.FFmpegPCMAudio(
            stream_url,
            before_options=before_opts,
            options=opts,
        )
        return cls(audio, data=data, volume=volume)


# ── Track Fabrikası ───────────────────────────────────────────────────────────

async def make_track_from_url(
    url: str,
    requester: discord.Member,
    loop: asyncio.AbstractEventLoop,
    source: str = "youtube",
) -> Optional[Track]:
    """
    Verilen URL için Track nesnesi oluşturur.
    Yalnızca metadata çeker; ses akışı başlatmaz.
    """
    # extract_flat OLMADAN — stream URL'yi de çekiyoruz
    ydl_opts = {
        **config.YTDL_FORMAT_OPTIONS,
        "noplaylist": True,
        "extract_flat": False,   # Tam bilgi çek
        "quiet": True,
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            query = url if is_url(url) else f"ytsearch:{url}"
            info = ydl.extract_info(query, download=False)
            if info and "entries" in info:
                info = info["entries"][0]
            return info

    try:
        data = await asyncio.get_event_loop().run_in_executor(None, _extract)
    except Exception as e:
        logger.error(f"Track bilgisi alinamadi [{url}]: {e}")
        return None

    if not data:
        return None

    # Stream URL'yi doğrula
    stream_url = data.get("url", "")
    if not stream_url:
        logger.warning(f"Stream URL bos geldi: {data.get('title','?')}")

    return Track(
        title=data.get("title", "Unknown"),
        url=data.get("webpage_url", url),
        stream_url=stream_url,
        duration=data.get("duration", 0),
        thumbnail=data.get("thumbnail", ""),
        requester_id=requester.id,
        requester_name=requester.display_name,
        source=source,
        webpage_url=data.get("webpage_url", url),
        uploader=data.get("uploader", data.get("channel", "")),
    )


async def make_track_from_spotify_info(
    info: dict,
    requester: discord.Member,
    loop: asyncio.AbstractEventLoop,
) -> Optional[Track]:
    """
    Spotify metadata dict → YouTube'da arama yap → Track döndür.
    info: {'search_query': ..., 'title': ..., 'duration': ..., 'thumbnail': ...}
    """
    search_query = info.get("search_query", info.get("title", ""))
    yt_track = await make_track_from_url(
        search_query,
        requester,
        loop,
        source="spotify",
    )
    if yt_track and not yt_track.thumbnail and info.get("thumbnail"):
        yt_track.thumbnail = info["thumbnail"]
    if yt_track and info.get("duration") and yt_track.duration == 0:
        yt_track.duration = info["duration"]
    return yt_track


async def fetch_youtube_playlist(
    url: str,
    requester: discord.Member,
    loop: asyncio.AbstractEventLoop,
) -> List[Track]:
    """
    YouTube playlist URL'sinden tüm şarkıların metadata'sını çeker.
    Stream URL'leri çekmez (lazy loading).
    """
    ydl_opts = {
        **config.YTDL_FORMAT_OPTIONS,
        "noplaylist": False,
        "extract_flat": True,
        "quiet": True,
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        data = await loop.run_in_executor(None, _extract)
    except Exception as e:
        logger.error(f"Playlist alınamadı [{url}]: {e}")
        return []

    if not data or "entries" not in data:
        return []

    tracks = []
    for entry in data["entries"]:
        if not entry:
            continue
        watch_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
        track = Track(
            title=entry.get("title", "Unknown"),
            url=watch_url,
            stream_url="",          # Lazy: çalınırken resolve edilecek
            duration=entry.get("duration", 0),
            thumbnail=entry.get("thumbnail", ""),
            requester_id=requester.id,
            requester_name=requester.display_name,
            source="youtube",
            webpage_url=watch_url,
            uploader=entry.get("uploader", entry.get("channel", "")),
        )
        tracks.append(track)

    logger.info(f"Playlist: {len(tracks)} şarkı alındı.")
    return tracks


async def resolve_stream_url(track: Track, loop: asyncio.AbstractEventLoop) -> str:
    """
    Her çalmadan önce TAZE stream URL çeker.
    YouTube stream URL'leri expire olur, her seferinde yenilenmeli.
    """
    ydl_opts = {
        **config.YTDL_FORMAT_OPTIONS,
        "noplaylist": True,
        "extract_flat": False,
        "quiet": True,
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(track.url, download=False)
            if info and "entries" in info:
                info = info["entries"][0]
            if not info:
                return ""
            return info.get("url", "")

    try:
        fresh_url = await loop.run_in_executor(None, _extract)
        if fresh_url:
            track.stream_url = fresh_url
            logger.info(f"Stream URL alindi: {track.title[:40]}")
        else:
            logger.error(f"Stream URL bos: {track.title}")
        return fresh_url
    except Exception as e:
        logger.error(f"Stream URL alinamadi [{track.url}]: {e}")
        return ""


def build_ffmpeg_source(
    stream_url: str,
    volume: float = 0.5,
    before_opts: str = "",
    extra_filters: str = "",
) -> discord.PCMVolumeTransformer:
    """
    FFmpeg ses kaynağı oluşturur.
    FFMPEG_EXE tam yoluyla çağrılır — PATH'e bağımlı değil.
    Windows uyumlu: -af filtrelerinde tek tırnak YOK.
    """
    default_before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin"
    b_opts = before_opts or default_before

    # Windows'ta -af ile single quote kullanılamaz, doğrudan yaz
    if extra_filters:
        options = f"-vn -af {extra_filters}"
    else:
        options = "-vn"

    logger.debug(f"FFmpegPCMAudio -> exe={FFMPEG_EXE}, opts={options}")

    audio = discord.FFmpegPCMAudio(
        stream_url,
        executable=FFMPEG_EXE,   # Tam yol — PATH'e bağlı değil!
        before_options=b_opts,
        options=options,
    )
    return discord.PCMVolumeTransformer(audio, volume=volume)
