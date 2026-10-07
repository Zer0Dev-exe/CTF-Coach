const $ = (id) => document.getElementById(id);

let me = null; // { user, score } o null
let challenges = [];
let current = null; // reto abierto
let roomsData = null; // { paths, badges }
let roomsStale = false;
let currentRoom = null;
let activeTaskId = null; // tarea en la que está trabajando el alumno (contexto del Coach)
let busy = false;
let roomBusy = false;
let authMode = "login";
let afterAuth = null; // acción pendiente tras iniciar sesión
let roadmapData = null;
let roadmapFilter = "all";
let lbPeriod = "all";

// ---------- Iconos SVG (trazo de línea, 24x24, heredan el color del texto) ----------

const ICONS = {
  compass: '<circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-1.8 5.41a2 2 0 0 1-1.27 1.27L7.76 16.24l1.8-5.41a2 2 0 0 1 1.27-1.27z"/>',
  network: '<rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/>',
  terminal: '<rect x="2" y="3" width="20" height="18" rx="2"/><path d="m7 9 3 3-3 3"/><path d="M13 15h4"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  binary: '<rect x="14" y="14" width="4" height="6" rx="2"/><rect x="6" y="4" width="4" height="6" rx="2"/><path d="M6 20h4"/><path d="M14 10h4"/><path d="M6 14h2v6"/><path d="M14 4h2v6"/>',
  hash: '<path d="M4 9h16"/><path d="M4 15h16"/><path d="M10 3 8 21"/><path d="M16 3l-2 18"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  code: '<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  wall: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M12 9v6"/><path d="M8 15v6"/><path d="M16 15v6"/><path d="M8 3v6"/><path d="M16 3v6"/>',
  flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
  award: '<circle cx="12" cy="8" r="6"/><path d="M15.48 12.89 17 22l-5-3-5 3 1.52-9.11"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  "arrow-left": '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  eye: '<path d="M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-19.88 0"/><circle cx="12" cy="12" r="3"/>',
  "eye-off": '<path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c4.97 0 8.4 3.6 9.94 6.65a1 1 0 0 1 0 .7 10.8 10.8 0 0 1-1.44 2.49"/><path d="M14.08 14.16a3 3 0 0 1-4.24-4.24"/><path d="M17.48 17.5A10.75 10.75 0 0 1 2.06 12.35a1 1 0 0 1 0-.7 10.8 10.8 0 0 1 4.44-5.14"/><path d="m2 2 20 20"/>',
  send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  copy: '<rect x="8" y="8" width="14" height="14" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  bars: '<path d="M3 3v18h18"/><path d="M8 17v-5"/><path d="M13 17V8"/><path d="M18 17v-9"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
};

function icon(name, cls = "icon") {
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.award}</svg>`;
}

// Sustituye los <span data-icon="..."> del HTML por su SVG.
function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    const block = el.classList.contains("icon-tile") || el.classList.contains("chev");
    el.innerHTML = icon(el.dataset.icon, block ? "icon" : "icon icon-inline");
    if (!block) el.replaceWith(...el.childNodes);
  });
}

// ---------- Avatares generados a partir del nombre ----------

function hashStr(s) {
  let h = 2166136261;
  for (const ch of s) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

const AVATAR_GRADIENTS = [
  ["#7ff0b4", "#1f9d6b"], ["#9ccaff", "#3b6fd8"], ["#f5cf7a", "#d9822b"], ["#ff9c8f", "#c2445e"],
  ["#8ae8de", "#2a8f9e"], ["#f7a8d3", "#c0569a"], ["#cdf07f", "#4fae4a"], ["#ffc9a3", "#e0664f"],
];

function initials(name) {
  const parts = name.split(/[_\-.\s]+/).filter(Boolean);
  const raw = parts.length > 1 ? parts[0][0] + parts[1][0] : name.replace(/[^A-Za-z0-9]/g, "").slice(0, 2);
  return (raw || "?").toUpperCase();
}

// Hexágono (como el logo) con un degradado propio de cada nombre y sus iniciales.
function avatar(name, cls = "av") {
  const h = hashStr(name.toLowerCase());
  const [c1, c2] = AVATAR_GRADIENTS[h % AVATAR_GRADIENTS.length];
  const id = `avg-${h.toString(36)}`;
  const dir = [["0", "0", "1", "1"], ["1", "0", "0", "1"], ["0", "1", "1", "0"], ["0.5", "0", "0.5", "1"]][(h >>> 3) % 4];
  return `<svg class="${cls}" viewBox="0 0 40 40" aria-hidden="true">
    <defs><linearGradient id="${id}" x1="${dir[0]}" y1="${dir[1]}" x2="${dir[2]}" y2="${dir[3]}">
      <stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/></linearGradient></defs>
    <path d="M20 3 35 11.5v17L20 37 5 28.5v-17z" fill="url(#${id})" stroke="url(#${id})" stroke-width="3" stroke-linejoin="round"/>
    <path d="M20 6.2 32.2 13.1v13.8L20 33.8 7.8 26.9V13.1z" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="1"/>
    <text x="20" y="20.5" text-anchor="middle" dominant-baseline="central" class="av-text">${escapeHtml(initials(name))}</text>
  </svg>`;
}

// ---------- Utilidades ----------

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const norm = (t) => t.normalize("NFD").replace(/\p{M}/gu, "").trim().toLowerCase();
const diffClass = (d) => "diff-" + norm(d);

// Markdown mínimo: bloques de código, código en línea, negrita, títulos, listas y párrafos.
function renderInline(t) {
  return t.replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*\w])\*([^*\n]+)\*(?![*\w])/g, "$1<em>$2</em>");
}

function renderMarkdown(text) {
  const blocks = [];
  const html = escapeHtml(text).replace(/```\w*\n?([\s\S]*?)```/g, (_, code) => {
    blocks.push(`<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
    return `\n\n\u0000${blocks.length - 1}\u0000\n\n`;
  });
  return html.split(/\n{2,}/).map((block) => {
    block = block.trim();
    if (!block) return "";
    const code = block.match(/^\u0000(\d+)\u0000$/);
    if (code) return blocks[code[1]];
    const lines = block.split("\n");
    if (/^#{1,4} /.test(block) && lines.length === 1) return `<h4>${renderInline(block.replace(/^#+ /, ""))}</h4>`;
    if (lines.every((l) => /^[-*] /.test(l))) return `<ul>${lines.map((l) => `<li>${renderInline(l.slice(2))}</li>`).join("")}</ul>`;
    if (lines.every((l) => /^\d+\. /.test(l))) return `<ol>${lines.map((l) => `<li>${renderInline(l.replace(/^\d+\. /, ""))}</li>`).join("")}</ol>`;
    return `<p>${renderInline(block).replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

async function api(path, options = {}) {
  const r = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const auth = path.startsWith("/api/login") || path.startsWith("/api/register");
    if (r.status === 401 && !auth) openAuth("login");
    const err = new Error(Array.isArray(data.detail) ? "Revisa los datos del formulario." : data.detail || `Error ${r.status}`);
    err.status = r.status;
    throw err;
  }
  return data;
}

function storageGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
function storageSet(key, v) { try { localStorage.setItem(key, v); } catch {} }

function progressBar(done, total) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  return `<div class="progress" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar" style="width:${pct}%"></div></div>`;
}

function showToast(html) {
  const t = $("toast");
  t.innerHTML = html;
  t.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => (t.hidden = true), 4500);
}

function level() {
  return storageGet("ctf-coach-level") || "principiante";
}

// ---------- Navegación (por hash, para que funcione el botón atrás) ----------

const VIEWS = ["landing", "roadmap", "rooms", "room", "play", "challenge", "leaderboard"];
const VIEW_HASH = { landing: "#inicio", roadmap: "#roadmap", rooms: "#salas", play: "#retos", leaderboard: "#clasificacion" };
const NAV_OF = { room: "rooms", challenge: "play" };

function navigate(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

function showView(view) {
  const changed = $(`view-${view}`).hidden;
  for (const v of VIEWS) $(`view-${v}`).hidden = v !== view;
  const nav = NAV_OF[view] || view;
  document.querySelectorAll(".nav-link").forEach((a) => {
    a.classList.toggle("active", a.dataset.view === nav);
    if (a.dataset.view === nav) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  if (changed) window.scrollTo(0, 0);
  updateNavIndicator();
}

function updateNavIndicator() {
  const ind = document.querySelector(".nav-indicator");
  const a = document.querySelector(".nav-link.active");
  if (!ind) return;
  ind.style.opacity = a ? "1" : "0";
  if (!a) return;
  ind.style.width = `${a.offsetWidth - 24}px`;
  ind.style.transform = `translateX(${a.offsetLeft + 12}px)`;
}

async function route() {
  const h = location.hash;
  const m = h.match(/^#(sala|reto)\/([\w-]+)$/);
  if (m?.[1] === "sala") return openRoom(m[2]).catch(() => navigate("#salas"));
  if (m?.[1] === "reto") return openChallenge(m[2]);
  if (h === "#salas") { showView("rooms"); if (roomsStale || !roomsData) await loadRooms(); return; }
  if (h === "#retos") { renderChallenges(); return showView("play"); }
  if (h === "#clasificacion") { showView("leaderboard"); return loadLeaderboard(); }
  if (h === "#roadmap") { showView("roadmap"); return loadRoadmap(); }
  if (h === "#inicio" || !me) { renderLanding(); return showView("landing"); }
  history.replaceState(null, "", "#salas");
  showView("rooms");
  if (roomsStale || !roomsData) await loadRooms();
}

// ---------- Cuenta ----------

let shownScore = null;

// Anima un número de su valor anterior al nuevo.
function countUp(el, to, ms = 700) {
  const from = Number(el.dataset.value ?? to);
  el.dataset.value = to;
  if (from === to || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = to; return; }
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / ms);
    el.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3)));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function closeUserMenu() {
  const pop = $("user-pop");
  if (!pop || pop.hidden) return;
  pop.hidden = true;
  $("user-btn").setAttribute("aria-expanded", "false");
}

async function refreshMe() {
  const data = await api("/api/me");
  me = data.user ? data : null;
  const box = $("user-box");
  if (me) {
    const name = escapeHtml(me.user);
    const rankText = me.rank ? `#${me.rank} de ${me.players}` : "Sin clasificar";
    box.innerHTML = `
      <div class="user-menu">
        <button id="user-btn" class="user-chip" aria-haspopup="menu" aria-expanded="false" aria-controls="user-pop">
          ${avatar(me.user, "av av-sm")}
          <span class="user-name">${name}</span>
          <span class="user-score" title="Puntos totales"><b id="score-num" data-value="${shownScore ?? me.score}">${shownScore ?? me.score}</b> pts</span>
          ${me.rank ? `<span class="user-rank" title="Tu posición">#${me.rank}</span>` : ""}
          ${icon("chevron-down", "icon icon-inline user-chev")}
        </button>
        <div id="user-pop" class="user-pop" role="menu" hidden>
          <div class="user-pop-head">${avatar(me.user, "av av-lg")}
            <div><strong>${name}</strong><span>${rankText} · ${me.score} pts</span></div></div>
          <button role="menuitem" data-goto="#clasificacion" data-hl="#lb-me">${icon("bars", "icon icon-inline")}Mi clasificación</button>
          <button role="menuitem" data-goto="#salas" data-hl=".badges-box">${icon("award", "icon icon-inline")}Mis insignias</button>
          <button role="menuitem" data-goto="#roadmap">${icon("compass", "icon icon-inline")}Mi roadmap</button>
          <div class="user-pop-sep" role="separator"></div>
          <button role="menuitem" id="logout" class="danger">${icon("logout", "icon icon-inline")}Cerrar sesión</button>
        </div>
      </div>`;
    countUp($("score-num"), me.score);
    shownScore = me.score;
    $("user-btn").onclick = (e) => {
      e.stopPropagation();
      const pop = $("user-pop");
      pop.hidden = !pop.hidden;
      $("user-btn").setAttribute("aria-expanded", String(!pop.hidden));
      if (!pop.hidden) pop.querySelector("[role=menuitem]").focus();
    };
    $("user-pop").querySelectorAll("[data-goto]").forEach((b) => (b.onclick = () => {
      closeUserMenu();
      navigate(b.dataset.goto);
      if (b.dataset.hl) spotlight(b.dataset.hl);
    }));
    $("logout").onclick = async () => {
      closeUserMenu();
      await api("/api/logout", { method: "POST" });
      shownScore = null;
      history.replaceState(null, "", location.pathname);
      await reloadAll();
    };
  } else {
    shownScore = null;
    box.innerHTML = `
      <button id="login-btn" class="btn btn-ghost btn-sm">Iniciar sesión</button>
      <button id="register-btn" class="btn btn-primary btn-sm">Crear cuenta</button>`;
    $("login-btn").onclick = () => openAuth("login");
    $("register-btn").onclick = () => openAuth("register");
  }
}

const AUTH_TEXT = {
  login: {
    title: "Bienvenido de nuevo", sub: "Entra para seguir donde lo dejaste.", submit: "Entrar",
    foot: "¿Aún no tienes cuenta?", switchTo: "Crear una",
  },
  register: {
    title: "Crea tu cuenta", sub: "Guarda tu progreso, gana insignias y aparece en la clasificación.", submit: "Crear cuenta",
    foot: "¿Ya tienes cuenta?", switchTo: "Inicia sesión",
  },
};
const USER_RE = /^[A-Za-z0-9_]{3,20}$/;
const STRENGTH = ["", "Débil", "Aceptable", "Buena", "Fuerte"];

function setFieldError(field, msg) {
  const el = $(`${field}-error`);
  el.textContent = msg || "";
  el.hidden = !msg;
  $(`f-${field}`).classList.toggle("has-error", !!msg);
  $(field === "user" ? "auth-user" : "auth-pass").setAttribute("aria-invalid", msg ? "true" : "false");
}

function clearAuthErrors() {
  setFieldError("user", "");
  setFieldError("pass", "");
  $("auth-error").textContent = "";
}

function passwordStrength(p) {
  if (!p) return 0;
  let s = p.length >= 8 ? 1 : 0;
  if (p.length >= 12) s++;
  if (/[A-Za-z]/.test(p) && /\d/.test(p)) s++;
  if (/[^A-Za-z0-9]/.test(p) || (/[a-z]/.test(p) && /[A-Z]/.test(p))) s++;
  return Math.max(1, Math.min(4, s));
}

function updateStrength() {
  if (authMode !== "register") return;
  const p = $("auth-pass").value;
  const s = passwordStrength(p);
  $("strength").dataset.level = s;
  $("pass-hint").textContent = p
    ? `Seguridad: ${STRENGTH[s]}${p.length < 8 ? ` · faltan ${8 - p.length} caracteres` : ""}`
    : "Mínimo 8 caracteres. Mejor si mezclas letras, números y símbolos.";
}

function setAuthMode(mode) {
  authMode = mode;
  const t = AUTH_TEXT[mode];
  $("auth-title").textContent = t.title;
  $("auth-sub").textContent = t.sub;
  $("auth-submit").textContent = t.submit;
  $("auth-foot-text").textContent = t.foot;
  $("auth-switch").textContent = t.switchTo;
  for (const m of ["login", "register"]) $(`tab-${m}`).setAttribute("aria-selected", m === mode ? "true" : "false");
  const reg = mode === "register";
  $("auth-pass").autocomplete = reg ? "new-password" : "current-password";
  $("user-hint").hidden = !reg;
  $("strength").hidden = !reg;
  $("pass-hint").hidden = !reg;
  clearAuthErrors();
  updateStrength();
}

function openAuth(mode, next = null) {
  afterAuth = next;
  $("auth-pass").type = "password";
  $("pass-toggle").setAttribute("aria-pressed", "false");
  $("pass-toggle").setAttribute("aria-label", "Mostrar contraseña");
  $("pass-toggle").innerHTML = icon("eye", "icon icon-inline");
  setAuthMode(mode);
  $("auth-modal").hidden = false;
  document.body.style.overflow = "hidden";
  $("auth-user").focus();
}

function closeAuth() {
  $("auth-modal").hidden = true;
  document.body.style.overflow = "";
  afterAuth = null;
}

function validateAuth() {
  const user = $("auth-user").value.trim();
  const pass = $("auth-pass").value;
  let ok = true;
  if (!user) { setFieldError("user", "Escribe tu nombre de usuario."); ok = false; }
  else if (authMode === "register" && !USER_RE.test(user)) {
    setFieldError("user", "Usa entre 3 y 20 caracteres: letras sin tildes, números o _."); ok = false;
  } else setFieldError("user", "");
  if (!pass) { setFieldError("pass", "Escribe tu contraseña."); ok = false; }
  else if (authMode === "register" && pass.length < 8) { setFieldError("pass", "Debe tener al menos 8 caracteres."); ok = false; }
  else setFieldError("pass", "");
  return ok;
}

async function submitAuth(e) {
  e.preventDefault();
  $("auth-error").textContent = "";
  if (!validateAuth()) {
    (document.querySelector(".field.has-error input") || $("auth-user")).focus();
    return;
  }
  const btn = $("auth-submit");
  btn.classList.add("is-loading");
  btn.disabled = true;
  try {
    const username = $("auth-user").value.trim();
    // El servidor exige 8 caracteres también al entrar: una contraseña más corta nunca puede ser correcta.
    if (authMode === "login" && $("auth-pass").value.length < 8) throw Object.assign(new Error(), { status: 401 });
    await api(`/api/${authMode}`, { method: "POST", body: JSON.stringify({ username, password: $("auth-pass").value }) });
    const next = afterAuth;
    const registered = authMode === "register";
    closeAuth();
    $("auth-form").reset();
    await reloadAll();
    showToast(registered ? `Cuenta creada. Bienvenido, <b>${escapeHtml(username)}</b>.` : `Hola de nuevo, <b>${escapeHtml(username)}</b>.`);
    if (next) next();
    else if ($("view-landing").hidden === false) navigate("#salas");
  } catch (err) {
    if (err.status === 409) { setFieldError("user", "Ese nombre ya está en uso. Prueba con otro."); $("auth-user").focus(); }
    else if (err.status === 401 || (authMode === "login" && err.status === 422)) $("auth-error").textContent = "Usuario o contraseña incorrectos.";
    else $("auth-error").textContent = err.message || "No se ha podido conectar. Inténtalo de nuevo.";
  } finally {
    btn.classList.remove("is-loading");
    btn.disabled = false;
  }
}

function togglePassword() {
  const input = $("auth-pass");
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  const b = $("pass-toggle");
  b.setAttribute("aria-pressed", String(show));
  b.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
  b.innerHTML = icon(show ? "eye-off" : "eye", "icon icon-inline");
  input.focus();
}

// Mantiene el foco dentro del diálogo y permite cerrarlo con Escape.
function authKeydown(e) {
  if ($("auth-modal").hidden) return;
  if (e.key === "Escape") { e.stopImmediatePropagation(); return closeAuth(); } // no cierra también el chat de Bit
  if (e.key !== "Tab") return;
  const items = [...$("auth-form").querySelectorAll("button, input")].filter((el) => !el.disabled && el.offsetParent);
  const first = items[0], last = items[items.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

// ---------- Landing ----------

const BIT_LOGO = `<svg class="logo coach-logo" aria-hidden="true"><use href="#logo"/></svg>`;
const TICKER_ITEMS = ["Redes", "Linux", "Base64", "XOR", "Hashes", "JWT", "DNS", "Phishing", "OWASP Top 10", "Logs",
  "Permisos", "Criptografía", "Forense", "SIEM", "Cloud", "Python", "Directorio Activo", "Análisis de malware"];
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---------- Demo animada del hero ----------
// Cada escena es una pequeña secuencia (escribir, mostrar, comprobar...). Si se cambia de escena a mitad,
// la secuencia anterior se cancela; si el ratón está encima, se pausa.

const coachBubble = `<div class="preview-coach pv-step" data-k="coach">${BIT_LOGO}<p><b>Coach</b> · <span data-k="say"></span></p></div>`;

const HERO_SCENES = [
  {
    tab: ["terminal", "Sala"], crumb: "salas / linux / permisos",
    html: `<p class="preview-task"><span class="pv-prompt">$</span> <span class="pv-cmd" data-k="cmd"></span><span class="pv-caret" data-k="caret"></span></p>
      <pre class="pv-step" data-k="out">-rwx<span class="hl">r-x</span>--- 1 ana devops 812 deploy.sh</pre>
      <div class="pv-break pv-step" data-k="break">
        <span class="pv-chip"><b>-</b><small>tipo</small></span><span class="pv-chip"><b>rwx</b><small>propietario</small></span>
        <span class="pv-chip hot"><b>r-x</b><small>grupo</small></span><span class="pv-chip"><b>---</b><small>otros</small></span>
      </div>
      <div class="preview-q pv-step" data-k="q"><p>¿Puede el grupo <code>devops</code> ejecutar el script?</p>
        <div class="preview-answer"><span class="fake-input" data-k="ans"></span>
          <span class="btn btn-primary btn-sm pv-check" data-k="btn">Comprobar</span><span class="pv-plus" data-k="plus">+10 pts</span></div></div>
      ${coachBubble}`,
    async play(c) {
      await c.wait(250);
      await c.type("cmd", "ls -l deploy.sh");
      await c.wait(200);
      c.el("caret").classList.add("off");
      await c.show("out", 450);
      await c.show("break", 1300);
      await c.show("q", 450);
      await c.type("ans", "sí", 140);
      await c.wait(200);
      await c.check("btn", "plus", "ans");
      await c.say("Exacto: la x del bloque del grupo es la de ejecución. ¿Y el resto de usuarios, podría?");
    },
  },
  {
    tab: ["bars", "Analizador"], crumb: "retos / capas de cebolla / analizador",
    html: `<div class="pv-input pv-step" data-k="box"><span class="pv-input-label">Texto a analizar</span><span class="pv-input-text" data-k="txt"></span></div>
      <div class="pv-an pv-step" data-k="an">
        <div class="pv-an-row best"><span>Base64</span><i><u data-k="f1"></u></i><b data-k="p1">0%</b></div>
        <div class="pv-an-row"><span>Base32</span><i><u data-k="f2"></u></i><b data-k="p2">0%</b></div>
        <div class="pv-an-row"><span>Hexadecimal</span><i><u data-k="f3"></u></i><b data-k="p3">0%</b></div>
      </div>
      <div class="pv-decoded pv-step" data-k="dec"><span class="pv-meta">modelo local · 0,5 ms</span>
        <span class="pv-dec-line">${icon("arrow-right", "icon icon-inline")}Decodificado: <code data-k="dectxt"></code></span></div>
      ${coachBubble}`,
    async play(c) {
      await c.show("box", 250);
      await c.type("txt", "SG9sYSBtdW5kbw==", 55);
      await c.wait(250);
      await c.show("an", 200);
      await Promise.all([c.bar("f1", "p1", 97), c.bar("f2", "p2", 2), c.bar("f3", "p3", 1)]);
      await c.wait(400);
      await c.show("dec", 300);
      await c.type("dectxt", "Hola mundo", 50);
      await c.wait(300);
      await c.say("Era Base64. Cuando quites una capa, vuelve a analizar el resultado: a veces hay más.");
    },
  },
  {
    tab: ["mail", "Phishing"], crumb: "salas / detectar phishing / tarea 2",
    html: `<div class="pv-mail pv-step" data-k="mail">
        <div class="pv-mail-head"><span class="pv-mail-av">SN</span>
          <div class="pv-mail-from"><b>Soporte Nube</b><span>alertas@<mark class="pv-mark" data-k="m1">minube-verificar.top</mark></span></div>
          <span class="pv-mail-time">09:41</span></div>
        <p class="pv-mail-subj">Su cuenta será suspendida <mark class="pv-mark" data-k="m2">HOY</mark></p>
        <p class="pv-mail-body">Verifique su identidad para evitar el bloqueo:
          <mark class="pv-mark link" data-k="m3">minube.com/acceso</mark></p>
      </div>
      <div class="pv-findings pv-step" data-k="findings">
        <span class="pv-find" data-k="f1">${icon("alert", "icon icon-inline")}Dominio falso</span>
        <span class="pv-find" data-k="f2">${icon("alert", "icon icon-inline")}Prisa: «HOY»</span>
        <span class="pv-find" data-k="f3">${icon("alert", "icon icon-inline")}El enlace va a otro sitio</span>
      </div>
      <div class="preview-q pv-step" data-k="q"><p>¿Cuántas señales de phishing hay?</p>
        <div class="pv-options"><span class="pv-opt" data-k="o1">1</span><span class="pv-opt" data-k="o2">2</span><span class="pv-opt" data-k="o3">3</span></div></div>
      ${coachBubble}`,
    async play(c) {
      await c.show("mail", 700);
      await c.show("findings");
      for (const k of [1, 2, 3]) {
        c.el(`m${k}`).classList.add("on");
        c.el(`f${k}`).classList.add("on");
        await c.wait(800);
      }
      await c.show("q", 600);
      c.el("o3").classList.add("on");
      await c.wait(400);
      await c.say("¡Eso es! Un dominio que imita al real, prisa y un enlace que no va donde dice.");
    },
  },
];
const SCENE_MS = 11000; // duración aproximada de cada escena, para la barra de la pestaña
const SCENE_HOLD = 3200;

class SceneCancelled extends Error {}
let sceneIdx = 0, sceneToken = 0, scenePaused = false;

function sceneCtx(token, instant) {
  let elapsed = 0;
  const body = $("pv-body");
  const el = (k) => body.querySelector(`[data-k="${k}"]`);
  const bar = () => $("pv-tabs").querySelector('[aria-selected="true"] .pv-tab-bar');
  const alive = () => { if (token !== sceneToken) throw new SceneCancelled(); };
  const running = () => !scenePaused && !document.hidden && !$("view-landing").hidden;
  async function wait(ms) {
    if (instant) return alive();
    for (let left = ms; left > 0;) {
      await sleep(40);
      alive();
      if (running()) {
        left -= 40;
        elapsed += 40;
        const b = bar();
        if (b) b.style.width = `${Math.min(100, (elapsed / SCENE_MS) * 100)}%`;
      }
    }
  }
  return {
    el, wait,
    async type(k, text, speed = 38) {
      const e = el(k);
      if (instant) { e.textContent = text; return; }
      for (let i = 1; i <= text.length; i++) { e.textContent = text.slice(0, i); await wait(speed); }
    },
    async show(k, after = 0) { el(k).classList.add("in"); await wait(after); },
    async bar(fk, pk, to) {
      el(fk).style.width = `${to}%`;
      const steps = 16;
      for (let i = 1; i <= steps; i++) { el(pk).textContent = `${Math.round((to * i) / steps)}%`; await wait(instant ? 0 : 45); }
    },
    async check(btnK, plusK, inputK) {
      const btn = el(btnK);
      btn.classList.add("is-loading");
      await wait(500);
      btn.classList.remove("is-loading", "btn-primary");
      btn.classList.add("ok");
      btn.innerHTML = `${icon("check", "icon icon-inline")}Correcto`;
      el(inputK).classList.add("ok");
      el(plusK).classList.add("in");
      await wait(700);
    },
    async say(text) {
      await this.show("coach");
      const say = el("say");
      if (!instant) {
        say.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
        await wait(800);
      }
      await this.type("say", text, 16);
    },
    finish() { const b = bar(); if (b) b.style.width = "100%"; },
  };
}

async function runScene(i) {
  sceneIdx = (i + HERO_SCENES.length) % HERO_SCENES.length;
  const token = ++sceneToken;
  const sc = HERO_SCENES[sceneIdx];
  $("pv-crumb").textContent = sc.crumb;
  $("pv-tabs").querySelectorAll(".pv-tab").forEach((t, k) => {
    t.setAttribute("aria-selected", String(k === sceneIdx));
    t.querySelector(".pv-tab-bar").style.width = "0";
  });
  const body = $("pv-body");
  body.innerHTML = sc.html;
  const instant = reducedMotion();
  const c = sceneCtx(token, instant);
  if (instant) body.querySelectorAll(".pv-step").forEach((e) => e.classList.add("in"));
  try {
    await sc.play(c);
    await c.wait(SCENE_HOLD);
    c.finish();
  } catch (err) {
    if (err instanceof SceneCancelled) return;
    throw err;
  }
  if (!instant && token === sceneToken) runScene(sceneIdx + 1);
}

function initHeroScenes() {
  $("pv-tabs").innerHTML = HERO_SCENES.map((sc, k) =>
    `<button class="pv-tab" role="tab" aria-selected="false">${icon(sc.tab[0], "icon icon-inline")}${sc.tab[1]}<i class="pv-tab-bar"></i></button>`).join("");
  $("pv-tabs").querySelectorAll(".pv-tab").forEach((t, k) => (t.onclick = () => runScene(k)));
  const pv = $("hero-preview");
  pv.onmouseenter = () => (scenePaused = true);
  pv.onmouseleave = () => (scenePaused = false);
  runScene(0);
}

function initTicker() {
  const items = TICKER_ITEMS.map((t) => `<span class="ticker-item"><i></i>${escapeHtml(t)}</span>`).join("");
  $("ticker").innerHTML = items + items; // dos copias: el bucle no tiene costuras
}

// --- Slider de salas ---
let sliderPaused = false;

function sliderStep() {
  const card = $("slider-track").querySelector(".slide");
  return card ? card.offsetWidth + 16 : 300;
}

function updateSliderDots() {
  const sl = $("room-slider");
  const i = Math.round(sl.scrollLeft / sliderStep());
  $("slider-dots").querySelectorAll("button").forEach((d, k) => d.classList.toggle("on", k === i));
  $("sl-prev").disabled = sl.scrollLeft <= 4;
  $("sl-next").disabled = sl.scrollLeft + sl.clientWidth >= sl.scrollWidth - 4;
}

function slide(dir) {
  const sl = $("room-slider");
  const atEnd = sl.scrollLeft + sl.clientWidth >= sl.scrollWidth - 4;
  if (dir > 0 && atEnd) sl.scrollTo({ left: 0, behavior: "smooth" });
  else sl.scrollBy({ left: dir * sliderStep(), behavior: "smooth" });
}

function renderSlider() {
  const rooms = roomsData.paths.flatMap((p) => p.rooms.map((r) => ({ ...r, path: p })));
  $("slider-track").innerHTML = rooms.map((r) => {
    const cta = !me || !r.answered ? "Empezar" : r.completed ? "Repasar" : "Continuar";
    return `<button class="slide ${r.completed ? "completed" : ""}" data-room="${r.id}">
      <span class="slide-path">${icon(r.path.icon, "icon icon-inline")}${escapeHtml(r.path.title)}</span>
      <span class="slide-icon">${icon(r.icon)}</span>
      <strong>${escapeHtml(r.title)}</strong>
      <span class="slide-text">${escapeHtml(r.summary)}</span>
      <span class="tags"><span class="tag ${diffClass(r.difficulty)}">${escapeHtml(r.difficulty)}</span><span class="tag">${r.questions} preguntas</span></span>
      ${me ? progressBar(r.answered, r.questions) : ""}
      <span class="slide-cta">${cta} ${icon("arrow-right", "icon icon-inline")}</span>
    </button>`;
  }).join("");
  $("slider-track").querySelectorAll(".slide").forEach((b) => (b.onclick = () => navigate(`#sala/${b.dataset.room}`)));
  $("slider-dots").innerHTML = rooms.map((r, k) => `<button aria-label="Ir a ${escapeHtml(r.title)}"></button>`).join("");
  $("slider-dots").querySelectorAll("button").forEach((d, k) => (d.onclick = () =>
    $("room-slider").scrollTo({ left: k * sliderStep(), behavior: "smooth" })));
  updateSliderDots();
}

function initSlider() {
  const sl = $("room-slider");
  $("sl-prev").onclick = () => slide(-1);
  $("sl-next").onclick = () => slide(1);
  sl.addEventListener("scroll", () => requestAnimationFrame(updateSliderDots), { passive: true });
  for (const ev of ["mouseenter", "focusin", "touchstart"]) sl.addEventListener(ev, () => (sliderPaused = true), { passive: true });
  for (const ev of ["mouseleave", "focusout"]) sl.addEventListener(ev, () => (sliderPaused = false));
  sl.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") { e.preventDefault(); slide(1); }
    if (e.key === "ArrowLeft") { e.preventDefault(); slide(-1); }
  });
  if (reducedMotion()) return;
  setInterval(() => {
    if (!sliderPaused && !document.hidden && !$("view-landing").hidden && isInViewport(sl)) slide(1);
  }, 4500);
}

function isInViewport(el) {
  const r = el.getBoundingClientRect();
  return r.top < window.innerHeight && r.bottom > 0;
}

// --- Aparición al hacer scroll ---
function initReveal() {
  const els = document.querySelectorAll("#view-landing .section-head, #view-landing .steps .step, #view-landing .path-list, "
    + "#view-landing .hint-table, #view-landing .checklist, #view-landing .cta, #view-landing .slider, #view-landing .section-foot");
  els.forEach((el, i) => {
    el.classList.add("reveal");
    if (el.classList.contains("step")) el.style.setProperty("--d", `${[...el.parentNode.children].indexOf(el) * 90}ms`);
  });
  if (reducedMotion() || !("IntersectionObserver" in window)) { els.forEach((el) => el.classList.add("in")); return; }
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  els.forEach((el) => io.observe(el));
}

function initLanding() {
  initHeroScenes();
  initTicker();
  initSlider();
  initReveal();
}

let factsAnimated = false;

function renderLanding() {
  document.querySelectorAll("[data-action='register']").forEach((b) => {
    b.innerHTML = `${me ? "Seguir aprendiendo" : "Crear cuenta gratis"} ${icon("arrow-right", "icon icon-inline")}`;
  });
  if (!roomsData) return;
  const rooms = roomsData.paths.flatMap((p) => p.rooms);
  const questions = rooms.reduce((n, r) => n + r.questions, 0);
  const official = challenges.filter((c) => !c.generated).length;
  $("hero-facts").innerHTML = [
    [roomsData.paths.length, "rutas"], [rooms.length, "salas"], [questions, "preguntas"], [official, "retos"],
  ].map(([n, label]) => `<span><b data-n="${n}">${factsAnimated ? n : 0}</b>${label}</span>`).join("");
  if (!factsAnimated) {
    factsAnimated = true;
    $("hero-facts").querySelectorAll("b").forEach((b) => { b.dataset.value = 0; countUp(b, Number(b.dataset.n), 1100); });
  }
  renderSlider();

  $("landing-paths").innerHTML = roomsData.paths.map((p) => `
    <button class="path-row" data-goto="#salas">
      <span class="icon-tile">${icon(p.icon)}</span>
      <div>
        <h3>${escapeHtml(p.title)}</h3>
        <p>${escapeHtml(p.description)}</p>
        <div class="tags">${p.rooms.map((r) => `<span class="tag">${escapeHtml(r.title)}</span>`).join("")}</div>
      </div>
      <span class="path-row-meta">${p.rooms.length} salas · ${p.questions} preg. ${icon("arrow-right", "icon icon-inline")}</span>
    </button>`).join("");
  $("landing-paths").querySelectorAll("[data-goto]").forEach((b) => (b.onclick = () => navigate(b.dataset.goto)));
}

// ---------- Salas ----------

function renderBadges() {
  const badges = roomsData?.badges || [];
  $("badges").innerHTML = badges.length
    ? badges.map((b) => `<span class="badge ${b.kind}" title="${b.kind === "ruta" ? "Ruta completada" : "Sala completada"}">${icon(b.icon)}${escapeHtml(b.name)}</span>`).join("")
    : `<p class="empty-note">${me ? "Completa una sala para ganar tu primera insignia." : "Inicia sesión para guardar tu progreso y ganar insignias."}</p>`;
}

function renderPaths() {
  const total = roomsData.paths.reduce((n, p) => n + p.questions, 0);
  const done = roomsData.paths.reduce((n, p) => n + p.answered, 0);
  $("rooms-progress").style.width = `${total ? Math.round((done / total) * 100) : 0}%`;
  $("rooms-progress-text").textContent = `${done}/${total} preguntas respondidas`;

  $("paths").innerHTML = roomsData.paths.map((p) => `
    <section class="path">
      <div class="path-head">
        <span class="icon-tile lg">${icon(p.icon)}</span>
        <div class="path-info">
          <h2>${escapeHtml(p.title)}</h2>
          <p>${escapeHtml(p.description)}</p>
        </div>
        <div class="path-progress">${progressBar(p.answered, p.questions)}
          <span class="small-text">${p.answered}/${p.questions} preguntas</span></div>
      </div>
      <div class="room-grid">
        ${p.rooms.map((r) => `
          <button class="room-card ${r.completed ? "completed" : ""}" data-room="${r.id}">
            <span class="icon-tile">${icon(r.icon)}</span>
            <strong>${escapeHtml(r.title)}</strong>
            <span class="card-text">${escapeHtml(r.summary)}</span>
            <span class="tags"><span class="tag ${diffClass(r.difficulty)}">${escapeHtml(r.difficulty)}</span>
              <span class="tag">${r.answered}/${r.questions} preguntas</span></span>
            ${progressBar(r.answered, r.questions)}
          </button>`).join("")}
      </div>
    </section>`).join("");
  document.querySelectorAll("#paths .room-card").forEach((b) => (b.onclick = () => navigate(`#sala/${b.dataset.room}`)));
}

async function loadRooms() {
  roomsData = await api("/api/rooms");
  roomsStale = false;
  renderBadges();
  renderPaths();
  renderLanding();
}

function openTaskId() {
  if (document.querySelector(`#tasks details[open][data-task="${activeTaskId}"]`)) return activeTaskId;
  return document.querySelector("#tasks details[open]")?.dataset.task || null;
}

function renderRoomProgress() {
  const r = currentRoom;
  $("room-progress").style.width = `${Math.round((r.answered / r.questions) * 100)}%`;
  $("room-progress-text").textContent = r.completed
    ? `Sala completada · ${r.answered}/${r.questions} preguntas`
    : `${r.answered}/${r.questions} preguntas respondidas`;
}

function questionHtml(q) {
  const input = q.options
    ? `<div class="options" role="radiogroup">${q.options.map((o) => `<label class="option"><input type="radio" name="${q.id}" value="${escapeHtml(o)}"
        ${q.answered && q.answer && norm(o) === norm(q.answer) ? "checked" : ""} ${q.answered ? "disabled" : ""}>${escapeHtml(o)}</label>`).join("")}</div>`
    : `<input class="answer-input" name="${q.id}" placeholder="${escapeHtml(q.mask || "")}" autocomplete="off" spellcheck="false"
        aria-label="Respuesta" value="${q.answered ? escapeHtml(q.answer || "") : ""}" ${q.answered ? "disabled" : ""}>`;
  const button = q.answered
    ? `<button type="submit" class="btn btn-secondary" disabled>${icon("check", "icon icon-inline")}Correcto</button>`
    : `<button type="submit" class="btn btn-primary">Comprobar</button>`;
  return `<form class="question ${q.answered ? "answered" : ""}" data-q="${q.id}">
      <p class="q-prompt">${renderInline(escapeHtml(q.prompt))}<span class="pts">${q.points} pts</span></p>
      <div class="q-row">${input}${button}</div>
      <p class="q-result" role="status"></p>
    </form>`;
}

// openIds: tareas que deben quedar desplegadas (por defecto, la primera sin terminar).
function renderRoom(openIds = null) {
  const r = currentRoom;
  $("room-icon").innerHTML = icon(r.icon);
  $("room-title").textContent = r.title;
  $("room-summary").textContent = r.summary;
  renderRoomProgress();
  const firstOpen = r.tasks.find((t) => t.questions.some((q) => !q.answered)) || r.tasks[0];
  openIds = openIds || [firstOpen.id];
  $("tasks").innerHTML = r.tasks.map((t, i) => {
    const done = t.questions.every((q) => q.answered);
    return `<details class="task panel" data-task="${t.id}" ${openIds.includes(t.id) ? "open" : ""}>
      <summary>
        <span class="task-num ${done ? "done" : ""}">${done ? icon("check", "icon icon-inline") : i + 1}</span>
        <span class="task-label">Tarea ${i + 1}</span><span>${escapeHtml(t.title)}</span>
        <span class="chev">${icon("chevron-down")}</span>
      </summary>
      <div class="task-body">
        <div class="theory">${renderMarkdown(t.content)}</div>
        ${t.data ? `<div><p class="data-label">Datos</p><div class="data-box"><pre>${escapeHtml(t.data)}</pre></div></div>` : ""}
        <div class="questions">${t.questions.map(questionHtml).join("")}</div>
      </div>
    </details>`;
  }).join("");
  document.querySelectorAll("#tasks .question").forEach((f) => (f.onsubmit = submitAnswer));
  document.querySelectorAll("#tasks details").forEach((d) =>
    d.addEventListener("toggle", () => { if (d.open) activeTaskId = d.dataset.task; }));
  if (!openIds.includes(activeTaskId)) activeTaskId = openIds[0];
}

async function openRoom(id) {
  const room = await api(`/api/rooms/${id}`);
  currentRoom = room;
  activeTaskId = null;
  showView("room");
  renderRoom();
  const box = $("room-messages");
  box.innerHTML = "";
  if (!me) return addNotice(box, "Inicia sesión para guardar tus respuestas y hablar con el Coach.", true);
  const chat = await api(`/api/rooms/${id}/chat`).catch(() => []);
  if (currentRoom !== room) return;
  if (!chat.length) addNotice(box, "¿Te atascas con alguna pregunta? Pregúntame y te guío.");
  for (const m of chat) addMessage(m.role, m.role === "user" ? showUserLine(m.content) : m.content, box);
}

async function submitAnswer(e) {
  e.preventDefault();
  const form = e.currentTarget;
  const qid = form.dataset.q;
  if (!me) {
    const typed = form.querySelector(".answer-input")?.value || form.querySelector("input[type=radio]:checked")?.value;
    // Tras registrarse la sala se vuelve a pintar: se repone la respuesta y se envía.
    return openAuth("register", () => {
      const again = document.querySelector(`#tasks .question[data-q="${qid}"]`);
      if (!again || !typed) return;
      const input = again.querySelector(".answer-input");
      if (input) input.value = typed;
      else again.querySelector(`input[type=radio][value="${CSS.escape(typed)}"]`)?.click();
      again.requestSubmit();
    });
  }
  const field = form.querySelector(".answer-input") || form.querySelector("input[type=radio]:checked");
  const answer = field?.value.trim();
  const result = form.querySelector(".q-result");
  if (!answer) {
    result.className = "q-result bad";
    result.textContent = form.querySelector(".options") ? "Elige una opción." : "Escribe una respuesta.";
    return;
  }
  const btn = form.querySelector("button");
  btn.classList.add("is-loading");
  try {
    const res = await api(`/api/rooms/${currentRoom.id}/questions/${qid}`, { method: "POST", body: JSON.stringify({ answer }) });
    if (!res.correct) {
      result.className = "q-result bad";
      result.textContent = "No es correcta. Vuelve a leer la teoría o pregunta al Coach.";
      form.classList.remove("shake");
      void form.offsetWidth;
      form.classList.add("shake");
      return;
    }
    const task = currentRoom.tasks.find((t) => t.questions.some((x) => x.id === qid));
    const q = task.questions.find((x) => x.id === qid);
    if (!q.answered) currentRoom.answered += 1;
    Object.assign(q, { answered: true, answer });
    currentRoom.completed = res.room_completed;
    // Se conservan las tareas abiertas; al terminar una, se abre la siguiente pendiente.
    const openIds = [...document.querySelectorAll("#tasks details[open]")].map((d) => d.dataset.task);
    activeTaskId = task.id;
    const next = task.questions.every((x) => x.answered)
      && currentRoom.tasks.slice(currentRoom.tasks.indexOf(task) + 1).find((t) => t.questions.some((x) => !x.answered));
    if (next) openIds.push(next.id);
    renderRoom(openIds);
    if (next) activeTaskId = next.id;
    const msg = res.already ? "Ya la tenías respondida." : `Correcto · <b>+${res.earned} pts</b>`;
    const badges = res.new_badges.map((b) => `<div class="toast-badge">${icon(b.icon, "icon icon-inline")}Nueva insignia: <b>${escapeHtml(b.name)}</b></div>`).join("");
    showToast(`<div>${msg}</div>${badges}`);
    roomsStale = true;
    await refreshMe();
  } catch (err) {
    result.className = "q-result bad";
    result.textContent = err.message;
  } finally {
    btn.classList.remove("is-loading");
  }
}

async function askRoomCoach(e) {
  e.preventDefault();
  if (!currentRoom || roomBusy) return;
  if (!me) return openAuth("login");
  const message = $("room-chat-input").value.trim();
  if (!message) return;
  $("room-chat-input").value = "";
  const box = $("room-messages");
  box.querySelector(".msg.system:not(.error)")?.remove();
  addMessage("user", message, box);
  const bubble = addMessage("assistant", "", box);
  roomBusy = true;
  const btn = $("room-chat-form").querySelector("button");
  btn.disabled = true;
  await streamCoach(`/api/rooms/${currentRoom.id}/tutor`, { message, level: level(), task_id: openTaskId() }, bubble, box);
  roomBusy = false;
  btn.disabled = false;
}

// ---------- Retos ----------

const CATEGORY_ICONS = { "Codificación": "binary", "Criptografía": "lock", "Web": "code", "Forense": "search" };
const CATEGORY_ORDER = ["Codificación", "Criptografía", "Web", "Forense"];

function challengeCard(ch) {
  const status = ch.solved
    ? `<span class="tag ok">+${ch.earned} pts</span>`
    : `<span class="tag">${ch.points} pts</span>`;
  const by = ch.author ? `<span class="tag ai">por ${escapeHtml(ch.author)}</span>` : "";
  return `<button class="room-card challenge-card ${ch.solved ? "completed" : ""}" data-ch="${ch.id}">
      <span class="icon-tile">${icon(CATEGORY_ICONS[ch.category] || "flag")}</span>
      <strong>${escapeHtml(ch.title)}</strong>
      <span class="card-text clamp">${escapeHtml(ch.description)}</span>
      <span class="tags"><span class="tag ${diffClass(ch.difficulty)}">${escapeHtml(ch.difficulty)}</span>${status}${by}</span>
    </button>`;
}

function renderChallenges() {
  const groups = [];
  const official = challenges.filter((c) => !c.generated);
  const cats = [...new Set([...CATEGORY_ORDER, ...official.map((c) => c.category)])];
  for (const cat of cats) {
    const items = official.filter((c) => c.category === cat);
    if (items.length) groups.push({ title: cat, icon: CATEGORY_ICONS[cat] || "flag", items });
  }
  groups.push({ title: "Creados por jugadores", icon: "plus", items: challenges.filter((c) => c.generated),
                empty: "Todavía no hay ninguno. Crea el primero con el formulario de arriba." });

  $("challenge-groups").innerHTML = groups.map((g) => `
    <section class="path">
      <div class="group-head">${icon(g.icon, "icon icon-inline")}<h3>${escapeHtml(g.title)}</h3>
        <span class="count">${g.items.filter((c) => c.solved).length}/${g.items.length}</span></div>
      ${g.items.length ? `<div class="room-grid">${g.items.map(challengeCard).join("")}</div>`
                       : `<p class="empty-note">${g.empty}</p>`}
    </section>`).join("");
  document.querySelectorAll(".challenge-card").forEach((b) => (b.onclick = () => navigate(`#reto/${b.dataset.ch}`)));

  const solved = challenges.filter((c) => c.solved).length;
  $("ch-progress").style.width = `${challenges.length ? Math.round((solved / challenges.length) * 100) : 0}%`;
  $("ch-progress-text").textContent = `${solved}/${challenges.length} retos resueltos`;
}

function addMessage(role, content, box = $("messages")) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = role === "assistant" ? renderMarkdown(content) : escapeHtml(content);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function addNotice(box, text, withLogin = false) {
  const div = document.createElement("div");
  div.className = "msg system";
  div.textContent = text;
  if (withLogin) {
    const b = document.createElement("button");
    b.className = "btn btn-secondary btn-sm";
    b.style.marginTop = "10px";
    b.textContent = "Iniciar sesión";
    b.onclick = () => openAuth("login");
    div.append(document.createElement("br"), b);
  }
  box.appendChild(div);
}

function setFlagResult(text, ok) {
  const el = $("flag-result");
  el.className = "flag-result " + (text ? (ok ? "ok" : "bad") : "");
  el.innerHTML = text ? `${icon(ok ? "check" : "alert", "icon icon-inline")}${text}` : "";
}

function renderHintStatus() {
  const h = current?.max_hint || 0;
  $("hint-status").textContent = current?.solved ? "" : h ? `Has usado pistas hasta el nivel ${h}.` : "";
}

function showUserLine(text) {
  const m = text.match(/^((?:\[[^\]]*\] ?)+)\n([\s\S]*)$/);
  if (!m) return text;
  const hint = m[1].match(/pista de nivel (\d)/);
  return (hint ? `Pista de nivel ${hint[1]}: ` : "") + m[2];
}

async function openChallenge(id) {
  current = challenges.find((c) => c.id === id);
  if (!current) return navigate("#retos");
  const ch = current;
  showView("challenge");
  $("ch-icon").innerHTML = icon(CATEGORY_ICONS[ch.category] || "flag");
  $("ch-title").textContent = ch.title;
  $("ch-diff").textContent = ch.difficulty;
  $("ch-diff").className = `tag ${diffClass(ch.difficulty)}`;
  $("ch-cat").textContent = ch.category;
  $("ch-points").textContent = `${ch.points} pts`;
  $("ch-author").hidden = !ch.generated;
  $("ch-author").textContent = ch.generated ? `por ${ch.author}` : "";
  $("ch-desc").textContent = ch.description;
  $("ch-data").textContent = ch.data;
  resetAnalyzer();
  $("flag-input").value = "";
  setFlagResult(ch.solved ? `Resuelto · +${ch.earned} pts` : "", true);
  renderHintStatus();

  const box = $("messages");
  box.innerHTML = "";
  if (!me) return addNotice(box, "Inicia sesión para enviar flags y hablar con el Coach.", true);
  const chat = await api(`/api/challenges/${id}/chat`).catch(() => []);
  if (current !== ch) return;
  if (!chat.length) addNotice(box, "No te daré la flag, pero te ayudaré a encontrarla.");
  for (const m of chat) addMessage(m.role, m.role === "user" ? showUserLine(m.content) : m.content, box);
}

async function submitFlag(e) {
  e.preventDefault();
  const flag = $("flag-input").value.trim();
  if (!current) return;
  if (!flag) return setFlagResult("Escribe la flag antes de enviarla.", false);
  if (!me) return openAuth("register", () => { $("flag-input").value = flag; $("flag-form").requestSubmit(); });
  const btn = $("flag-form").querySelector("button");
  btn.classList.add("is-loading");
  try {
    const res = await api(`/api/challenges/${current.id}/submit`, { method: "POST", body: JSON.stringify({ flag }) });
    if (!res.correct) {
      setFlagResult("Esa no es la flag. Sigue probando.", false);
      return;
    }
    Object.assign(current, { solved: true, earned: res.earned });
    setFlagResult(res.already ? `Ya lo habías resuelto · +${res.earned} pts` : `¡Correcto! · +${res.earned} pts`, true);
    if (!res.already) showToast(`Reto resuelto · <b>+${res.earned} pts</b>`);
    renderChallenges();
    renderHintStatus();
    await refreshMe();
  } catch (err) {
    setFlagResult(escapeHtml(err.message), false);
  } finally {
    btn.classList.remove("is-loading");
  }
}

function setBusy(v) {
  busy = v;
  document.querySelectorAll("#chat-form button, .hint-buttons button").forEach((b) => (b.disabled = v));
}

// Envía un mensaje al Coach y va pintando la respuesta (NDJSON: una línea JSON por evento).
async function streamCoach(url, body, bubble, box) {
  bubble.innerHTML = '<span class="typing" aria-label="El Coach está escribiendo"><i></i><i></i><i></i></span>';
  let text = "";
  let final = null;
  try {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      if (r.status === 401) openAuth("login");
      throw new Error(Array.isArray(data.detail) ? "Datos no válidos." : data.detail || `Error ${r.status}`);
    }
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const ev = JSON.parse(line);
        if (ev.type === "text") {
          text += ev.text;
          bubble.innerHTML = renderMarkdown(text);
        } else if (ev.type === "done" || ev.type === "refusal") {
          bubble.innerHTML = renderMarkdown(ev.reply);
          final = ev;
        } else if (ev.type === "error") {
          throw new Error(ev.message);
        }
        box.scrollTop = box.scrollHeight;
      }
    }
  } catch (err) {
    bubble.className = "msg system error";
    bubble.textContent = err.message;
  }
  return final;
}

async function askTutor(message, hintLevel = null) {
  if (!current || busy) return;
  if (!me) return openAuth("login");
  if (!message && !hintLevel) return;
  const ch = current;
  const box = $("messages");
  box.querySelector(".msg.system:not(.error)")?.remove();
  addMessage("user", hintLevel ? `Pista de nivel ${hintLevel}${message ? ": " + message : ""}` : message, box);
  const bubble = addMessage("assistant", "", box);
  setBusy(true);
  const ev = await streamCoach(`/api/challenges/${ch.id}/tutor`, { message, level: level(), hint_level: hintLevel }, bubble, box);
  setBusy(false);
  if (ev?.type === "done" && hintLevel && !ch.solved) {
    ch.max_hint = Math.max(ch.max_hint || 0, hintLevel);
    if (current === ch) renderHintStatus();
  }
}

// ---------- Crear reto ----------

async function submitGenerate(e) {
  e.preventDefault();
  if (!me) return openAuth("register");
  const btn = $("gen-form").querySelector("button");
  btn.classList.add("is-loading");
  btn.disabled = true;
  $("gen-status").className = "small-text muted";
  $("gen-status").textContent = "Preparando el reto. Puede tardar unos segundos…";
  try {
    const ch = await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({ theme: $("gen-theme").value.trim(), difficulty: $("gen-difficulty").value }),
    });
    challenges.push({ ...ch, solved: false, earned: 0, max_hint: 0 });
    renderChallenges();
    $("gen-theme").value = "";
    $("gen-status").textContent = "";
    navigate(`#reto/${ch.id}`);
  } catch (err) {
    $("gen-status").className = "small-text flag-result bad";
    $("gen-status").textContent = err.message;
  } finally {
    btn.classList.remove("is-loading");
    btn.disabled = false;
  }
}

// ---------- Analizador local ----------

function resetAnalyzer() {
  $("an-input").value = current?.data || "";
  $("an-results").innerHTML = "";
  $("an-meta").textContent = "";
  $("an-figure").hidden = true;
  if (!$("analyzer").open) return;
  runAnalyzer();
}

// Gráfica SVG de frecuencias: barras = tu texto, puntos = español habitual.
function frequencyChart(f) {
  const W = 520, H = 170, L = 30, B = 22, T = 8;
  const max = Math.max(...f.text, ...f.spanish);
  const top = Math.max(10, Math.ceil(max / 10) * 10); // múltiplo de 10: las marcas del eje salen enteras
  const step = (W - L) / 26;
  const y = (v) => T + (H - T - B) * (1 - v / top);
  const grid = [0, top / 2, top].map((v) => `
    <line x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}" class="ch-grid"/>
    <text x="${L - 6}" y="${y(v) + 4}" class="ch-axis" text-anchor="end">${v}</text>`).join("");
  const cols = f.letters.map((l, i) => {
    const x = L + i * step;
    const bh = (H - T - B) * (f.text[i] / top);
    return `<g class="ch-col"><title>${l}: ${f.text[i].toFixed(1)} % en tu texto · ${f.spanish[i].toFixed(1)} % en español</title>
      <rect x="${x}" y="${T}" width="${step}" height="${H - T - B}" class="ch-hit"/>
      ${bh > 0 ? `<rect x="${x + step * 0.18}" y="${y(f.text[i])}" width="${step * 0.64}" height="${bh}" rx="2" class="ch-bar"/>` : ""}
      <circle cx="${x + step / 2}" cy="${y(f.spanish[i])}" r="3.2" class="ch-dot"/>
      <text x="${x + step / 2}" y="${H - 6}" class="ch-axis" text-anchor="middle">${l}</text></g>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Frecuencia de letras del texto comparada con el español">${grid}${cols}</svg>`;
}

let analyzeSeq = 0;
async function runAnalyzer() {
  const text = $("an-input").value.trim();
  const seq = ++analyzeSeq;
  if (text.length < 4) {
    $("an-results").innerHTML = text
      ? `<p class="an-explain">Escribe al menos 4 caracteres para analizarlo.</p>` : "";
    $("an-meta").textContent = "";
    $("an-figure").hidden = true;
    return;
  }
  try {
    const t0 = performance.now();
    const res = await api("/api/analyze", { method: "POST", body: JSON.stringify({ text }) });
    if (seq !== analyzeSeq) return; // llegó una respuesta más nueva
    const [best] = res.predictions;
    const rows = res.predictions.map((p, i) => {
      const pct = Math.round(p.probability * 100);
      return `<div class="an-row ${i === 0 ? "best" : ""}" title="${escapeHtml(p.explanation)}">
        <span>${escapeHtml(p.name)}</span>
        <div class="an-track"><div class="an-fill" style="width:${pct}%"></div></div>
        <span class="an-pct">${pct}%</span></div>`;
    });
    const unsure = best.probability < 0.55;
    rows.push(unsure
      ? `<p class="an-explain warn">${icon("alert", "icon icon-inline")}No está claro. Puede que haya varias capas mezcladas o que el texto sea muy corto: prueba a decodificar una parte.</p>`
      : `<p class="an-explain">${escapeHtml(best.explanation)}</p>`);
    $("an-results").innerHTML = rows.join("");
    const ms = (v, d = 1) => v.toLocaleString("es-ES", { maximumFractionDigits: d });
    $("an-meta").textContent = `modelo local · ${ms(res.elapsed_ms)} ms en el servidor · ${ms(performance.now() - t0, 0)} ms en total`;
    $("an-figure").hidden = !res.frequencies;
    if (res.frequencies) $("an-chart").innerHTML = frequencyChart(res.frequencies);
  } catch (err) {
    if (seq === analyzeSeq) $("an-results").innerHTML = `<p class="flag-result bad">${escapeHtml(err.message)}</p>`;
  }
}

// ---------- Roadmap ----------

const STATUS_LABEL = {
  completado: "Completado", en_curso: "En curso", disponible: "Disponible aquí", externo: "Recursos externos",
};

function topicHtml(t) {
  const internal = [
    ...t.rooms.map((r) => `
      <button class="rm-link" data-goto="#sala/${r.id}">
        <span class="rm-link-kind">Sala</span><span class="rm-link-title">${escapeHtml(r.title)}</span>
        <span class="rm-link-meta">${r.done === r.total ? icon("check", "icon icon-inline") : `${r.done}/${r.total}`}</span>
      </button>`),
    // Con muchos retos, un único enlace al catálogo en lugar de una lista larga.
    ...(t.challenges.length > 3
      ? [`<button class="rm-link" data-goto="#retos">
          <span class="rm-link-kind">Retos</span><span class="rm-link-title">Todos los retos</span>
          <span class="rm-link-meta">${t.challenges.filter((c) => c.solved).length}/${t.challenges.length}</span>
        </button>`]
      : t.challenges.map((c) => `
      <button class="rm-link" data-goto="#reto/${c.id}">
        <span class="rm-link-kind">Reto</span><span class="rm-link-title">${escapeHtml(c.title)}</span>
        <span class="rm-link-meta">${c.solved ? icon("check", "icon icon-inline") : ""}</span>
      </button>`)),
  ].join("");
  const external = t.resources.map((r) => `
      <a class="rm-ext" href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer">
        ${escapeHtml(r.name)}${icon("external", "icon icon-inline")}</a>`).join("");
  return `<article class="topic status-${t.status}" data-topic="${t.id}">
      <div class="topic-head">
        <h3>${escapeHtml(t.title)}</h3>
        <span class="status status-${t.status}"><i></i>${STATUS_LABEL[t.status]}</span>
      </div>
      <p class="topic-desc">${escapeHtml(t.description)}</p>
      <div class="tags">${t.skills.map((k) => `<span class="tag">${escapeHtml(k)}</span>`).join("")}</div>
      ${t.total ? `<div class="topic-progress">${progressBar(t.done, t.total)}</div>` : ""}
      ${internal ? `<div class="rm-links">${internal}</div>` : ""}
      ${external ? `<div class="rm-exts"><span class="rm-exts-label">Aprende fuera</span>${external}</div>` : ""}
    </article>`;
}

function renderRoadmap() {
  const topics = roadmapData.flatMap((s) => s.topics);
  const here = topics.filter((t) => t.total);
  const completed = here.filter((t) => t.status === "completado").length;
  $("rm-progress").style.width = `${here.length ? Math.round((completed / here.length) * 100) : 0}%`;
  $("rm-progress-text").textContent = `${completed}/${here.length} temas disponibles completados · ${topics.length} en total`;
  document.querySelectorAll(".rm-filter [data-filter]").forEach((b) =>
    b.setAttribute("aria-selected", String(b.dataset.filter === roadmapFilter)));

  $("roadmap").innerHTML = roadmapData.map((stage, i) => {
    const visible = stage.topics.filter((t) => roadmapFilter === "all" || t.total);
    const avail = stage.topics.filter((t) => t.total);
    const state = avail.length && avail.every((t) => t.status === "completado") ? "done"
      : stage.topics.some((t) => t.done) ? "active" : "";
    return `<li class="stage ${state}">
        <span class="stage-node">${state === "done" ? icon("check", "icon icon-inline") : i + 1}</span>
        <div class="stage-body">
          <div class="stage-head">
            <h2>${escapeHtml(stage.title)}</h2>
            <span class="tag">${escapeHtml(stage.duration)}</span>
          </div>
          <p class="stage-desc">${escapeHtml(stage.description)}</p>
          ${visible.length ? `<div class="topic-grid">${visible.map(topicHtml).join("")}</div>`
                           : `<p class="empty-note">En esta etapa todavía no hay salas ni retos: usa los recursos externos.</p>`}
        </div>
      </li>`;
  }).join("");
  $("roadmap").querySelectorAll("[data-goto]").forEach((b) => (b.onclick = () => navigate(b.dataset.goto)));
}

async function loadRoadmap() {
  roadmapData = await api("/api/roadmap");
  renderRoadmap();
}

// ---------- Clasificación ----------

const PERIOD_TEXT = { all: "", week: " en los últimos 7 días" };
const pad2 = (n) => String(n).padStart(2, "0");
const statsLine = (r) => `${r.rooms} ${r.rooms === 1 ? "sala" : "salas"} · ${r.solved} ${r.solved === 1 ? "reto" : "retos"}`;

function renderLbMe(data) {
  const box = $("lb-me");
  if (!me) {
    box.innerHTML = `<div class="lb-me-card guest">
        <div><strong>Entra en la clasificación</strong><p>Crea una cuenta y cada pregunta o reto que resuelvas sumará puntos.</p></div>
        <button class="btn btn-primary" id="lb-join">Crear cuenta</button></div>`;
    $("lb-join").onclick = () => openAuth("register");
    return;
  }
  const m = data.me;
  if (!m) {
    box.innerHTML = `<div class="lb-me-card guest">
        <div><strong>Aún no tienes puntos${PERIOD_TEXT[data.period]}</strong><p>Responde una pregunta de cualquier sala para entrar en la tabla.</p></div>
        <button class="btn btn-primary" data-goto="#salas">Ir a las salas</button></div>`;
  } else {
    const next = m.ahead
      ? `Te faltan <b>${m.gap} pts</b> para adelantar a <b>${escapeHtml(m.ahead)}</b>.`
      : "Vas primero. Que no te alcancen.";
    box.innerHTML = `<div class="lb-me-card">
        ${avatar(m.username, "av av-lg")}
        <div class="lb-me-rank"><span>Tu posición</span><b>#${m.rank}</b><small>de ${data.players}</small></div>
        <div class="lb-me-stat"><span>Puntos${PERIOD_TEXT[data.period]}</span><b>${m.score}</b></div>
        <div class="lb-me-next"><p>${next}</p><span class="small-text">${statsLine(m)}</span></div>
        <button class="btn btn-secondary" data-goto="#salas">Sumar puntos ${icon("arrow-right", "icon icon-inline")}</button>
      </div>`;
  }
  box.querySelectorAll("[data-goto]").forEach((b) => (b.onclick = () => navigate(b.dataset.goto)));
}

function renderPodium(rows) {
  const top = [rows[1], rows[0], rows[2]].filter(Boolean); // 2.º, 1.º, 3.º
  $("lb-podium").hidden = !rows.length;
  $("lb-podium").innerHTML = top.map((r) => `
    <div class="podium-spot p${r.rank} ${me && r.username === me.user ? "me" : ""}">
      <span class="podium-rank">${pad2(r.rank)}</span>
      ${avatar(r.username, "av podium-avatar")}
      <strong class="podium-name">${escapeHtml(r.username)}</strong>
      <span class="podium-score">${r.score}<small> pts</small></span>
      <span class="podium-meta">${statsLine(r)}</span>
      <span class="podium-step" aria-hidden="true"></span>
    </div>`).join("");
}

async function loadLeaderboard() {
  const data = await api(`/api/leaderboard?period=${lbPeriod}`);
  document.querySelectorAll(".lb-period [data-period]").forEach((b) =>
    b.setAttribute("aria-selected", String(b.dataset.period === lbPeriod)));
  const rows = data.rows;
  renderLbMe(data);
  renderPodium(rows);
  const rest = rows.slice(3);
  const leader = rows[0]?.score || 1;
  $("lb-board").hidden = !rest.length;
  $("leaderboard").innerHTML = rest.map((r) => `
    <tr class="${me && r.username === me.user ? "me" : ""}">
      <td><span class="rank">${pad2(r.rank)}</span></td>
      <td><span class="player">${avatar(r.username)}${escapeHtml(r.username)}</span></td>
      <td class="bar-col"><div class="score-cell"><div class="progress"><div class="progress-bar" style="width:${Math.round((r.score / leader) * 100)}%"></div></div><b>${r.score}</b></div></td>
      <td class="num">${r.rooms}</td><td class="num">${r.solved}</td>
    </tr>`).join("");
  const empty = $("leaderboard-empty");
  empty.hidden = rows.length > 0;
  empty.textContent = data.period === "week"
    ? "Nadie ha sumado puntos en los últimos 7 días. Es un buen momento para ponerse primero."
    : "Todavía no hay nadie en la tabla. Responde una pregunta y estrénala.";
}

// ---------- Bit, la mascota ----------

const BIT_SVG = `<svg class="bit-svg" viewBox="0 0 64 64" aria-hidden="true">
  <path d="M32 6v10" class="bit-antenna"/>
  <path d="M33 5 43.5 8.6 33 12.2z" class="bit-flag"/>
  <path d="M32 17 50.5 27.7v21.6L32 60 13.5 49.3V27.7z" class="bit-body"/>
  <rect x="19.5" y="29.5" width="25" height="17" rx="6" class="bit-screen"/>
  <g class="bit-eyes"><rect x="24.6" y="33.4" width="4.6" height="7" rx="2.3"/><rect x="34.8" y="33.4" width="4.6" height="7" rx="2.3"/></g>
  <rect x="29.2" y="42.6" width="5.6" height="1.8" rx=".9" class="bit-mouth"/>
</svg>`;

let bitStarted = false;
let bitBusy = false;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const isMobile = () => window.matchMedia("(max-width: 560px)").matches;

function currentView() {
  return VIEWS.find((v) => !$(`view-${v}`).hidden) || "landing";
}

function bitMessage(role, html) {
  const box = $("bit-messages");
  const div = document.createElement("div");
  div.className = `bit-msg ${role}`;
  div.innerHTML = html;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function renderBitSuggestions(list) {
  $("bit-suggestions").innerHTML = list.map((t) => `<button type="button" class="bit-chip">${escapeHtml(t)}</button>`).join("");
  $("bit-suggestions").querySelectorAll(".bit-chip").forEach((b) => (b.onclick = () => askBit(b.textContent)));
}

async function askBit(message, silent = false) {
  if (bitBusy) return;
  bitBusy = true;
  if (!silent) bitMessage("user", escapeHtml(message));
  $("bit-suggestions").innerHTML = "";
  $("bit-panel").classList.add("thinking");
  const bubble = bitMessage("bot", '<span class="typing" aria-label="Bit está escribiendo"><i></i><i></i><i></i></span>');
  try {
    const [res] = await Promise.all([
      api("/api/assistant", { method: "POST", body: JSON.stringify({ message, view: currentView() }) }),
      sleep(350), // una pausa breve para que se note que «piensa»
    ]);
    bubble.innerHTML = renderMarkdown(res.reply);
    if (res.actions.length) {
      const row = document.createElement("div");
      row.className = "bit-actions";
      for (const a of res.actions) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "btn btn-secondary btn-sm";
        b.innerHTML = `${escapeHtml(a.label)} ${icon(a.ask ? "send" : "arrow-right", "icon icon-inline")}`;
        b.onclick = () => runBitAction(a);
        row.appendChild(b);
      }
      bubble.appendChild(row);
    }
    renderBitSuggestions(res.suggestions);
  } catch (err) {
    bubble.className = "bit-msg bot error";
    bubble.textContent = "Uy, no he podido responder. Inténtalo otra vez.";
  } finally {
    bitBusy = false;
    $("bit-panel").classList.remove("thinking");
    $("bit-messages").scrollTop = $("bit-messages").scrollHeight;
  }
}

async function spotlight(selector) {
  let el = null;
  for (let i = 0; i < 30 && !el; i++) {  // la vista puede tardar un poco en pintarse
    el = document.querySelector(selector);
    if (!el || el.offsetParent === null) { el = null; await sleep(100); }
  }
  if (!el) return;
  el.closest("details")?.setAttribute("open", "");
  if (el.tagName === "DETAILS") el.open = true;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.remove("spotlight");
  void el.offsetWidth;
  el.classList.add("spotlight");
  setTimeout(() => el.classList.remove("spotlight"), 2800);
}

function runBitAction(a) {
  if (a.ask) return askBit(a.ask);
  if (a.auth) {
    if (isMobile()) closeBit();
    return openAuth(a.auth);
  }
  if (isMobile() && (a.goto || a.highlight)) closeBit();
  if (a.goto) navigate(a.goto);
  if (a.highlight) spotlight(a.highlight);
}

function openBit() {
  $("bit-panel").hidden = false;
  $("bit-fab").setAttribute("aria-expanded", "true");
  $("bit-fab").classList.add("open");
  $("bit-bubble").hidden = true;
  storageSet("bit-seen", "1");
  if (!bitStarted) {
    bitStarted = true;
    askBit("", true);
  }
  setTimeout(() => $("bit-input").focus(), 50);
}

function closeBit() {
  $("bit-panel").hidden = true;
  $("bit-fab").setAttribute("aria-expanded", "false");
  $("bit-fab").classList.remove("open");
}

function initBit() {
  document.querySelectorAll("[data-bit]").forEach((el) => (el.innerHTML = BIT_SVG));
  $("bit-fab").onclick = () => ($("bit-panel").hidden ? openBit() : closeBit());
  $("bit-close").onclick = () => { closeBit(); $("bit-fab").focus(); };
  $("bit-form").onsubmit = (e) => {
    e.preventDefault();
    const msg = $("bit-input").value.trim();
    if (!msg || bitBusy) return;
    $("bit-input").value = "";
    askBit(msg);
  };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("bit-panel").hidden && $("auth-modal").hidden) closeBit();
  });
  // La primera visita, Bit se presenta con un bocadillo.
  if (!storageGet("bit-seen")) {
    setTimeout(() => { if (!bitStarted) $("bit-bubble").hidden = false; }, 1500);
    setTimeout(() => ($("bit-bubble").hidden = true), 9000);
  }
  $("bit-bubble").onclick = openBit;
}

// ---------- Arranque ----------

async function reloadAll() {
  await refreshMe();
  [challenges, roomsData] = await Promise.all([api("/api/challenges"), api("/api/rooms")]);
  roomsStale = false;
  renderBadges();
  renderPaths();
  renderChallenges();
  renderLanding();
  await route();
}

function init() {
  hydrateIcons();

  document.querySelectorAll("[data-view]").forEach((b) => (b.onclick = () => navigate(VIEW_HASH[b.dataset.view])));
  document.querySelectorAll("[data-action='register']").forEach((b) => (b.onclick = () => (me ? navigate("#salas") : openAuth("register"))));
  document.querySelectorAll("[data-action='start']").forEach((b) => (b.onclick = () =>
    me ? navigate("#sala/redes") : openAuth("register", () => navigate("#sala/redes"))));

  // Acceso
  $("auth-form").onsubmit = submitAuth;
  $("auth-cancel").onclick = closeAuth;
  $("auth-modal").onmousedown = (e) => { if (e.target === $("auth-modal")) closeAuth(); };
  $("auth-switch").onclick = () => setAuthMode(authMode === "login" ? "register" : "login");
  document.querySelectorAll(".segmented [data-mode]").forEach((b) => (b.onclick = () => setAuthMode(b.dataset.mode)));
  $("pass-toggle").onclick = togglePassword;
  $("auth-pass").oninput = () => { updateStrength(); if ($("f-pass").classList.contains("has-error")) setFieldError("pass", ""); };
  $("auth-user").oninput = () => { if ($("f-user").classList.contains("has-error")) setFieldError("user", ""); };
  $("auth-user").onblur = () => {
    const v = $("auth-user").value.trim();
    if (authMode === "register" && v && !USER_RE.test(v)) setFieldError("user", "Usa entre 3 y 20 caracteres: letras sin tildes, números o _.");
  };
  document.addEventListener("keydown", authKeydown);

  // Nivel del Coach (un único ajuste compartido por las dos fichas)
  document.querySelectorAll(".level-select").forEach((s) => {
    s.value = level();
    s.onchange = () => {
      storageSet("ctf-coach-level", s.value);
      document.querySelectorAll(".level-select").forEach((o) => (o.value = s.value));
    };
  });

  // Retos
  $("flag-form").onsubmit = submitFlag;
  $("gen-form").onsubmit = submitGenerate;
  $("chat-form").onsubmit = (e) => {
    e.preventDefault();
    const msg = $("chat-input").value.trim();
    if (busy || !msg) return;
    $("chat-input").value = "";
    askTutor(msg);
  };
  document.querySelectorAll(".hint-buttons button").forEach((b) => {
    b.onclick = () => {
      if (busy) return;
      const msg = $("chat-input").value.trim();
      $("chat-input").value = "";
      askTutor(msg, Number(b.dataset.hint));
    };
  });
  $("copy").onclick = async () => {
    try { await navigator.clipboard.writeText(current?.data || ""); } catch { return; }
    const label = $("copy").querySelector("span:last-child");
    label.textContent = "Copiado";
    setTimeout(() => (label.textContent = "Copiar"), 1500);
  };
  let anTimer;
  $("an-input").oninput = () => { clearTimeout(anTimer); anTimer = setTimeout(runAnalyzer, 150); };
  $("analyzer").addEventListener("toggle", () => { if ($("analyzer").open && !$("an-results").innerHTML) runAnalyzer(); });
  $("an-reset").onclick = resetAnalyzer;
  $("ch-back").onclick = () => navigate("#retos");

  // Clasificación
  document.querySelectorAll(".lb-period [data-period]").forEach((b) => (b.onclick = () => {
    lbPeriod = b.dataset.period;
    loadLeaderboard();
  }));

  // Roadmap
  document.querySelectorAll(".rm-filter [data-filter]").forEach((b) => (b.onclick = () => {
    roadmapFilter = b.dataset.filter;
    if (roadmapData) renderRoadmap();
  }));

  // Salas
  $("room-back").onclick = () => navigate("#salas");
  $("room-chat-form").onsubmit = askRoomCoach;

  initBit();
  initLanding();
  document.addEventListener("click", (e) => { if (!e.target.closest(".user-menu")) closeUserMenu(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeUserMenu(); });
  window.addEventListener("resize", updateNavIndicator);
  document.fonts?.ready.then(updateNavIndicator);
  const topbar = document.querySelector(".topbar");
  window.addEventListener("scroll", () => topbar.classList.toggle("scrolled", window.scrollY > 8), { passive: true });
  window.addEventListener("hashchange", route);
  reloadAll();
}

init();
