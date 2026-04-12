/* ─── Player IPTV — HLS.js + Video.js ───────────────────────────────────── */

let vjsPlayer = null;
let hlsInstance = null;
let allChannels = [];
let filteredChannels = [];
let currentPage = 1;
const PER_PAGE = 50;
let currentPlaylistId = null;
let currentChannelIndex = -1;

// ─── Inicialização ────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  initPlayer();
  await loadPlaylistSelector();

  // Verificar se há playlist na URL
  const params = new URLSearchParams(window.location.search);
  const playlistId = params.get("playlist");
  if (playlistId) {
    const sel = document.getElementById("playlist-selector");
    sel.value = playlistId;
    if (sel.value) {
      loadPlaylist(playlistId);
    }
  }
});

// ─── Inicializar Video.js ─────────────────────────────────────────────────────
function initPlayer() {
  vjsPlayer = videojs("main-player", {
    controls: true,
    autoplay: false,
    preload: "auto",
    fluid: true,
    responsive: true,
    playbackRates: [0.5, 1, 1.5, 2],
    html5: {
      vhs: {
        overrideNative: true,
        enableLowInitialPlaylist: true,
        smoothQualityChange: true
      }
    }
  });

  vjsPlayer.on("error", () => {
    const err = vjsPlayer.error();
    console.warn("Player error:", err);
    showPlayerError("Erro ao reproduzir o canal. Tente outro.");
  });

  vjsPlayer.on("playing", () => {
    hidePlayerOverlay();
  });
}

// ─── Carregar lista de playlists no seletor ───────────────────────────────────
async function loadPlaylistSelector() {
  try {
    const res = await apiRequest("/api/playlists");
    if (!res) return;
    const playlists = await res.json();
    const sel = document.getElementById("playlist-selector");
    sel.innerHTML = '<option value="">Selecionar playlist...</option>';
    playlists.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = `${p.name} (${p.channel_count || 0} canais)`;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error("Erro ao carregar playlists:", err);
  }
}

// ─── Carregar canais da playlist ──────────────────────────────────────────────
async function loadPlaylist(playlistId) {
  if (!playlistId) return;
  currentPlaylistId = playlistId;
  currentPage = 1;
  allChannels = [];
  filteredChannels = [];

  document.getElementById("channels-list").innerHTML = '<div class="loading-spinner">Carregando canais...</div>';
  document.getElementById("channels-count").textContent = "Carregando...";
  document.getElementById("group-filter").innerHTML = '<option value="">Todos os grupos</option>';

  try {
    // Carregar grupos
    const gRes = await apiRequest(`/api/playlists/${playlistId}/groups`);
    if (gRes && gRes.ok) {
      const groups = await gRes.json();
      const sel = document.getElementById("group-filter");
      groups.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g.group_title;
        opt.textContent = `${g.group_title} (${g.count})`;
        sel.appendChild(opt);
      });
    }

    // Carregar todos os canais (paginado)
    await loadChannelsPage(playlistId, 1, true);

  } catch (err) {
    document.getElementById("channels-list").innerHTML =
      '<div class="empty-state"><p>Erro ao carregar canais.</p></div>';
  }
}

async function loadChannelsPage(playlistId, page, reset = false) {
  const group = document.getElementById("group-filter").value;
  const search = document.getElementById("channel-search").value.trim();

  const params = new URLSearchParams({
    page,
    per_page: PER_PAGE,
    ...(group && { group }),
    ...(search && { search })
  });

  const res = await apiRequest(`/api/playlists/${playlistId}/channels?${params}`);
  if (!res || !res.ok) return;

  const data = await res.json();
  if (reset) allChannels = [];

  allChannels = data.channels;
  filteredChannels = allChannels;
  currentPage = page;

  document.getElementById("channels-count").textContent =
    `${data.total} canais${search ? ` (filtrado: "${search}")` : ""}`;

  renderChannels();
  renderPagination(data.total, page, PER_PAGE, playlistId);
}

// ─── Renderizar lista de canais ───────────────────────────────────────────────
function renderChannels() {
  const list = document.getElementById("channels-list");

  if (filteredChannels.length === 0) {
    list.innerHTML = '<div class="empty-state"><p>Nenhum canal encontrado.</p></div>';
    return;
  }

  list.innerHTML = filteredChannels.map((ch, i) => {
    const logo = ch.tvg_logo
      ? `<img class="channel-logo" src="${escapeHtml(ch.tvg_logo)}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" /><div class="channel-logo-placeholder" style="display:none">📺</div>`
      : `<div class="channel-logo-placeholder">📺</div>`;

    return `
      <div class="channel-item" id="ch-${i}" onclick="playChannel(${i})">
        ${logo}
        <div class="channel-info">
          <div class="channel-name">${escapeHtml(ch.name)}</div>
          <div class="channel-group">${escapeHtml(ch.group_title || "OUTROS")}</div>
        </div>
      </div>
    `;
  }).join("");
}

// ─── Paginação ────────────────────────────────────────────────────────────────
function renderPagination(total, page, perPage, playlistId) {
  const totalPages = Math.ceil(total / perPage);
  const pag = document.getElementById("pagination");

  if (totalPages <= 1) {
    pag.innerHTML = "";
    return;
  }

  let html = "";
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);

  if (page > 1) html += `<button class="page-btn" onclick="loadChannelsPage(${playlistId}, ${page - 1})">‹</button>`;
  if (start > 1) html += `<button class="page-btn" onclick="loadChannelsPage(${playlistId}, 1)">1</button>`;
  if (start > 2) html += `<span style="color:var(--text-muted);padding:0 4px">...</span>`;

  for (let i = start; i <= end; i++) {
    html += `<button class="page-btn ${i === page ? "active" : ""}" onclick="loadChannelsPage(${playlistId}, ${i})">${i}</button>`;
  }

  if (end < totalPages - 1) html += `<span style="color:var(--text-muted);padding:0 4px">...</span>`;
  if (end < totalPages) html += `<button class="page-btn" onclick="loadChannelsPage(${playlistId}, ${totalPages})">${totalPages}</button>`;
  if (page < totalPages) html += `<button class="page-btn" onclick="loadChannelsPage(${playlistId}, ${page + 1})">›</button>`;

  pag.innerHTML = html;
}

// ─── Filtrar canais ───────────────────────────────────────────────────────────
let filterTimeout = null;
function filterChannels() {
  clearTimeout(filterTimeout);
  filterTimeout = setTimeout(() => {
    if (currentPlaylistId) {
      loadChannelsPage(currentPlaylistId, 1, true);
    }
  }, 400);
}

// ─── Reproduzir canal ─────────────────────────────────────────────────────────
function playChannel(index) {
  const channel = filteredChannels[index];
  if (!channel) return;

  currentChannelIndex = index;

  // Atualizar UI
  document.querySelectorAll(".channel-item").forEach((el, i) => {
    el.classList.toggle("active", i === index);
  });

  // Atualizar título
  document.getElementById("now-playing-title").textContent = `▶ ${channel.name}`;
  document.title = `${channel.name} — IPTV System`;

  // Reproduzir stream
  playStream(channel.url, channel.name);
}

function playStream(url, name) {
  hidePlayerOverlay();

  // Destruir instância HLS anterior
  if (hlsInstance) {
    hlsInstance.destroy();
    hlsInstance = null;
  }

  const videoEl = document.getElementById("main-player");
  const isHLS = url.includes(".m3u8") || url.includes("/hls/") || url.includes("type=m3u_plus");
  const isMPEGTS = url.includes(".ts") || url.includes("type=ts");

  if (Hls.isSupported() && (isHLS || (!isMPEGTS && !url.includes(".mp4")))) {
    // Usar HLS.js para streams HLS
    hlsInstance = new Hls({
      enableWorker: true,
      lowLatencyMode: true,
      backBufferLength: 90,
      maxBufferLength: 30,
      maxMaxBufferLength: 600,
      startLevel: -1
    });

    // Usar Proxy Reverso para bypass de CORS e antibloqueio
  const proxyUrl = `/api/proxy?url=${encodeURIComponent(url)}`;
  
  hlsInstance.loadSource(proxyUrl);
  hlsInstance.attachMedia(videoEl);

    hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
      vjsPlayer.play().catch(() => {});
    });

    hlsInstance.on(Hls.Events.ERROR, (event, data) => {
      if (data.fatal) {
        console.warn("HLS fatal error:", data.type, data.details);
        // Tentar fallback direto
        tryDirectPlay(url, videoEl);
      }
    });
  } else {
    // Reprodução direta (MP4, TS, RTMP via proxy, etc.)
    tryDirectPlay(url, videoEl);
  }
}

function tryDirectPlay(url, videoEl) {
  // Usar Proxy Reverso para bypass de CORS e antibloqueio
  const proxyUrl = `/api/proxy?url=${encodeURIComponent(url)}`;
  
  vjsPlayer.src({ src: proxyUrl, type: guessType(url) });
  vjsPlayer.play().catch(err => {
    console.warn("Direct play error:", err);
    showPlayerError("Não foi possível reproduzir este canal. O stream pode estar offline ou bloqueado por CORS.");
  });
}

function guessType(url) {
  if (url.includes(".m3u8")) return "application/x-mpegURL";
  if (url.includes(".ts")) return "video/mp2t";
  if (url.includes(".mp4")) return "video/mp4";
  if (url.includes(".mkv")) return "video/x-matroska";
  return "application/x-mpegURL";
}

// ─── Overlay do player ────────────────────────────────────────────────────────
function hidePlayerOverlay() {
  const overlay = document.getElementById("player-overlay");
  if (overlay) overlay.classList.add("hidden");
}

function showPlayerError(msg) {
  const overlay = document.getElementById("player-overlay");
  if (overlay) {
    overlay.classList.remove("hidden");
    overlay.innerHTML = `
      <div class="overlay-content">
        <div class="overlay-icon">⚠️</div>
        <p style="color:#ff6b6b">${msg}</p>
        <button class="btn btn-outline btn-sm" style="margin-top:12px" onclick="retryChannel()">Tentar novamente</button>
      </div>
    `;
  }
}

function retryChannel() {
  if (currentChannelIndex >= 0) {
    playChannel(currentChannelIndex);
  }
}

// ─── Escape HTML ──────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
