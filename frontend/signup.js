import { api } from "./common.js";

const $ = id => document.getElementById(id);
const msg = $("msg");

function showMsg(text, kind = "err") {
  msg.textContent = text;
  msg.className = `msg show ${kind}`;
}

async function signup() {
  const username = $("username").value.trim();
  const password = $("password").value;
  const password2 = $("password2").value;

  if (!username || !password) return showMsg("Fill in all fields.");
  if (password.length < 4)     return showMsg("Password must be at least 4 characters.");
  if (password !== password2)  return showMsg("Passwords don't match.");

  $("signupBtn").disabled = true;
  try {
    await api("/signup", {
      method: "POST",
      auth: false,
      body: { username, password },
    });
    $("formCard").style.display = "none";
    $("doneCard").style.display = "block";
  } catch (e) {
    showMsg(e.status === 409 ? "That username is already taken." : e.message);
  } finally {
    $("signupBtn").disabled = false;
  }
}

$("signupBtn").addEventListener("click", signup);