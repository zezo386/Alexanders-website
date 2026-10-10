export const API_BASE = "";

const TOKEN_KEY = "attendance.token";

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}
export function setToken(t) {
  sessionStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(extra = {}) {
  const t = getToken();
  return t ? { ...extra, "Authorization": `Bearer ${t}` } : extra;
}

export async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) Object.assign(headers, authHeaders());

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try { data = await res.json(); } catch (_) {}

  if (!res.ok) {
    const err = new Error((data && data.detail) || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export async function requireAuth(role = null) {
  const token = getToken();
  if (!token) {
    location.replace("/static/index.html");
    throw new Error("no token");
  }
  try {
    const me = await api("/me");
    if (role && me.role !== role) {
      location.replace("/static/dashboard.html");
      throw new Error("wrong role");
    }
    return me;
  } catch (e) {
    clearToken();
    location.replace("/static/index.html");
    throw e;
  }
}

export function renderNavbar(me, activePath) {
  const el = document.getElementById("navbar");
  if (!el) return;

  const isAdmin = me.role === "admin";
  const links = [
    { href: "/static/dashboard.html", label: "Dashboard" },
    ...(isAdmin ? [
      { href: "/static/scanner.html", label: "Scanner" },
      { href: "/static/admin.html",   label: "Admin" }
    ] : []),
  ];

  el.innerHTML = `
    <div class="navbar">
      <div class="brand">Attendance</div>
      <nav>
        ${links.map(l => `
          <a href="${l.href}" class="${l.href === activePath ? "active" : ""}">${l.label}</a>
        `).join("")}
      </nav>
      <div class="right">
        <span>${me.username}</span>
        <span class="pill">${me.role}</span>
        <button class="ghost" id="logoutBtn" style="width:auto;padding:.35rem .7rem;font-size:.8rem;">Log out</button>
      </div>
    </div>
  `;

  document.getElementById("logoutBtn").addEventListener("click", () => {
    clearToken();
    location.replace("/static/index.html");
  });
}