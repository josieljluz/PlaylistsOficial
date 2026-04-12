/* ─── Dashboard — Gerenciamento de Playlists ─────────────────────────────── */

let currentTab = "url";

// ─── Troca de abas do modal ───────────────────────────────────────────────────
function switchTab(name) {
  currentTab = name;
  document.querySelectorAll(".tabs .tab-btn").forEach(btn => {
    const onclick = btn.getAttribute("onclick") || "";
    btn.classList.toggle("active", onclick.includes(`'${name}'`));
  });
  document.getElementById("tab-url").classList.toggle("hidden", name !== "url");
  document.getElementById("tab-paste").classList.toggle("hidden", name !== "paste");
}

// ─── Inicialização ────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadPlaylists();
  loadExternalAccessUrls();
});

// ─── Carregar URLs de Acesso Externo (Merged) ─────────────────────────────────
async function loadExternalAccessUrls() {
  try {
    const res = await apiRequest("/api/auth/me");
    if (!res || !res.ok) return;
    const user = await res.json();
    
    const base = window.location.origin;
    const username = encodeURIComponent(user.username);
    
    // URL da Playlist Unificada
    const unifiedUrl = `${base}/api/playlist`;
    document.getElementById("unified-playlist-url").value = unifiedUrl;
    
    // URL da API Xtream (get.php)
    const xtreamUrl = `${base}/api/get.php?username=${username}&password=SUA_SENHA`;
    document.getElementById("xtream-api-url").value = xtreamUrl;
    
  } catch (err) {
    console.error("Erro ao carregar URLs de acesso externo:", err);
  }
}

// Função de cópia genérica para o dashboard
function copyToClipboard(elementId) {
  const input = document.getElementById(elementId);
  if (!input) return;
  
  input.select();
  input.setSelectionRange(0, 99999);
  
  try {
    document.execCommand("copy");
    const btn = input.nextElementSibling;
    if (btn && btn.tagName === "BUTTON") {
      const originalText = btn.textContent;
      btn.textContent = "Copiado!";
      btn.classList.replace("btn-primary", "btn-success");
      setTimeout(() => {
        btn.textContent = originalText;
        btn.classList.replace("btn-success", "btn-primary");
      }, 2000);
    }
  } catch (err) {
    console.error("Erro ao copiar:", err);
  }
}

// ─── Carregar playlists ───────────────────────────────────────────────────────
async function loadPlaylists() {
  const grid = document.getElementById("playlists-grid");
  grid.innerHTML = '<div class="loading-spinner">Carregando playlists...</div>';

  try {
    const res = await apiRequest("/api/playlists");
    if (!res) return;
    const playlists = await res.json();

    // Atualizar stats
    const totalChannels = playlists.reduce((s, p) => s + (p.channel_count || 0), 0);
    document.getElementById("stat-playlists").textContent = formatNumber(playlists.length);
    document.getElementById("stat-channels").textContent = formatNumber(totalChannels);

    if (playlists.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <div style="font-size:48px;margin-bottom:12px">📋</div>
          <p>Nenhuma playlist cadastrada ainda.</p>
          <p>Clique em <strong>+ Nova Playlist</strong> para começar.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = playlists.map(p => renderPlaylistCard(p)).join("");
  } catch (err) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <p>Erro ao carregar playlists. Tente novamente.</p>
    </div>`;
  }
}

function renderPlaylistCard(p) {
  const badge = p.is_public
    ? '<span class="badge badge-public">Pública</span>'
    : '<span class="badge badge-private">Privada</span>';

  const updatedAt = formatDate(p.updated_at);
  const hasUrl = p.source_url ? `<span>🔗 URL externa</span>` : "";

  return `
    <div class="playlist-card" onclick="openPlayer(${p.id})">
      <div class="playlist-card-header">
        <div style="display:flex;align-items:center;gap:10px;flex:1">
          <span class="playlist-icon">📺</span>
          <div style="flex:1;min-width:0">
            <div class="playlist-title">${escapeHtml(p.name)}</div>
            ${badge}
          </div>
        </div>
      </div>
      <div class="playlist-desc">${escapeHtml(p.description || "Sem descrição")}</div>
      <div class="playlist-meta">
        <span>📡 ${formatNumber(p.channel_count)} canais</span>
        <span>🕐 ${updatedAt}</span>
        ${hasUrl}
      </div>
      <div class="playlist-actions" onclick="event.stopPropagation()">
        <button class="btn btn-primary btn-sm" onclick="openPlayer(${p.id})">▶ Assistir</button>
        <button class="btn btn-outline btn-sm" onclick="downloadPlaylist(${p.id}, '${escapeHtml(p.name)}')">⬇ M3U</button>
        <button class="btn btn-outline btn-sm" onclick="showPlayerUrl(${p.id})">🔗 URL</button>
        ${p.source_url ? `<button class="btn btn-outline btn-sm" onclick="refreshPlaylist(${p.id})">🔄</button>` : ""}
        <button class="btn btn-outline btn-sm" onclick="editPlaylist(${p.id}, ${JSON.stringify(p).replace(/"/g, '&quot;')})">✏️</button>
        <button class="btn btn-danger btn-sm" onclick="deletePlaylist(${p.id}, '${escapeHtml(p.name)}')">🗑</button>
      </div>
    </div>
  `;
}

// ─── Abrir player ─────────────────────────────────────────────────────────────
function openPlayer(playlistId) {
  window.location.href = `/player?playlist=${playlistId}`;
}

// ─── Salvar nova playlist ─────────────────────────────────────────────────────
async function savePlaylist() {
  const btn = document.getElementById("btn-save-playlist");
  const name = document.getElementById("pl-name").value.trim();
  const desc = document.getElementById("pl-desc").value.trim();
  const url = document.getElementById("pl-url").value.trim();
  const content = document.getElementById("pl-content").value.trim();
  const isPublic = document.getElementById("pl-public").checked;

  if (!name) {
    showAlert("Nome da playlist é obrigatório", "error", "modal-alert");
    return;
  }

  if (currentTab === "url" && !url) {
    showAlert("Informe a URL da playlist ou cole o conteúdo M3U", "error", "modal-alert");
    return;
  }

  if (currentTab === "paste" && !content) {
    showAlert("Cole o conteúdo M3U no campo acima", "error", "modal-alert");
    return;
  }

  setLoading(btn, true);
  hideAlert("modal-alert");

  try {
    const body = { name, description: desc, is_public: isPublic };
    if (currentTab === "url") body.source_url = url;
    else body.content = content;

    const res = await apiRequest("/api/playlists", {
      method: "POST",
      body: JSON.stringify(body)
    });

    if (!res) return;
    const data = await res.json();

    if (res.ok) {
      closeModal("modal-add-playlist");
      showAlert(`Playlist criada com ${formatNumber(data.channel_count)} canais!`, "success");
      resetAddForm();
      loadPlaylists();
    } else {
      showAlert(data.error || "Erro ao criar playlist", "error", "modal-alert");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error", "modal-alert");
  } finally {
    setLoading(btn, false);
  }
}

function resetAddForm() {
  document.getElementById("pl-name").value = "";
  document.getElementById("pl-desc").value = "";
  document.getElementById("pl-url").value = "";
  document.getElementById("pl-content").value = "";
  document.getElementById("pl-public").checked = false;
}

// ─── Editar playlist ──────────────────────────────────────────────────────────
function editPlaylist(id, playlist) {
  document.getElementById("edit-pl-id").value = id;
  document.getElementById("edit-pl-name").value = playlist.name || "";
  document.getElementById("edit-pl-desc").value = playlist.description || "";
  document.getElementById("edit-pl-url").value = playlist.source_url || "";
  document.getElementById("edit-pl-public").checked = !!playlist.is_public;
  hideAlert("edit-alert");
  openModal("modal-edit-playlist");
}

async function updatePlaylist() {
  const btn = document.getElementById("btn-update-playlist");
  const id = document.getElementById("edit-pl-id").value;
  const name = document.getElementById("edit-pl-name").value.trim();
  const desc = document.getElementById("edit-pl-desc").value.trim();
  const url = document.getElementById("edit-pl-url").value.trim();
  const isPublic = document.getElementById("edit-pl-public").checked;

  if (!name) {
    showAlert("Nome é obrigatório", "error", "edit-alert");
    return;
  }

  setLoading(btn, true);
  hideAlert("edit-alert");

  try {
    const res = await apiRequest(`/api/playlists/${id}`, {
      method: "PUT",
      body: JSON.stringify({ name, description: desc, source_url: url, is_public: isPublic })
    });

    if (!res) return;
    const data = await res.json();

    if (res.ok) {
      closeModal("modal-edit-playlist");
      showAlert("Playlist atualizada!", "success");
      loadPlaylists();
    } else {
      showAlert(data.error || "Erro ao atualizar", "error", "edit-alert");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error", "edit-alert");
  } finally {
    setLoading(btn, false);
  }
}

// ─── Excluir playlist ─────────────────────────────────────────────────────────
async function deletePlaylist(id, name) {
  if (!confirm(`Excluir a playlist "${name}"? Esta ação não pode ser desfeita.`)) return;

  try {
    const res = await apiRequest(`/api/playlists/${id}`, { method: "DELETE" });
    if (!res) return;
    if (res.ok) {
      showAlert("Playlist excluída", "success");
      loadPlaylists();
    } else {
      const data = await res.json();
      showAlert(data.error || "Erro ao excluir", "error");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error");
  }
}

// ─── Download M3U ─────────────────────────────────────────────────────────────
function downloadPlaylist(id, name) {
  window.open(`/api/playlists/${id}/download`, "_blank");
}

// ─── Atualizar playlist ───────────────────────────────────────────────────────
async function refreshPlaylist(id) {
  showAlert("Atualizando playlist...", "info");
  try {
    const res = await apiRequest(`/api/playlists/${id}/refresh`, { method: "POST" });
    if (!res) return;
    const data = await res.json();
    if (res.ok) {
      showAlert(`Playlist atualizada com ${formatNumber(data.channel_count)} canais!`, "success");
      loadPlaylists();
    } else {
      showAlert(data.error || "Erro ao atualizar", "error");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error");
  }
}

// ─── URL para player externo ──────────────────────────────────────────────────
async function showPlayerUrl(playlistId) {
  const res = await apiRequest("/api/auth/me");
  if (!res) return;
  const user = await res.json();
  const base = window.location.origin;
  const url = `${base}/api/get.php?username=${encodeURIComponent(user.username)}&password=SUA_SENHA&playlist_id=${playlistId}`;
  document.getElementById("player-url-text").value = url;
  openModal("modal-player-url");
}

function copyPlayerUrl() {
  const input = document.getElementById("player-url-text");
  copyToClipboard(input.value);
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
