"""
parguszv1 — Main Bot Entry Point
"""
import asyncio
import logging
import sys
import os

import discord
from discord.ext import commands

import config

# ── Logging ──────────────────────────────────────────────────────────────────
# Windows terminalinde UTF-8 zorla
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("parguszv1.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("parguszv1")

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True   # Chat'teki link algılama için gerekli
intents.voice_states    = True
intents.guilds          = True
intents.members         = False   # Privileged intent — açmak için Developer Portal'a git


# ── Bot ───────────────────────────────────────────────────────────────────────
class ParguszBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=config.BOT_PREFIX,
            intents=intents,
            help_command=None,  # Kendi /help komutumuz var
            description=(
                "parguszv1 — Advanced Music Bot\n"
                "• Plays music from YouTube & Spotify in voice channels\n"
                "• Auto-detects links pasted in chat\n"
                "• Queue system with loop, shuffle & volume control\n"
                "• Web dashboard for remote control\n"
                "• Developed by parguszv1"
            ),
        )

    async def setup_hook(self):
        """Bot başlamadan önce cog'ları yükle."""
        cogs = [
            "cogs.music",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"[OK] Cog yuklendi: {cog}")
            except Exception as e:
                logger.error(f"[HATA] Cog yuklenemedi [{cog}]: {e}")

        # Slash komutlarını Discord'a kaydet
        try:
            synced = await self.tree.sync()
            logger.info(f"[SYNC] {len(synced)} slash komut senkronize edildi.")
        except Exception as e:
            logger.error(f"Slash komut sync hatasi: {e}")

    async def on_ready(self):
        logger.info("=" * 50)
        logger.info(f"  [READY] parguszv1 hazir!")
        logger.info(f"  Bot: {self.user} (ID: {self.user.id})")
        logger.info(f"  Sunucu sayisi: {len(self.guilds)}")
        logger.info(f"  Ping: {round(self.latency * 1000)}ms")
        logger.info("=" * 50)

        # Durum mesajı
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=config.BOT_STATUS,
            ),
        )

    async def on_command_error(self, ctx, error):
        logger.warning(f"Komut hatası: {error}")

    async def on_application_command_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        msg = f"Bir hata oluştu: `{error}`"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass
        logger.error(f"Slash komut hatası: {error}")


# ── Dashboard Thread ──────────────────────────────────────────────────────────

def start_dashboard(bot_ref):
    """Web dashboard'u ayrı thread'de başlatır."""
    try:
        from dashboard.app import create_app
        app = create_app(bot_ref)
        app.run(
            host=config.DASHBOARD_HOST,
            port=config.DASHBOARD_PORT,
            debug=False,
            use_reloader=False,
        )
    except ImportError:
        logger.warning("Dashboard modülü bulunamadı, atlanıyor.")
    except Exception as e:
        logger.error(f"Dashboard başlatma hatası: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not config.DISCORD_TOKEN:
        logger.error(
            "❌ DISCORD_TOKEN bulunamadı!\n"
            "   .env dosyanı oluştur ve DISCORD_TOKEN='token_burada' ekle.\n"
            "   Örnek: .env.example dosyasına bak."
        )
        sys.exit(1)

    bot = ParguszBot()

    # Dashboard'u arka planda başlat
    import threading
    dash_thread = threading.Thread(
        target=start_dashboard, args=(bot,), daemon=True, name="dashboard"
    )
    dash_thread.start()

    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
