/* ─── IPTV System — JavaScript Principal ─────────────────────────────────── */

// ─── Utilitários de UI ────────────────────────────────────────────────────────
function showAlert(message, type = "error", containerId = "alert-box") {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.className = `alert ${type}`;
  el.textContent = message;
  el.classList.remove("hidden");
  if (type === "success") {
    setTimeout(() => hideAlert(containerId), 4000);
  }
}

function hideAlert(containerId = "alert-box") {
  const el = document.getElementById(containerId);
  if (el) el.classList.add("hidden");
}

function setLoading(btn, loading) {
  if (!btn) return;
  const text = btn.querySelector(".btn-text");
  const spinner = btn.querySelector(".btn-loading");
  btn.disabled = loading;
  if (text) text.classList.toggle("hidden", loading);
  if (spinner) spinner.classList.toggle("hidden", !loading);
}

function togglePassword(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.toggle("open");
}

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("hidden");
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}

// Fechar modal ao clicar fora
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.add("hidden");
  }
});

// ─── Autenticação ─────────────────────────────────────────────────────────────
async function logout() {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  } catch (e) {}
  window.location.href = "/login";
}

// ─── Formatação ───────────────────────────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr.replace(" ", "T") + "Z");
    return d.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
  } catch {
    return dateStr;
  }
}

function formatNumber(n) {
  if (n === undefined || n === null) return "—";
  return Number(n).toLocaleString("pt-BR");
}

// ─── API Helper ───────────────────────────────────────────────────────────────
async function apiRequest(url, options = {}) {
  const defaults = {
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  };
  const res = await fetch(url, { ...defaults, ...options, headers: { ...defaults.headers, ...(options.headers || {}) } });
  if (res.status === 401) {
    window.location.href = "/login";
    return null;
  }
  return res;
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("onclick")?.includes(`'${name}'`));
  });
  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.toggle("hidden", !el.id.includes(name));
  });
}

// ─── Copiar para clipboard ────────────────────────────────────────────────────
function copyToClipboard(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Copiado!");
    });
  } else {
    const el = document.createElement("textarea");
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
    showToast("Copiado!");
  }
}

function showToast(message) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.style.cssText = `
      position: fixed; bottom: 24px; right: 24px;
      background: #4caf50; color: #fff;
      padding: 10px 20px; border-radius: 8px;
      font-size: 14px; z-index: 9999;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transition: opacity 0.3s;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = "1";
  setTimeout(() => { toast.style.opacity = "0"; }, 2000);
}
