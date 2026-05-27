# 🎵 parguszv1 — Advanced Discord Music Bot

> **parguszv1** is a powerful Discord music bot that plays music from YouTube and Spotify directly in voice channels. It auto-detects links pasted in chat and includes a web dashboard for remote control.

## ✨ Features

- ▶️ **YouTube** — URL, playlist, search term
- 💚 **Spotify** — Track, album, playlist (resolves to YouTube)
- 💬 **Auto-detection** — Paste a link in chat and the bot plays it automatically
- 📋 **Queue system** — Unlimited queue, add multiple links
- 🔂 **Loop modes** — Off / Single track / Full queue
- 🔀 **Shuffle** — Randomize the queue
- 🔊 **Volume control** — 0–200%
- 🌐 **Web Dashboard** — Control the bot from your browser
- 👋 **Auto-leave** — Bot leaves when the voice channel is empty

---

## 🚀 Quick Setup (Step by Step)

### Step 1 — Get a Discord Bot Token

1. Go to: **https://discord.com/developers/applications**
2. Click **"New Application"** → name it `parguszv1`
3. Go to **Bot** tab → click **"Add Bot"**
4. Under **Privileged Gateway Intents**, enable:
   - ✅ **MESSAGE CONTENT INTENT**
   - ✅ **SERVER MEMBERS INTENT** (optional)
   - ✅ **PRESENCE INTENT** (optional)
5. Click **"Reset Token"** → copy your token
6. Under **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Bot Permissions: `Connect`, `Speak`, `Send Messages`, `Read Message History`, `Embed Links`, `Use Slash Commands`
7. Copy the generated URL and open it to add the bot to your server

### Step 2 — Get Spotify API Credentials (Optional)

1. Go to: **https://developer.spotify.com/dashboard**
2. Log in and click **"Create app"**
3. Fill in the name (`parguszv1`) and redirect URI (`http://localhost`)
4. Copy **Client ID** and **Client Secret**

### Step 3 — Install Python & FFmpeg

**Python 3.10+:**
```
https://www.python.org/downloads/
```
Make sure to check **"Add Python to PATH"** during installation.

**FFmpeg (Required for audio):**
1. Download from: https://www.gyan.dev/ffmpeg/builds/ → `ffmpeg-release-essentials.zip`
2. Extract to `C:\ffmpeg\`
3. Add `C:\ffmpeg\bin` to your Windows PATH:
   - Search "Environment Variables" in Start
   - Edit "Path" → Add `C:\ffmpeg\bin`
4. Test: Open PowerShell → type `ffmpeg -version`

### Step 4 — Configure the Bot

```powershell
# In the discordbot folder:
copy .env.example .env
```

Open `.env` and fill in your values:
```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### Step 5 — Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 6 — Run the Bot

```powershell
python bot.py
```

You should see:
```
✅ parguszv1 hazır!
Bot: parguszv1#1234 (ID: ...)
```

---

## 🎮 Commands

| Command | Description |
|---|---|
| `/play <link or search>` | Play from YouTube/Spotify or search |
| `/skip` | Skip current song |
| `/stop` | Stop and clear queue |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/queue [page]` | Show queue |
| `/nowplaying` | Show current song |
| `/volume <0-200>` | Set volume |
| `/loop [off/track/queue]` | Set loop mode |
| `/shuffle` | Shuffle queue |
| `/remove <number>` | Remove song from queue |
| `/leave` | Disconnect bot |
| `/help` | Show help |
| `/ping` | Show bot latency |

## 💬 Auto-detection

Just paste a YouTube or Spotify link in **any text channel** while you're in a voice channel — the bot will automatically join and start playing!

---

## 🌐 Web Dashboard

The dashboard starts automatically at: **http://localhost:5000**

From the dashboard you can:
- See all servers and what's playing
- Control playback (play/pause/skip/stop)
- Adjust volume
- View and manage the queue
- Toggle loop mode

---

## 📁 File Structure

```
discordbot/
├── bot.py              # Main entry point
├── config.py           # Configuration
├── .env                # Your API keys (create from .env.example)
├── .env.example        # Template
├── requirements.txt    # Python packages
├── cogs/
│   └── music.py        # All music commands
├── utils/
│   ├── player.py       # yt-dlp audio engine
│   ├── queue.py        # Queue management
│   ├── spotify.py      # Spotify resolver
│   └── embeds.py       # Discord embed templates
└── dashboard/
    ├── app.py          # Flask web server
    ├── templates/
    │   └── index.html  # Dashboard UI
    └── static/
        ├── dashboard.css
        └── dashboard.js
```

---

## ⚠️ Troubleshooting

**"ffmpeg not found"**
→ Make sure FFmpeg is installed and `C:\ffmpeg\bin` is in PATH. Restart PowerShell after adding to PATH.

**"DISCORD_TOKEN not found"**
→ Make sure `.env` file exists (copy from `.env.example`) and has your token.

**Spotify links not working**
→ Add your Spotify Client ID and Secret to `.env`. Without them, only YouTube works.

**Bot doesn't respond to links in chat**
→ Make sure **Message Content Intent** is enabled in Discord Developer Portal.

**"Sign in to confirm you're not a bot" error from YouTube**
→ Update yt-dlp: `pip install -U yt-dlp`

---

## 📜 Bot Description

```
parguszv1 — Advanced Music Bot
• Plays music from YouTube & Spotify in voice channels
• Auto-detects links pasted in chat
• Queue system with loop, shuffle & volume control
• Web dashboard for remote control
```
