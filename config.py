"""
parguszv1 — Config Module
Merkezi ayar yönetimi
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Discord ──────────────────────────────────────
DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN", "")
DISCORD_CLIENT_ID  = os.getenv("DISCORD_CLIENT_ID", "")

# ── Spotify ──────────────────────────────────────
SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# ── Genius ───────────────────────────────────────
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN", "")

# ── Dashboard ────────────────────────────────────
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "parguszv1_secret")
DASHBOARD_HOST       = os.getenv("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT       = int(os.getenv("DASHBOARD_PORT", os.getenv("PORT", "5000")))

# ── Bot Ayarları ─────────────────────────────────
BOT_PREFIX    = "!"           # Yedek prefix (slash komutlar öncelikli)
BOT_STATUS    = "🎵 /play ile müzik çal"
BOT_ACTIVITY  = "music"
MAX_QUEUE     = 500           # Maksimum kuyruk boyutu
VOTE_SKIP     = False         # Oy ile geçme (False = herkes geçebilir)
IDLE_TIMEOUT  = 180           # Boşta kalma süresi (saniye), sonra kanaldan ayrılır

# ── YTDL Seçenekleri ─────────────────────────────
YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,        # Her zaman tam bilgi çek (stream URL dahil)
    "cookiefile": None,
}

# Playlist için ayrı seçenek
YTDL_PLAYLIST_OPTIONS = {
    **YTDL_FORMAT_OPTIONS,
    "noplaylist": False,
    "extract_flat": True,
}

# ── FFmpeg Seçenekleri ───────────────────────────
FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-nostdin"
    ),
    "options": "-vn -filter:a 'volume=0.5'",
}

# ── Renk Paleti (Embed renkleri) ─────────────────
COLOR_PRIMARY  = 0x5865F2   # Discord blurple
COLOR_SUCCESS  = 0x57F287   # Yeşil
COLOR_WARNING  = 0xFEE75C   # Sarı
COLOR_ERROR    = 0xED4245   # Kırmızı
COLOR_INFO     = 0x5865F2   # Mavi
COLOR_SPOTIFY  = 0x1DB954   # Spotify yeşili
COLOR_YOUTUBE  = 0xFF0000   # YouTube kırmızısı
