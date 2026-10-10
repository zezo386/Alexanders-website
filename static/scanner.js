import { api, requireAuth, renderNavbar } from "./common.js";

const $ = id => document.getElementById(id);

const me = await requireAuth("admin");     // scanner is admin-only
renderNavbar(me, "/static/scanner.html");

const eventSelect = $("eventSelect");
const scanBtn     = $("scanBtn");
const readerDiv   = $("reader");
const statusDiv   = $("status");
const historyDiv  = $("history");

let html5QrCode = null;
let scanning    = false;

// ---------- status ----------
function showStatus(text, kind = "ok") {
  statusDiv.textContent = text;
  statusDiv.className = `msg show ${kind}`;
  // auto-hide after 4s so it doesn't linger between scans
  clearTimeout(showStatus._t);
  showStatus._t = setTimeout(() => {
    statusDiv.className = "msg";
  }, 4000);
}

// ---------- load events ----------
async function loadEvents() {
  try {
    const events = await api("/events", { auth: false });
    eventSelect.innerHTML = "";

    if (!events.length) {
      const opt = document.createElement("option");
      opt.textContent = "No events — create one in Admin";
      opt.value = "";
      eventSelect.appendChild(opt);
      return;
    }

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "— Select an event —";
    eventSelect.appendChild(placeholder);

    for (const ev of events) {
      const opt = document.createElement("option");
      opt.value = ev.id;
      opt.textContent = `${ev.name} (#${ev.id})`;
      eventSelect.appendChild(opt);
    }
  } catch (e) {
    eventSelect.innerHTML = `<option value="">Failed to load events</option>`;
    showStatus(`Could not load events: ${e.message}`, "err");
  }
}

eventSelect.addEventListener("change", () => {
  scanBtn.disabled = !eventSelect.value;
});

// ---------- submit attendance ----------
async function submitAttendance(userId) {
  const eventId = parseInt(eventSelect.value, 10);
  if (!eventId) return;

  try {
    const data = await api("/attend", {
      method: "POST",
      body: { user_id: userId, event_id: eventId },
    });

    showStatus(`✅ Recorded: ${userId}`, "ok");
    addHistory(userId, "ok");
    if (navigator.vibrate) navigator.vibrate(120);
  } catch (e) {
    if (e.status === 404) {
      showStatus(`❌ Unknown user: ${userId}`, "err");
      addHistory(userId, "err", "Not a registered user");
    } else {
      showStatus(`❌ ${e.message}`, "err");
      addHistory(userId, "err", e.message);
    }
  }
}

// ---------- history ----------
function addHistory(userId, kind, note = "") {
  const row = document.createElement("div");
  const icon = kind === "ok" ? "✅" : "❌";
  row.innerHTML = `
    <span>
      <span class="icon">${icon}</span>
      <code>${userId}</code>
      ${note ? `<span style="margin-left:.5rem;color:var(--err);">— ${note}</span>` : ""}
    </span>
    <span style="font-size:.75rem;">${new Date().toLocaleTimeString()}</span>
  `;
  historyDiv.prepend(row);
  // cap the history so it doesn't grow forever
  while (historyDiv.children.length > 50) {
    historyDiv.lastChild.remove();
  }
}

// ---------- scan control ----------
async function startScanning() {
  if (scanning) return;

  html5QrCode = new Html5Qrcode("reader");
  readerDiv.classList.add("active");
  scanBtn.textContent = "Stop scanning";
  scanning = true;

  try {
    await html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 240, height: 240 } },
      async (decodedText) => {
        // Pause so we don't fire the same QR 10× per second
        await html5QrCode.pause(true);
        await submitAttendance(decodedText.trim());
        // Resume after a short cooldown for the next person
        setTimeout(() => {
          if (scanning) html5QrCode.resume();
        }, 1200);
      },
      () => { /* per-frame decode misses — ignore */ }
    );
  } catch (e) {
    showStatus(`Could not start camera: ${e.message}`, "err");
    readerDiv.classList.remove("active");
    scanBtn.textContent = "Start scanning";
    scanning = false;
  }
}

async function stopScanning() {
  if (!html5QrCode) return;
  scanning = false;
  try {
    await html5QrCode.stop();
    html5QrCode.clear();
  } catch (_) {}
  readerDiv.classList.remove("active");
  scanBtn.textContent = "Start scanning";
  html5QrCode = null;
}

scanBtn.addEventListener("click", () => {
  scanning ? stopScanning() : startScanning();
});

// ---------- init ----------
loadEvents();