"""
parguszv1 — Queue Manager
Kuyruk yönetim sistemi
"""
import asyncio
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List
import time


@dataclass
class Track:
    """Tek bir şarkıyı temsil eder."""
    title: str
    url: str                    # Orijinal URL (YouTube/Spotify linki)
    stream_url: str = ""        # FFmpeg'e verilecek direkt stream URL
    duration: int = 0           # Saniye cinsinden süre
    thumbnail: str = ""         # Kapak resmi URL'si
    requester_id: int = 0       # İsteyen kullanıcının ID'si
    requester_name: str = ""
    source: str = "youtube"     # "youtube" | "spotify" | "search"
    webpage_url: str = ""       # YouTube watch URL
    uploader: str = ""
    added_at: float = field(default_factory=time.time)

    @property
    def duration_str(self) -> str:
        """Süreyi MM:SS veya HH:MM:SS formatına çevirir."""
        if self.duration <= 0:
            return "?"
        h = self.duration // 3600
        m = (self.duration % 3600) // 60
        s = self.duration % 60
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @property
    def progress_bar(self, current: int = 0, length: int = 20) -> str:
        """İlerleme çubuğu döndürür."""
        if self.duration <= 0:
            return "─" * length
        filled = int(length * current / self.duration)
        bar = "▓" * filled + "░" * (length - filled)
        return f"[{bar}]"


class MusicQueue:
    """
    Sunucu başına müzik kuyruğu.
    Her Guild'in kendi MusicQueue instance'ı olur.
    """

    def __init__(self, guild_id: int):
        self.guild_id   = guild_id
        self._queue: deque[Track] = deque()
        self.current: Optional[Track] = None
        self.loop_mode: str = "off"   # "off" | "track" | "queue"
        self._lock = asyncio.Lock()
        self.volume: float = 0.5      # 0.0 – 2.0 arası
        self.start_time: float = 0.0  # Şu anki şarkının başlama zamanı
        self.paused_at: float = 0.0
        self.is_paused: bool = False

    # ── Temel Kuyruk İşlemleri ────────────────────

    def add(self, track: Track) -> int:
        """Kuyruğa şarkı ekler. Kuyruktaki pozisyonunu döndürür."""
        self._queue.append(track)
        return len(self._queue)

    def add_many(self, tracks: List[Track]) -> int:
        """Birden fazla şarkı ekler."""
        self._queue.extend(tracks)
        return len(tracks)

    def pop_next(self) -> Optional[Track]:
        """
        Sonraki şarkıyı döndürür.
        Loop moduna göre davranış değişir.
        """
        if self.loop_mode == "track" and self.current:
            return self.current

        if not self._queue:
            if self.loop_mode == "queue" and self.current:
                # Queue loop: current'ı kuyruğun sonuna ekle
                self._queue.append(self.current)
                self.current = self._queue.popleft()
                return self.current
            self.current = None
            return None

        if self.loop_mode == "queue" and self.current:
            self._queue.append(self.current)

        self.current = self._queue.popleft()
        return self.current

    def clear(self):
        """Kuyruğu temizler."""
        self._queue.clear()

    def shuffle(self):
        """Kuyruğu karıştırır."""
        lst = list(self._queue)
        random.shuffle(lst)
        self._queue = deque(lst)

    def remove(self, index: int) -> Optional[Track]:
        """Belirli bir indeksteki şarkıyı siler (1'den başlar)."""
        lst = list(self._queue)
        if 0 <= index - 1 < len(lst):
            removed = lst.pop(index - 1)
            self._queue = deque(lst)
            return removed
        return None

    def move(self, from_idx: int, to_idx: int) -> bool:
        """Şarkıyı kuyrukte taşır."""
        lst = list(self._queue)
        if not (0 <= from_idx - 1 < len(lst) and 0 <= to_idx - 1 < len(lst)):
            return False
        track = lst.pop(from_idx - 1)
        lst.insert(to_idx - 1, track)
        self._queue = deque(lst)
        return True

    # ── Property'ler ─────────────────────────────

    @property
    def upcoming(self) -> List[Track]:
        """Kuyruktaki şarkıların listesi."""
        return list(self._queue)

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def total_duration(self) -> int:
        """Kuyruktaki toplam süre (saniye)."""
        return sum(t.duration for t in self._queue)

    @property
    def total_duration_str(self) -> str:
        secs = self.total_duration
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

    @property
    def current_position(self) -> int:
        """Şu anki şarkıda geçen süre (saniye)."""
        if not self.current or self.start_time == 0:
            return 0
        if self.is_paused:
            return int(self.paused_at - self.start_time)
        return int(time.time() - self.start_time)

    # ── Volume ───────────────────────────────────

    def set_volume(self, volume: int) -> float:
        """
        Volume 0–200 arasında tam sayı alır.
        İç temsil 0.0–2.0'dır.
        """
        self.volume = max(0.0, min(2.0, volume / 100))
        return self.volume

    # ── Loop ─────────────────────────────────────

    def cycle_loop(self) -> str:
        """Loop modunu döngüsel olarak değiştirir."""
        modes = ["off", "track", "queue"]
        idx = modes.index(self.loop_mode)
        self.loop_mode = modes[(idx + 1) % len(modes)]
        return self.loop_mode

    # ── Repr ─────────────────────────────────────

    def __repr__(self):
        return (
            f"<MusicQueue guild={self.guild_id} "
            f"size={self.size} loop={self.loop_mode} "
            f"current={self.current.title if self.current else 'None'}>"
        )


class QueueManager:
    """Tüm guild kuyrukları için merkezi yönetici."""

    def __init__(self):
        self._queues: dict[int, MusicQueue] = {}

    def get(self, guild_id: int) -> MusicQueue:
        """Guild için kuyruk döndürür, yoksa oluşturur."""
        if guild_id not in self._queues:
            self._queues[guild_id] = MusicQueue(guild_id)
        return self._queues[guild_id]

    def remove(self, guild_id: int):
        """Guild kuyruğunu siler."""
        self._queues.pop(guild_id, None)

    def __contains__(self, guild_id: int) -> bool:
        return guild_id in self._queues


# Global singleton
queue_manager = QueueManager()
