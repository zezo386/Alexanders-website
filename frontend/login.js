import { api, setToken, getToken } from "./common.js";

const $ = id => document.getElementById(id);
const msg = $("msg");

function showMsg(text, kind = "err") {
  msg.textContent = text;
  msg.className = `msg show ${kind}`;
}

if (getToken()) location.replace("/static/dashboard.html");

async function login() {
  const username = $("username").value.trim();
  const password = $("password").value;

  if (!username || !password) {
    return showMsg("Enter username and password.");
  }

  $("loginBtn").disabled = true;
  try {
    const data = await api("/login", {
      method: "POST",
      auth: false,
      body: { username, password },
    });
    setToken(data.access_token);
    location.replace("/static/dashboard.html");
  } catch (e) {
    if (e.status === 401) showMsg("Invalid username or password.");
    else showMsg(e.message || "Login failed.");
  } finally {
    $("loginBtn").disabled = false;
  }
}

$("loginBtn").addEventListener("click", login);
$("password").addEventListener("keydown", e => { if (e.key === "Enter") login(); });