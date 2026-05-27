/* ─────────────────────────────────────────────────────────
   parguszv1 Dashboard — JavaScript
   Auto-refresh, controls, queue modal
   ───────────────────────────────────────────────────────── */

const REFRESH_INTERVAL = 3000; // ms

let guildsState = {};   // guildId → {guildData}
let queueModal  = null; // currently open guild id

// ── Format helpers ────────────────────────────────────────

function fmtDuration(secs) {
  if (!secs || secs <= 0) return '?';
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  return `${m}:${String(s).padStart(2,'0')}`;
}

function progressPct(pos, dur) {
  if (!dur || dur <= 0) return 0;
  return Math.min(100, Math.round((pos / dur) * 100));
}

// ── Build Guild Card ──────────────────────────────────────

function buildCard(guild) {
  const { id, name, icon, is_playing, is_paused, in_vc, vc_channel, current, queue_size, loop_mode, volume } = guild;

  // Status
  let statusLabel = 'Boşta';
  let statusClass = 'idle';
  if (is_playing) { statusLabel = '▶ Çalıyor'; statusClass = 'playing'; }
  else if (is_paused) { statusLabel = '⏸ Duraklatıldı'; statusClass = 'paused'; }

  // Icon
  const iconHtml = icon
    ? `<img class="guild-icon" src="${icon}" alt="${name}" />`
    : `<div class="guild-icon">🏠</div>`;

  // Now Playing section
  let npHtml;
  if (current) {
    const pct  = progressPct(current.position, current.duration);
    const pos  = fmtDuration(current.position);
    const dur  = fmtDuration(current.duration);
    const thumb = current.thumbnail
      ? `<img class="track-thumb" src="${current.thumbnail}" alt="cover" />`
      : `<div class="track-thumb" style="background:#1a1b23;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">🎵</div>`;

    npHtml = `
      <div class="now-playing">
        ${thumb}
        <div class="track-info">
          <div class="track-title">
            <a href="${current.url}" target="_blank" rel="noopener">${escHtml(current.title)}</a>
          </div>
          <div class="track-meta">
            ${current.requester ? `👤 ${escHtml(current.requester)}` : ''}
            ${vc_channel ? ` • 🔊 ${escHtml(vc_channel)}` : ''}
          </div>
          <div class="progress-wrap">
            <div class="progress-bar"><div class="progress-fill" id="prog-${id}" style="width:${pct}%"></div></div>
            <div class="progress-times"><span id="pos-${id}">${pos}</span><span>${dur}</span></div>
          </div>
        </div>
      </div>`;
  } else {
    npHtml = `<div class="idle-state">🎵 Şu an hiçbir şey çalmıyor</div>`;
  }

  // Loop icon
  const loopIcons = { off: '➡️', track: '🔂', queue: '🔁' };
  const loopIcon  = loopIcons[loop_mode] || '➡️';

  // Controls
  const playPauseIcon = is_paused ? '▶️' : (is_playing ? '⏸️' : '▶️');

  return `
    <div class="guild-card ${is_playing ? 'is-playing' : ''}" id="card-${id}">
      <div class="card-header">
        ${iconHtml}
        <div class="guild-info">
          <div class="guild-name">${escHtml(name)}</div>
          <div class="guild-meta">${queue_size} şarkı kuyruğta</div>
        </div>
        <span class="status-badge ${statusClass}">${statusLabel}</span>
      </div>

      ${npHtml}

      <div class="controls">
        <button class="ctrl-btn danger" title="Durdur" onclick="ctrlStop('${id}')">⏹️</button>
        <button class="ctrl-btn primary" title="${is_paused ? 'Devam Ettir' : 'Duraklat'}"
          onclick="ctrlPause('${id}')" id="pp-${id}">${playPauseIcon}</button>
        <button class="ctrl-btn" title="Geç" onclick="ctrlSkip('${id}')">⏭️</button>
        <button class="mode-badge ${loop_mode !== 'off' ? 'active' : ''}"
          onclick="ctrlLoop('${id}')" title="Döngü">${loopIcon} ${loop_mode}</button>
        <button class="queue-btn" onclick="openQueue('${id}')">📋 Kuyruk (${queue_size})</button>
        <div class="volume-wrap">
          🔊
          <input type="range" class="volume-slider" min="0" max="200" value="${volume}"
            oninput="ctrlVolume('${id}', this.value)"
            id="vol-${id}" />
          <span id="vol-lbl-${id}">${volume}%</span>
        </div>
      </div>
    </div>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Fetch & Render ────────────────────────────────────────

async function fetchStatus() {
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();

    // Header
    document.getElementById('latency-val').textContent = `${data.latency_ms} ms`;
    document.getElementById('guild-count').textContent  = `${data.guild_count} sunucu`;

    const grid       = document.getElementById('guilds-grid');
    const emptyState = document.getElementById('empty-state');

    if (!data.guilds || data.guilds.length === 0) {
      grid.innerHTML = '';
      emptyState.style.display = 'block';
      return;
    }
    emptyState.style.display = 'none';

    data.guilds.forEach(guild => {
      guildsState[guild.id] = guild;
      const existing = document.getElementById(`card-${guild.id}`);
      if (existing) {
        // Smooth update: only update changing parts
        updateCard(guild, existing);
      } else {
        grid.insertAdjacentHTML('beforeend', buildCard(guild));
      }
    });
  } catch (err) {
    console.warn('Status fetch failed:', err);
  }
}

function updateCard(guild, cardEl) {
  const { id, is_playing, is_paused, current, queue_size, loop_mode, volume } = guild;

  // Status badge
  const badge = cardEl.querySelector('.status-badge');
  if (badge) {
    badge.className = `status-badge ${is_playing ? 'playing' : is_paused ? 'paused' : 'idle'}`;
    badge.textContent = is_playing ? '▶ Çalıyor' : is_paused ? '⏸ Duraklatıldı' : 'Boşta';
  }

  // Play/pause button
  const ppBtn = document.getElementById(`pp-${id}`);
  if (ppBtn) ppBtn.textContent = is_paused ? '▶️' : (is_playing ? '⏸️' : '▶️');

  // Queue count
  const qBtn = cardEl.querySelector('.queue-btn');
  if (qBtn) qBtn.textContent = `📋 Kuyruk (${queue_size})`;

  const qMeta = cardEl.querySelector('.guild-meta');
  if (qMeta) qMeta.textContent = `${queue_size} şarkı kuyruğta`;

  // Progress
  if (current) {
    const progEl = document.getElementById(`prog-${id}`);
    const posEl  = document.getElementById(`pos-${id}`);
    if (progEl) progEl.style.width = `${progressPct(current.position, current.duration)}%`;
    if (posEl)  posEl.textContent  = fmtDuration(current.position);
  }

  // Volume
  const volSlider = document.getElementById(`vol-${id}`);
  const volLbl    = document.getElementById(`vol-lbl-${id}`);
  if (volSlider && document.activeElement !== volSlider) volSlider.value = volume;
  if (volLbl) volLbl.textContent = `${volume}%`;
}

// ── Controls ──────────────────────────────────────────────

async function ctrlSkip(guildId) {
  await fetch(`/api/guild/${guildId}/skip`, { method: 'POST' });
  setTimeout(fetchStatus, 500);
}

async function ctrlPause(guildId) {
  await fetch(`/api/guild/${guildId}/pause`, { method: 'POST' });
  setTimeout(fetchStatus, 300);
}

async function ctrlStop(guildId) {
  await fetch(`/api/guild/${guildId}/stop`, { method: 'POST' });
  setTimeout(fetchStatus, 300);
}

async function ctrlLoop(guildId) {
  await fetch(`/api/guild/${guildId}/loop`, { method: 'POST' });
  setTimeout(fetchStatus, 300);
}

let volTimer = {};
function ctrlVolume(guildId, val) {
  document.getElementById(`vol-lbl-${guildId}`).textContent = `${val}%`;
  clearTimeout(volTimer[guildId]);
  volTimer[guildId] = setTimeout(async () => {
    await fetch(`/api/guild/${guildId}/volume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level: parseInt(val) }),
    });
  }, 300);
}

// ── Queue Modal ───────────────────────────────────────────

async function openQueue(guildId) {
  queueModal = guildId;
  const modal = document.getElementById('queue-modal');
  const body  = document.getElementById('modal-queue-body');
  modal.style.display = 'flex';
  body.innerHTML = '<p class="muted">Yükleniyor...</p>';

  try {
    const res  = await fetch(`/api/guild/${guildId}/queue`);
    const data = await res.json();

    if (!data.queue || data.queue.length === 0) {
      body.innerHTML = '<p class="muted">Kuyruk boş.</p>';
      return;
    }

    const items = data.queue.map((t, i) => {
      const thumb = t.thumbnail
        ? `<img class="q-thumb" src="${t.thumbnail}" alt="" />`
        : `<div class="q-thumb" style="background:#1a1b23;display:flex;align-items:center;justify-content:center;">🎵</div>`;
      const srcClass = t.source === 'spotify' ? 'sp' : 'yt';
      return `
        <div class="queue-item">
          <span class="q-num">${i + 1}</span>
          ${thumb}
          <div class="src-dot ${srcClass}"></div>
          <div class="q-info">
            <div class="q-title"><a href="${t.url}" target="_blank">${escHtml(t.title)}</a></div>
            <div class="q-meta">👤 ${escHtml(t.requester || '?')}</div>
          </div>
          <span class="q-dur">${fmtDuration(t.duration)}</span>
        </div>`;
    }).join('');

    body.innerHTML = `<p class="muted" style="margin-bottom:12px">${data.total} şarkı</p>${items}`;
  } catch (err) {
    body.innerHTML = '<p class="muted">Hata oluştu.</p>';
  }
}

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('queue-modal').style.display = 'none';
  queueModal = null;
});

document.getElementById('queue-modal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) {
    e.currentTarget.style.display = 'none';
    queueModal = null;
  }
});

// ── Init ──────────────────────────────────────────────────

fetchStatus();
setInterval(fetchStatus, REFRESH_INTERVAL);
