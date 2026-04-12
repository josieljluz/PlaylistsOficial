/* ─── Admin Panel — Gerenciamento de Usuários e Logs ─────────────────────── */

let logsPage = 1;

document.addEventListener("DOMContentLoaded", () => {
  loadAdminStats();
  loadUsers();
});

// ─── Estatísticas ─────────────────────────────────────────────────────────────
async function loadAdminStats() {
  try {
    const res = await apiRequest("/api/admin/stats");
    if (!res || !res.ok) return;
    const s = await res.json();
    document.getElementById("s-users").textContent = formatNumber(s.users);
    document.getElementById("s-active").textContent = formatNumber(s.active_users);
    document.getElementById("s-playlists").textContent = formatNumber(s.playlists);
    document.getElementById("s-channels").textContent = formatNumber(s.channels);
    document.getElementById("s-logs").textContent = formatNumber(s.logs_today);
  } catch (err) {
    console.error("Erro ao carregar stats:", err);
  }
}

// ─── Tabs Admin ───────────────────────────────────────────────────────────────
function showAdminTab(tab) {
  document.querySelectorAll(".admin-tabs .tab-btn").forEach((btn, i) => {
    const tabs = ["users", "logs"];
    btn.classList.toggle("active", tabs[i] === tab);
  });
  document.getElementById("admin-tab-users").classList.toggle("hidden", tab !== "users");
  document.getElementById("admin-tab-logs").classList.toggle("hidden", tab !== "logs");

  if (tab === "logs") loadLogs(1);
}

// ─── Usuários ─────────────────────────────────────────────────────────────────
async function loadUsers() {
  const tbody = document.getElementById("users-tbody");
  tbody.innerHTML = '<tr><td colspan="8" class="text-center">Carregando...</td></tr>';

  try {
    const res = await apiRequest("/api/admin/users");
    if (!res || !res.ok) return;
    const users = await res.json();

    if (users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Nenhum usuário</td></tr>';
      return;
    }

    tbody.innerHTML = users.map(u => `
      <tr>
        <td>${u.id}</td>
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td>${escapeHtml(u.email || "—")}</td>
        <td>${u.playlist_count || 0}</td>
        <td>${u.is_admin ? '<span class="badge badge-public">Admin</span>' : '—'}</td>
        <td>${u.is_active
          ? '<span class="badge badge-public">Ativo</span>'
          : '<span class="badge" style="background:rgba(244,67,54,0.2);color:#f44336">Inativo</span>'
        }</td>
        <td>${formatDate(u.last_login)}</td>
        <td>
          <div class="flex gap-2">
            <button class="btn btn-outline btn-sm" onclick="openEditUser(${JSON.stringify(u).replace(/"/g, '&quot;')})">✏️</button>
            <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id}, '${escapeHtml(u.username)}')">🗑</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Erro ao carregar</td></tr>';
  }
}

// ─── Criar usuário ────────────────────────────────────────────────────────────
async function createUser() {
  const username = document.getElementById("new-username").value.trim();
  const email = document.getElementById("new-email").value.trim();
  const password = document.getElementById("new-password").value;
  const isAdmin = document.getElementById("new-is-admin").checked;

  if (!username || !password) {
    showAlert("Usuário e senha são obrigatórios", "error", "add-user-alert");
    return;
  }

  try {
    const res = await apiRequest("/api/admin/users", {
      method: "POST",
      body: JSON.stringify({ username, email, password, is_admin: isAdmin })
    });
    if (!res) return;
    const data = await res.json();
    if (res.ok) {
      closeModal("modal-add-user");
      showAlert("Usuário criado com sucesso!", "success");
      loadUsers();
      loadAdminStats();
      // Limpar form
      ["new-username", "new-email", "new-password"].forEach(id => {
        document.getElementById(id).value = "";
      });
      document.getElementById("new-is-admin").checked = false;
    } else {
      showAlert(data.error || "Erro ao criar usuário", "error", "add-user-alert");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error", "add-user-alert");
  }
}

// ─── Editar usuário ───────────────────────────────────────────────────────────
function openEditUser(user) {
  document.getElementById("edit-user-id").value = user.id;
  document.getElementById("edit-user-email").value = user.email || "";
  document.getElementById("edit-user-password").value = "";
  document.getElementById("edit-user-admin").checked = !!user.is_admin;
  document.getElementById("edit-user-active").checked = !!user.is_active;
  hideAlert("edit-user-alert");
  openModal("modal-edit-user");
}

async function updateUser() {
  const id = document.getElementById("edit-user-id").value;
  const email = document.getElementById("edit-user-email").value.trim();
  const password = document.getElementById("edit-user-password").value;
  const isAdmin = document.getElementById("edit-user-admin").checked;
  const isActive = document.getElementById("edit-user-active").checked;

  const body = { email, is_admin: isAdmin, is_active: isActive };
  if (password) body.password = password;

  try {
    const res = await apiRequest(`/api/admin/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(body)
    });
    if (!res) return;
    const data = await res.json();
    if (res.ok) {
      closeModal("modal-edit-user");
      showAlert("Usuário atualizado!", "success");
      loadUsers();
    } else {
      showAlert(data.error || "Erro ao atualizar", "error", "edit-user-alert");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error", "edit-user-alert");
  }
}

// ─── Excluir usuário ──────────────────────────────────────────────────────────
async function deleteUser(id, username) {
  if (!confirm(`Excluir o usuário "${username}" e todas as suas playlists?`)) return;

  try {
    const res = await apiRequest(`/api/admin/users/${id}`, { method: "DELETE" });
    if (!res) return;
    const data = await res.json();
    if (res.ok) {
      showAlert("Usuário excluído", "success");
      loadUsers();
      loadAdminStats();
    } else {
      showAlert(data.error || "Erro ao excluir", "error");
    }
  } catch (err) {
    showAlert("Erro de conexão", "error");
  }
}

// ─── Logs de acesso ───────────────────────────────────────────────────────────
async function loadLogs(page = 1) {
  logsPage = page;
  const tbody = document.getElementById("logs-tbody");
  tbody.innerHTML = '<tr><td colspan="4" class="text-center">Carregando...</td></tr>';

  try {
    const res = await apiRequest(`/api/admin/logs?page=${page}&per_page=50`);
    if (!res || !res.ok) return;
    const data = await res.json();

    if (data.logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhum log</td></tr>';
      return;
    }

    tbody.innerHTML = data.logs.map(l => `
      <tr>
        <td>${formatDate(l.created_at)}</td>
        <td>${escapeHtml(l.username || "—")}</td>
        <td><code>${escapeHtml(l.action)}</code></td>
        <td>${escapeHtml(l.ip_address || "—")}</td>
      </tr>
    `).join("");

    // Paginação
    const totalPages = Math.ceil(data.total / 50);
    renderLogsPagination(page, totalPages);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Erro ao carregar</td></tr>';
  }
}

function renderLogsPagination(page, totalPages) {
  const pag = document.getElementById("logs-pagination");
  if (totalPages <= 1) { pag.innerHTML = ""; return; }

  let html = "";
  if (page > 1) html += `<button class="page-btn" onclick="loadLogs(${page - 1})">‹ Anterior</button>`;
  html += `<span style="color:var(--text-muted);padding:0 8px">Página ${page} de ${totalPages}</span>`;
  if (page < totalPages) html += `<button class="page-btn" onclick="loadLogs(${page + 1})">Próxima ›</button>`;
  pag.innerHTML = html;
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
