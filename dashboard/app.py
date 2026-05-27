"""
parguszv1 — Web Dashboard
Flask tabanlı kontrol paneli
"""
import threading
from typing import Optional

from flask import Flask, render_template, jsonify, request, redirect, url_for
import discord

import config


def create_app(bot) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = config.DASHBOARD_SECRET_KEY

    # ── API Endpoints ─────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def api_status():
        """Bot durumu ve tüm sunucu bilgisi."""
        guilds_data = []
        for guild in bot.guilds:
            from utils.queue import queue_manager
            q = queue_manager.get(guild.id)
            vc = guild.voice_client

            guilds_data.append({
                "id":        str(guild.id),
                "name":      guild.name,
                "icon":      str(guild.icon.url) if guild.icon else "",
                "is_playing": vc is not None and vc.is_playing(),
                "is_paused":  vc is not None and vc.is_paused(),
                "in_vc":     vc is not None and vc.is_connected(),
                "vc_channel": vc.channel.name if vc and vc.is_connected() else None,
                "current":   {
                    "title":     q.current.title if q.current else None,
                    "url":       q.current.url if q.current else None,
                    "thumbnail": q.current.thumbnail if q.current else None,
                    "duration":  q.current.duration if q.current else 0,
                    "position":  q.current_position if q.current else 0,
                    "requester": q.current.requester_name if q.current else None,
                } if q.current else None,
                "queue_size":    q.size,
                "queue_total":   q.total_duration_str,
                "loop_mode":     q.loop_mode,
                "volume":        int(q.volume * 100),
            })

        return jsonify({
            "bot_name":    str(bot.user),
            "bot_id":      str(bot.user.id),
            "latency_ms":  round(bot.latency * 1000) if (bot.latency is not None and bot.latency == bot.latency) else 0,
            "guild_count": len(bot.guilds),
            "guilds":      guilds_data,
        })

    @app.route("/api/guild/<int:guild_id>/queue")
    def api_queue(guild_id: int):
        from utils.queue import queue_manager
        q = queue_manager.get(guild_id)
        tracks = [
            {
                "title":     t.title,
                "url":       t.url,
                "duration":  t.duration,
                "thumbnail": t.thumbnail,
                "requester": t.requester_name,
                "source":    t.source,
            }
            for t in q.upcoming
        ]
        return jsonify({"queue": tracks, "total": len(tracks)})

    @app.route("/api/guild/<int:guild_id>/skip", methods=["POST"])
    def api_skip(guild_id: int):
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({"error": "Guild not found"}), 404
        vc = guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            return jsonify({"success": True, "message": "Skipped"})
        return jsonify({"error": "Not playing"}), 400

    @app.route("/api/guild/<int:guild_id>/pause", methods=["POST"])
    def api_pause(guild_id: int):
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({"error": "Guild not found"}), 404
        vc = guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            return jsonify({"success": True, "message": "Paused"})
        if vc and vc.is_paused():
            vc.resume()
            return jsonify({"success": True, "message": "Resumed"})
        return jsonify({"error": "Not playing"}), 400

    @app.route("/api/guild/<int:guild_id>/stop", methods=["POST"])
    def api_stop(guild_id: int):
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({"error": "Guild not found"}), 404
        from utils.queue import queue_manager
        q = queue_manager.get(guild_id)
        q.clear()
        q.current = None
        vc = guild.voice_client
        if vc:
            vc.stop()
        return jsonify({"success": True, "message": "Stopped"})

    @app.route("/api/guild/<int:guild_id>/volume", methods=["POST"])
    def api_volume(guild_id: int):
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({"error": "Guild not found"}), 404

        data = request.json or {}
        level = int(data.get("level", 100))
        level = max(0, min(200, level))

        from utils.queue import queue_manager
        q = queue_manager.get(guild_id)
        q.set_volume(level)

        vc = guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = q.volume

        return jsonify({"success": True, "volume": level})

    @app.route("/api/guild/<int:guild_id>/loop", methods=["POST"])
    def api_loop(guild_id: int):
        from utils.queue import queue_manager
        q = queue_manager.get(guild_id)
        mode = q.cycle_loop()
        return jsonify({"success": True, "loop_mode": mode})

    @app.route("/api/guild/<int:guild_id>/shuffle", methods=["POST"])
    def api_shuffle(guild_id: int):
        from utils.queue import queue_manager
        q = queue_manager.get(guild_id)
        q.shuffle()
        return jsonify({"success": True, "message": f"Shuffled {q.size} tracks"})

    return app
