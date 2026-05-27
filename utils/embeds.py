"""
parguszv1 — Embed Templates
Güzel Discord embed'leri için şablonlar
"""
import math
import time
from typing import Optional, List

import discord

import config
from utils.queue import Track, MusicQueue

# ── Sabitler ─────────────────────────────────────────────────────────────────
BAR_LENGTH    = 18
LOOP_ICONS    = {"off": "➡️", "track": "🔂", "queue": "🔁"}
SOURCE_ICONS  = {"youtube": "▶️", "spotify": "💚", "search": "🔍"}
SOURCE_COLORS = {
    "youtube": config.COLOR_YOUTUBE,
    "spotify": config.COLOR_SPOTIFY,
    "search":  config.COLOR_PRIMARY,
}

FOOTER_TEXT = "parguszv1 • Music Bot"
FOOTER_ICON = "https://i.imgur.com/4OO5uNr.png"  # Bot ikonu


def _progress_bar(current: int, total: int, length: int = BAR_LENGTH) -> str:
    """İlerleme çubuğu oluşturur: ▓▓▓▓▓▓░░░░░░░"""
    if total <= 0:
        return "─" * length
    filled = min(length, int(length * current / total))
    return "▓" * filled + "░" * (length - filled)


def _duration_str(seconds: int) -> str:
    if seconds <= 0:
        return "?"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ── Now Playing ───────────────────────────────────────────────────────────────

def now_playing_embed(
    track: Track,
    queue: MusicQueue,
    *,
    current_pos: int = 0,
) -> discord.Embed:
    """Şu an çalan şarkının embed kartı."""

    source_icon  = SOURCE_ICONS.get(track.source, "🎵")
    source_color = SOURCE_COLORS.get(track.source, config.COLOR_PRIMARY)
    loop_icon    = LOOP_ICONS.get(queue.loop_mode, "➡️")

    embed = discord.Embed(
        title=f"{source_icon} Now Playing",
        color=source_color,
    )

    embed.description = f"### [{track.title}]({track.url})\n"

    # Progress bar
    bar = _progress_bar(current_pos, track.duration)
    pos_str   = _duration_str(current_pos)
    total_str = _duration_str(track.duration)
    embed.description += f"`{pos_str}` {bar} `{total_str}`\n"

    # Meta bilgileri
    embed.add_field(name="🎤 Sanatçı", value=track.uploader or "Bilinmiyor", inline=True)
    embed.add_field(name="⏱️ Süre",    value=total_str, inline=True)
    embed.add_field(
        name="🔊 Ses",
        value=f"{int(queue.volume * 100)}%",
        inline=True,
    )
    embed.add_field(name="🔄 Tekrar",    value=loop_icon, inline=True)
    embed.add_field(name="📋 Kuyruk",    value=f"{queue.size} şarkı", inline=True)
    embed.add_field(
        name="👤 İsteyen",
        value=f"<@{track.requester_id}>",
        inline=True,
    )

    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)

    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


# ── Queue ─────────────────────────────────────────────────────────────────────

def queue_embed(
    queue: MusicQueue,
    page: int = 1,
    per_page: int = 10,
) -> discord.Embed:
    """Kuyruğun sayfalı embed'i."""
    tracks = queue.upcoming
    total  = len(tracks)
    pages  = max(1, math.ceil(total / per_page))
    page   = max(1, min(page, pages))

    embed = discord.Embed(
        title="📋 Müzik Kuyruğu",
        color=config.COLOR_PRIMARY,
    )

    # Şu an çalan
    if queue.current:
        pos_str = _duration_str(queue.current_position)
        tot_str = _duration_str(queue.current.duration)
        embed.description = (
            f"**🎵 Şu An Çalıyor:**\n"
            f"[{queue.current.title}]({queue.current.url}) "
            f"`{pos_str}/{tot_str}` • <@{queue.current.requester_id}>\n\n"
        )
    else:
        embed.description = "Şu an hiçbir şey çalmıyor.\n\n"

    # Kuyruk listesi
    if not tracks:
        embed.description += "*Kuyruk boş.*"
    else:
        start = (page - 1) * per_page
        end   = min(start + per_page, total)
        lines = []
        for i, t in enumerate(tracks[start:end], start=start + 1):
            dur = _duration_str(t.duration)
            lines.append(f"`{i}.` [{t.title}]({t.url}) `[{dur}]` • <@{t.requester_id}>")
        embed.description += "\n".join(lines)

    # Footer bilgileri
    loop_icon = LOOP_ICONS.get(queue.loop_mode, "➡️")
    embed.set_footer(
        text=(
            f"{FOOTER_TEXT} • Sayfa {page}/{pages} • "
            f"Toplam: {total} şarkı • {queue.total_duration_str} • "
            f"Döngü: {loop_icon}"
        ),
        icon_url=FOOTER_ICON,
    )
    return embed


# ── Added To Queue ────────────────────────────────────────────────────────────

def added_embed(track: Track, position: int) -> discord.Embed:
    """Kuyruğa şarkı eklendiğinde gösterilir."""
    source_color = SOURCE_COLORS.get(track.source, config.COLOR_SUCCESS)
    embed = discord.Embed(
        title="✅ Kuyruğa Eklendi",
        description=f"**[{track.title}]({track.url})**",
        color=source_color,
    )
    embed.add_field(name="⏱️ Süre",      value=_duration_str(track.duration), inline=True)
    embed.add_field(name="📍 Pozisyon",  value=f"#{position}", inline=True)
    embed.add_field(name="👤 İsteyen",   value=f"<@{track.requester_id}>", inline=True)

    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


def added_playlist_embed(count: int, name: str, requester_id: int) -> discord.Embed:
    """Playlist eklendiğinde gösterilir."""
    embed = discord.Embed(
        title="✅ Playlist Kuyruğa Eklendi",
        description=f"**{name}** — `{count}` şarkı kuyruğa eklendi.",
        color=config.COLOR_SUCCESS,
    )
    embed.add_field(name="👤 İsteyen", value=f"<@{requester_id}>", inline=True)
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


# ── Error ─────────────────────────────────────────────────────────────────────

def error_embed(message: str, title: str = "❌ Hata") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=config.COLOR_ERROR)


def info_embed(message: str, title: str = "ℹ️ Bilgi") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=config.COLOR_INFO)


def success_embed(message: str, title: str = "✅ Başarılı") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=config.COLOR_SUCCESS)


# ── Volume ────────────────────────────────────────────────────────────────────

def volume_embed(volume_pct: int) -> discord.Embed:
    bar_len = 20
    filled  = int(bar_len * volume_pct / 200)
    bar     = "█" * filled + "░" * (bar_len - filled)

    icon = "🔇" if volume_pct == 0 else "🔉" if volume_pct < 50 else "🔊"
    embed = discord.Embed(
        title=f"{icon} Ses Seviyesi",
        description=f"`{bar}` **{volume_pct}%**",
        color=config.COLOR_PRIMARY,
    )
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed


# ── Help ─────────────────────────────────────────────────────────────────────

def help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎵 parguszv1 — Komut Listesi",
        description=(
            "YouTube veya Spotify linki paylaş, ben de çalarım!\n"
            "Linki sohbete yapıştırman yeterli ya da `/play` kullan."
        ),
        color=config.COLOR_PRIMARY,
    )

    embed.add_field(
        name="🎵 Müzik",
        value=(
            "`/play <link|arama>` — Şarkı veya playlist çal\n"
            "`/skip` — Sonraki şarkıya geç\n"
            "`/pause` — Duraklat\n"
            "`/resume` — Devam et\n"
            "`/stop` — Durdur ve kuyruğu temizle\n"
            "`/leave` — Ses kanalından ayrıl\n"
            "`/nowplaying` — Şu an çalanı göster\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="📋 Kuyruk",
        value=(
            "`/queue [sayfa]` — Kuyruğu göster\n"
            "`/shuffle` — Kuyruğu karıştır\n"
            "`/loop [mod]` — Tekrarlama modu\n"
            "`/remove <numara>` — Kuyruktakini sil\n"
            "`/volume <0-200>` — Ses seviyesi\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="ℹ️ Genel",
        value=(
            "`/help` — Bu menü\n"
            "`/ping` — Bot gecikmesi\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="💡 İpucu",
        value=(
            "Sohbete direkt YouTube veya Spotify linki yapıştırırsan "
            "bot otomatik olarak kuyruğa ekler ve çalmaya başlar!"
        ),
        inline=False,
    )

    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed
