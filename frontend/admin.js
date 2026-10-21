import { api, requireAuth, renderNavbar, getToken } from "./common.js";

const $ = id => document.getElementById(id);
const msg = $("msg");

function showMsg(text, kind = "ok") {
  msg.textContent = text;
  msg.className = `msg show ${kind}`;
  setTimeout(() => { msg.className = "msg"; }, 4000);
}

const me = await requireAuth("admin");
renderNavbar(me, "/static/admin.html");

async function loadPending() {
  const tbody = $("pendingBody");
  tbody.innerHTML = `<tr><td colspan="4" class="empty">Loading…</td></tr>`;
  try {
    const rows = await api("/admin/pending");
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="empty">No pending sign-ups.</td></tr>`;
      return;
    }
    tbody.innerHTML = "";
    for (const p of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${p.full_name}</td>
        <td>${new Date(p.requested_at).toLocaleString()}</td>
        <td>${p.interview_at ? new Date(p.interview_at).toLocaleString() : "—"}</td>
        <td>
          <div class="row-actions">
            <input type="datetime-local" id="dt-${p.id}" style="margin:0;font-size:.75rem;padding:.35rem;" />
            <button class="ghost" data-action="schedule" data-id="${p.id}">Schedule</button>
            <button class="ok"    data-action="approve"  data-id="${p.id}">Approve</button>
            <button class="ok"    data-action="approve-admin" data-id="${p.id}">Approve as Admin</button>
            <button class="danger" data-action="reject"  data-id="${p.id}">Reject</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    }
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty">Error: ${e.message}</td></tr>`;
  }
}

$("pendingBody").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const action = btn.dataset.action;
  const id = btn.dataset.id;
  try {
    if (action === "schedule") {
      const dt = document.getElementById(`dt-${id}`).value;
      if (!dt) return showMsg("Pick a date/time first.", "warn");
      await api(`/admin/pending/${id}/schedule`, {
        method: "POST",
        body: { interview_at: new Date(dt).toISOString() },
      });
      showMsg("Interview scheduled.");
    } else if (action === "approve") {
      await api(`/admin/pending/${id}/approve?admin_approve=0`, { method: "POST" });
      showMsg("User approved.");
    } else if (action === "approve-admin") {
      await api(`/admin/pending/${id}/approve?admin_approve=1`, { method: "POST" });
      showMsg("User approved as admin.");
    } else if (action === "reject") {
      if (!confirm("Reject this request?")) return;
      await api(`/admin/pending/${id}/reject`, { method: "POST" });
      showMsg("Request rejected.");
    }
    await Promise.all([loadPending(), loadUsers()]);
  } catch (e) {
    showMsg(e.message, "err");
  }
});

async function loadUsers() {
  const tbody = $("usersBody");
  tbody.innerHTML = `<tr><td colspan="2" class="empty">Loading…</td></tr>`;
  try {
    const rows = await api("/users");
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="2" class="empty">No users yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(u => `
      <tr><td>${u.full_name}</td><td><span class="pill">${u.role}</span></td></tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="2" class="empty">Error: ${e.message}</td></tr>`;
  }
}

async function loadEvents() {
  const tbody = $("eventsBody");
  tbody.innerHTML = `<tr><td colspan="2" class="empty">Loading…</td></tr>`;
  try {
    const rows = await api("/events", { auth: false });
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="2" class="empty">No events yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(ev => `<tr><td>#${ev.id}</td><td>${ev.name}</td></tr>`).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="2" class="empty">Error: ${e.message}</td></tr>`;
  }
}

$("createEventBtn").addEventListener("click", async () => {
  const name = $("eventName").value.trim();
  if (!name) return showMsg("Event name required.", "warn");
  try {
    await api("/events", { method: "POST", body: { name } });
    $("eventName").value = "";
    showMsg("Event created.");
    loadEvents();
  } catch (e) {
    showMsg(e.message, "err");
  }
});

$("exportAttendanceBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/export_attendance", {
      headers: { "Authorization": `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "attendance.csv";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    showMsg(e.message, "err");
  }
});

$("exportUsersBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/export_users", {
      headers: { "Authorization": `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "users.csv";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    showMsg(e.message, "err");
  }
});

loadPending();
loadUsers();
loadEvents();