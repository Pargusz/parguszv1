"""
parguszv1 — Music Cog
Tüm müzik komutları ve ses kanalı yönetimi
"""
import asyncio
import logging
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from utils.queue import Track, queue_manager
from utils.player import (
    make_track_from_url,
    make_track_from_spotify_info,
    fetch_youtube_playlist,
    resolve_stream_url,
    build_ffmpeg_source,
    is_youtube_playlist,
    is_youtube_url,
    is_url,
)
from utils.spotify import is_spotify_url, resolve_spotify_url
from utils import embeds

logger = logging.getLogger(__name__)


class Music(commands.Cog):
    """
    parguszv1 Müzik Sistemi
    ────────────────────────
    • YouTube URL/playlist/arama
    • Spotify track/playlist/album
    • Chat'e link yazıldığında otomatik algılama
    • Kuyruk, loop, shuffle, volume
    • Boşta kalınca otomatik ayrılma
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._idle_checker.start()

    def cog_unload(self):
        self._idle_checker.cancel()

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    async def _get_voice_client(
        self, interaction: discord.Interaction
    ) -> Optional[discord.VoiceClient]:
        """Kullanıcının kanalına bağlanır; bağlı değilse hata gönderir."""
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice:
            await interaction.followup.send(
                embed=embeds.error_embed("Önce bir ses kanalına gir!"), ephemeral=True
            )
            return None

        vc_channel = member.voice.channel

        if interaction.guild.voice_client is None:
            try:
                vc = await vc_channel.connect(timeout=10, reconnect=True)
            except Exception as e:
                logger.error(f"Ses kanalına bağlanılamadı: {e}")
                await interaction.followup.send(
                    embed=embeds.error_embed(f"Ses kanalına bağlanılamadı: {e}"),
                    ephemeral=True,
                )
                return None
            return vc

        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc.channel != vc_channel:
            await vc.move_to(vc_channel)
        return vc

    async def _play_next(self, guild: discord.Guild):
        """
        Kuyruktaki sonraki şarkıyı çalar.
        Otomatik çağrılır (after callback).
        """
        q = queue_manager.get(guild.id)
        track = q.pop_next()

        if track is None:
            # Kuyruk bitti, çalmayı durdur
            logger.info(f"[{guild.name}] Kuyruk bitti.")
            return

        vc: discord.VoiceClient = guild.voice_client
        if vc is None or not vc.is_connected():
            logger.warning(f"[{guild.name}] VoiceClient bağlı değil, çalma atlandı.")
            return

        # Stream URL'si lazım (lazy resolve)
        stream_url = await resolve_stream_url(track, asyncio.get_event_loop())
        if not stream_url:
            logger.error(f"Stream URL alınamadı: {track.title}")
            # Bir sonrakine geç
            await self._play_next(guild)
            return

        # Ses kaynağı oluştur
        source = build_ffmpeg_source(stream_url, volume=q.volume)

        def after_play(error):
            if error:
                logger.error(f"Çalma hatası [{track.title}]: {error}")
            # Sonraki şarkıyı çal
            asyncio.run_coroutine_threadsafe(
                self._play_next(guild), self.bot.loop
            )

        q.start_time = time.time()
        q.is_paused  = False
        vc.play(source, after=after_play)

        # Now playing mesajı gönder
        text_ch = self._get_text_channel(guild)
        if text_ch:
            try:
                await text_ch.send(embed=embeds.now_playing_embed(track, q))
            except Exception:
                pass

        logger.info(f"[{guild.name}] ▶ {track.title}")

    def _get_text_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Bot'un son mesaj gönderdiği kanalı döndürür (kaydedilmişse)."""
        return getattr(self.bot, "_last_channel", {}).get(guild.id)

    def _set_text_channel(self, guild: discord.Guild, channel: discord.TextChannel):
        if not hasattr(self.bot, "_last_channel"):
            self.bot._last_channel = {}
        self.bot._last_channel[guild.id] = channel

    # ── Otomatik Link Algılama ────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Chat'e YouTube veya Spotify linki yazıldığında otomatik çalar.
        """
        if message.author.bot:
            return
        if not message.guild:
            return

        content = message.content.strip()

        # Link var mı?
        is_yt = is_youtube_url(content) or (is_url(content) and "youtu" in content)
        is_sp = is_spotify_url(content)

        if not (is_yt or is_sp):
            return

        # Kullanıcı ses kanalında mı?
        member = message.author
        if not isinstance(member, discord.Member) or not member.voice:
            return

        # Ses kanalına bağlan
        vc_channel = member.voice.channel
        guild = message.guild

        if guild.voice_client is None:
            try:
                vc = await vc_channel.connect(timeout=10, reconnect=True)
            except Exception as e:
                await message.reply(embed=embeds.error_embed(f"Bağlanamadım: {e}"))
                return
        else:
            vc = guild.voice_client
            if vc.channel != vc_channel:
                await vc.move_to(vc_channel)

        self._set_text_channel(guild, message.channel)

        # İşleme başla
        async with message.channel.typing():
            await self._handle_url(content, member, message.channel, guild, vc)

    # ── URL İşleyici (ortak) ──────────────────────────────────────────────────

    async def _handle_url(
        self,
        url: str,
        requester: discord.Member,
        channel,
        guild: discord.Guild,
        vc: discord.VoiceClient,
    ):
        """URL'yi çözümler ve kuyruğa ekler."""
        q = queue_manager.get(guild.id)
        loop = asyncio.get_event_loop()

        # ── Spotify ───────────────────────────────────────────────────────────
        if is_spotify_url(url):
            single, playlist_tracks = await resolve_spotify_url(url)

            if single:
                track = await make_track_from_spotify_info(single, requester, loop)
                if track:
                    pos = q.add(track)
                    await channel.send(embed=embeds.added_embed(track, pos))
                    if not vc.is_playing() and not vc.is_paused():
                        await self._play_next(guild)
                else:
                    await channel.send(embed=embeds.error_embed("Spotify şarkısı bulunamadı."))

            elif playlist_tracks:
                # Playlistler için ilk şarkıyı hemen çal, gerisini arka planda ekle
                tracks_resolved = []
                first_added = False

                for i, info in enumerate(playlist_tracks):
                    track = await make_track_from_spotify_info(info, requester, loop)
                    if not track:
                        continue
                    q.add(track)
                    if not first_added:
                        first_added = True
                        if not vc.is_playing() and not vc.is_paused():
                            await self._play_next(guild)

                await channel.send(
                    embed=embeds.added_playlist_embed(
                        len(playlist_tracks), "Spotify Playlist", requester.id
                    )
                )
            else:
                await channel.send(embed=embeds.error_embed("Spotify linki çözümlenemedi."))
            return

        # ── YouTube Playlist ───────────────────────────────────────────────────
        if is_youtube_playlist(url):
            tracks = await fetch_youtube_playlist(url, requester, loop)
            if not tracks:
                await channel.send(embed=embeds.error_embed("Playlist yüklenemedi."))
                return

            q.add_many(tracks)
            await channel.send(
                embed=embeds.added_playlist_embed(
                    len(tracks), "YouTube Playlist", requester.id
                )
            )
            if not vc.is_playing() and not vc.is_paused():
                await self._play_next(guild)
            return

        # ── YouTube Tekli / Arama ─────────────────────────────────────────────
        track = await make_track_from_url(url, requester, loop)
        if not track:
            await channel.send(embed=embeds.error_embed("Şarkı bulunamadı."))
            return

        pos = q.add(track)
        if vc.is_playing() or vc.is_paused():
            await channel.send(embed=embeds.added_embed(track, pos))
        else:
            await self._play_next(guild)

    # ══════════════════════════════════════════════════════════════════════════
    # SLASH KOMUTLARI
    # ══════════════════════════════════════════════════════════════════════════

    @app_commands.command(name="play", description="▶️ YouTube/Spotify linki veya arama terimi ile müzik çal")
    @app_commands.describe(query="YouTube linki, Spotify linki veya şarkı adı")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        self._set_text_channel(interaction.guild, interaction.channel)

        vc = await self._get_voice_client(interaction)
        if vc is None:
            return

        await interaction.followup.send(embed=embeds.info_embed(f"🔍 Aranıyor: `{query}`"))
        await self._handle_url(
            query,
            interaction.user,
            interaction.channel,
            interaction.guild,
            vc,
        )

    @app_commands.command(name="skip", description="⏭️ Sıradaki şarkıya geç")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc: discord.VoiceClient = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            await interaction.followup.send(embed=embeds.error_embed("Bot ses kanalında değil."), ephemeral=True)
            return

        if not vc.is_playing() and not vc.is_paused():
            await interaction.followup.send(embed=embeds.error_embed("Şu an çalan bir şey yok."), ephemeral=True)
            return

        q = queue_manager.get(interaction.guild.id)
        skipped = q.current

        vc.stop()  # after callback _play_next'i tetikler

        msg = f"⏭️ **{skipped.title}** atlandı." if skipped else "⏭️ Atlandı."
        await interaction.followup.send(embed=embeds.success_embed(msg))

    @app_commands.command(name="stop", description="⏹️ Çalmayı durdur ve kuyruğu temizle")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc: discord.VoiceClient = interaction.guild.voice_client
        q = queue_manager.get(interaction.guild.id)

        if vc and vc.is_connected():
            q.clear()
            q.current = None
            vc.stop()
            await interaction.followup.send(embed=embeds.success_embed("⏹️ Durduruldu ve kuyruk temizlendi."))
        else:
            await interaction.followup.send(embed=embeds.error_embed("Bot ses kanalında değil."), ephemeral=True)

    @app_commands.command(name="pause", description="⏸️ Müziği duraklat")
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc: discord.VoiceClient = interaction.guild.voice_client

        if vc and vc.is_playing():
            vc.pause()
            q = queue_manager.get(interaction.guild.id)
            q.is_paused = True
            q.paused_at = time.time()
            await interaction.followup.send(embed=embeds.success_embed("⏸️ Duraklatıldı."))
        else:
            await interaction.followup.send(embed=embeds.error_embed("Şu an çalan bir şey yok."), ephemeral=True)

    @app_commands.command(name="resume", description="▶️ Duraklatılmış müziği devam ettir")
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc: discord.VoiceClient = interaction.guild.voice_client

        if vc and vc.is_paused():
            vc.resume()
            q = queue_manager.get(interaction.guild.id)
            q.is_paused = False
            # Duraklatma süresini başlangıç zamanından çıkar
            q.start_time += time.time() - q.paused_at
            await interaction.followup.send(embed=embeds.success_embed("▶️ Devam ediyor."))
        else:
            await interaction.followup.send(embed=embeds.error_embed("Bot duraklatılmış değil."), ephemeral=True)

    @app_commands.command(name="leave", description="👋 Bot ses kanalından ayrılsın")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc: discord.VoiceClient = interaction.guild.voice_client

        if vc and vc.is_connected():
            q = queue_manager.get(interaction.guild.id)
            q.clear()
            q.current = None
            await vc.disconnect()
            queue_manager.remove(interaction.guild.id)
            await interaction.followup.send(embed=embeds.success_embed("👋 Görüşürüz!"))
        else:
            await interaction.followup.send(embed=embeds.error_embed("Bot zaten ses kanalında değil."), ephemeral=True)

    @app_commands.command(name="nowplaying", description="🎵 Şu an çalan şarkıyı göster")
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer()
        q = queue_manager.get(interaction.guild.id)

        if not q.current:
            await interaction.followup.send(embed=embeds.error_embed("Şu an çalan bir şey yok."), ephemeral=True)
            return

        await interaction.followup.send(
            embed=embeds.now_playing_embed(q.current, q, current_pos=q.current_position)
        )

    @app_commands.command(name="queue", description="📋 Müzik kuyruğunu göster")
    @app_commands.describe(page="Sayfa numarası")
    async def queue_cmd(self, interaction: discord.Interaction, page: int = 1):
        await interaction.response.defer()
        q = queue_manager.get(interaction.guild.id)
        await interaction.followup.send(embed=embeds.queue_embed(q, page=page))

    @app_commands.command(name="volume", description="🔊 Ses seviyesini ayarla (0-200)")
    @app_commands.describe(level="Ses seviyesi (0-200)")
    async def volume(self, interaction: discord.Interaction, level: int):
        await interaction.response.defer()

        if not 0 <= level <= 200:
            await interaction.followup.send(
                embed=embeds.error_embed("Ses seviyesi 0 ile 200 arasında olmalı."), ephemeral=True
            )
            return

        q = queue_manager.get(interaction.guild.id)
        q.set_volume(level)

        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = q.volume

        await interaction.followup.send(embed=embeds.volume_embed(level))

    @app_commands.command(name="loop", description="🔄 Tekrarlama modunu değiştir")
    @app_commands.describe(mode="off = kapalı, track = tek şarkı, queue = tüm kuyruk")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Kapalı",        value="off"),
        app_commands.Choice(name="Tek Şarkı",     value="track"),
        app_commands.Choice(name="Tüm Kuyruk",    value="queue"),
    ])
    async def loop_cmd(self, interaction: discord.Interaction, mode: str = ""):
        await interaction.response.defer()
        q = queue_manager.get(interaction.guild.id)

        if mode:
            q.loop_mode = mode
        else:
            mode = q.cycle_loop()

        icons = {"off": "➡️", "track": "🔂", "queue": "🔁"}
        labels = {"off": "Kapalı", "track": "Tek Şarkı", "queue": "Tüm Kuyruk"}
        await interaction.followup.send(
            embed=embeds.success_embed(f"{icons[mode]} Tekrarlama modu: **{labels[mode]}**")
        )

    @app_commands.command(name="shuffle", description="🔀 Kuyruğu karıştır")
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        q = queue_manager.get(interaction.guild.id)

        if q.is_empty:
            await interaction.followup.send(embed=embeds.error_embed("Kuyruk boş."), ephemeral=True)
            return

        q.shuffle()
        await interaction.followup.send(
            embed=embeds.success_embed(f"🔀 {q.size} şarkı karıştırıldı!")
        )

    @app_commands.command(name="remove", description="🗑️ Kuyruktan şarkı sil")
    @app_commands.describe(index="Silinecek şarkının sıra numarası")
    async def remove(self, interaction: discord.Interaction, index: int):
        await interaction.response.defer()
        q = queue_manager.get(interaction.guild.id)
        removed = q.remove(index)

        if removed:
            await interaction.followup.send(
                embed=embeds.success_embed(f"🗑️ **{removed.title}** kuyruktan silindi.")
            )
        else:
            await interaction.followup.send(
                embed=embeds.error_embed(f"Geçersiz numara: `{index}`"), ephemeral=True
            )

    @app_commands.command(name="help", description="❓ Bot komutlarını göster")
    async def help_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=embeds.help_embed())

    @app_commands.command(name="ping", description="🏓 Bot gecikmesini göster")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        color = config.COLOR_SUCCESS if latency < 100 else config.COLOR_WARNING if latency < 200 else config.COLOR_ERROR
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Gecikme: **{latency}ms**",
            color=color,
        )
        await interaction.response.send_message(embed=embed)

    # ── Boşta Kalma Kontrolü ─────────────────────────────────────────────────

    @tasks.loop(seconds=30)
    async def _idle_checker(self):
        """
        30 saniyede bir kontrol eder:
        Bot ses kanalında ama kimse dinlemiyorsa çıkar.
        """
        for guild in self.bot.guilds:
            vc: discord.VoiceClient = guild.voice_client
            if vc is None or not vc.is_connected():
                continue

            # Kanaldaki insan sayısı
            humans = [m for m in vc.channel.members if not m.bot]
            if not humans:
                # Boş kanal: çalmayı durdur ve çık
                q = queue_manager.get(guild.id)
                q.clear()
                q.current = None
                await vc.disconnect()
                queue_manager.remove(guild.id)
                logger.info(f"[{guild.name}] Boş kanaldan ayrıldı.")

                ch = self._get_text_channel(guild)
                if ch:
                    try:
                        await ch.send(
                            embed=embeds.info_embed(
                                "Ses kanalında kimse kalmadı, ayrıldım. 👋"
                            )
                        )
                    except Exception:
                        pass

    @_idle_checker.before_loop
    async def before_idle_checker(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
