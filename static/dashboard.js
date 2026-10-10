import { api, requireAuth, renderNavbar, getToken, API_BASE } from "./common.js";

const $ = id => document.getElementById(id);

const me = await requireAuth();
renderNavbar(me, "/static/dashboard.html");

$("username").textContent = me.username;
$("userId").textContent   = me.id;
$("memberSince").textContent = me.created_at
  ? new Date(me.created_at).toLocaleDateString()
  : "—";

const roleBadge = $("roleBadge");
roleBadge.textContent = me.role;
roleBadge.className = `role-badge ${me.role}`;

async function loadQr() {
  const res = await fetch(`${API_BASE}/qrcode/${me.id}`, {
    headers: { "Authorization": `Bearer ${getToken()}` },
  });
  if (!res.ok) return;
  const blob = await res.blob();
  $("qrImg").src = URL.createObjectURL(blob);
}
loadQr();

$("downloadPdfBtn").addEventListener("click", () => {
  const card = document.querySelector(".profile");

  const clone = card.cloneNode(true);
  clone.style.background = "#ffffff";
  clone.style.color = "#0f1729";
  clone.style.padding = "24px";
  clone.style.borderRadius = "12px";
  clone.querySelectorAll(".meta div").forEach(d => {
    d.style.background = "#f1f5fb";
    d.style.color = "#0f1729";
    d.style.border = "1px solid #dbe4f0";
  });
  clone.querySelectorAll(".meta strong").forEach(s => { s.style.color = "#0f1729"; });
  clone.querySelector(".qr-panel").style.background = "#f1f5fb";
  clone.querySelector(".qr-panel").style.border = "1px solid #dbe4f0";
  clone.querySelector("#downloadPdfBtn")?.remove();

  const wrap = document.createElement("div");
  wrap.style.width = "700px";
  wrap.style.padding = "24px";
  wrap.style.background = "#ffffff";
  wrap.appendChild(clone);

  html2pdf().set({
    margin: 10,
    filename: `attendance-${me.username}.pdf`,
    image: { type: "jpeg", quality: 0.95 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
  }).from(wrap).save();
});