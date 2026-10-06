const $ = (s) => document.querySelector(s);
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `${r.status} ${r.statusText}`);
  }
  return r.json();
};

const todayId = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const prettyDate = (id) =>
  new Date(id + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

const player = $("#player");
let current = null; // episode currently loaded
let lineStarts = []; // estimated start fraction per line

// ---------- episodes ----------

async function loadArchive() {
  const eps = await api("/api/shows");
  const ul = $("#archive");
  ul.innerHTML = eps.length ? "" : '<li class="muted">No episodes yet.</li>';
  for (const ep of eps) {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.innerHTML = `<span></span><span class="d">${ep.id}</span>`;
    b.firstChild.textContent = ep.title;
    b.onclick = () => loadEpisode(ep.id, true);
    li.append(b);
    ul.append(li);
  }
  return eps;
}

async function loadEpisode(id, autoplay = false) {
  const ep = await api(`/api/shows/${id}`);
  current = ep;
  $("#today").textContent = prettyDate(ep.id);
  $("#title").textContent = ep.title;
  $("#tuneLabel").textContent = ep.id === todayId() ? "Re-record today's show" : "Record today's show";
  player.src = `/audio/${ep.id}.wav?t=${encodeURIComponent(ep.created)}`;
  player.hidden = false;
  renderTranscript(ep);
  setNeedle(ep.id);
  if (autoplay) player.play().catch(() => {});
}

function renderTranscript(ep) {
  const box = $("#transcript");
  box.innerHTML = "";
  const firstHost = ep.hosts[0].name;
  // Audio has no word timings, so estimate each line's position by its share of the characters.
  const lens = ep.lines.map((l) => l.line.length + 12);
  const total = lens.reduce((a, b) => a + b, 0);
  let acc = 0;
  lineStarts = lens.map((n) => { const s = acc / total; acc += n; return s; });

  ep.lines.forEach((l, i) => {
    const div = document.createElement("div");
    div.className = "line";
    div.innerHTML = `<span class="style"></span><span class="who"></span><span class="text"></span>`;
    div.querySelector(".style").textContent = l.style;
    const who = div.querySelector(".who");
    who.textContent = l.speaker;
    if (l.speaker === firstHost) who.classList.add("h1");
    div.querySelector(".text").textContent = l.line;
    div.onclick = () => {
      if (player.duration) { player.currentTime = lineStarts[i] * player.duration; player.play(); }
    };
    box.append(div);
  });
  $("#transcriptWrap").hidden = false;
}

player.addEventListener("timeupdate", () => {
  if (!player.duration || !lineStarts.length) return;
  const frac = player.currentTime / player.duration;
  let idx = 0;
  while (idx + 1 < lineStarts.length && lineStarts[idx + 1] <= frac) idx++;
  const lines = document.querySelectorAll("#transcript .line");
  lines.forEach((el, i) => el.classList.toggle("active", i === idx));
  const el = lines[idx];
  if (el && !player.paused) {
    const box = $("#transcript");
    const top = el.offsetTop - box.offsetTop - box.clientHeight / 3;
    if (Math.abs(box.scrollTop - top) > 40) box.scrollTop = top;
  }
});
player.addEventListener("play", () => $("#onair").classList.add("live"));
player.addEventListener("pause", () => $("#onair").classList.remove("live"));
player.addEventListener("ended", () => $("#onair").classList.remove("live"));

function setNeedle(id) {
  // Each day gets its own "frequency" on the dial.
  const day = Number(id.slice(-2)) || 1;
  $("#needle").style.left = `${8 + ((day * 37) % 82)}%`;
}

// ---------- generation ----------

async function tuneIn() {
  $("#error").hidden = true;
  try {
    await api("/api/shows/generate", { method: "POST" });
  } catch (e) {
    if (!String(e.message).includes("already")) return showError(e.message);
  }
  setBusy(true);
  poll();
}

async function poll() {
  const s = await api("/api/status").catch(() => null);
  if (!s) return setTimeout(poll, 2000);
  updateSteps(s.step);
  if (s.state === "running") return setTimeout(poll, 1500);
  setBusy(false);
  if (s.state === "error") return showError(s.error);
  if (s.state === "done" && s.episode) {
    await loadArchive();
    await loadEpisode(s.episode, true);
  }
}

function updateSteps(step) {
  const items = [...document.querySelectorAll("#steps li")];
  const at = items.findIndex((li) => step && step.startsWith(li.dataset.step));
  items.forEach((li, i) => {
    li.classList.toggle("active", i === at);
    li.classList.toggle("done", at > i || step === "On air!");
  });
}

function setBusy(busy) {
  $("#tuneIn").disabled = busy;
  $("#steps").hidden = !busy;
  $(".dial").classList.toggle("scanning", busy);
  if (busy) {
    $("#tuneLabel").textContent = "Producing your show…";
    player.pause();
  }
}

function showError(msg) {
  $("#error").textContent = `Dead air: ${msg}`;
  $("#error").hidden = false;
  $("#tuneLabel").textContent = "Try again";
}

$("#tuneIn").onclick = tuneIn;

// ---------- settings ----------

const dlg = $("#settings");
const form = $("#settingsForm");
let cfg = null;

$("#openSettings").onclick = async () => {
  const { config, voices, custom_voices: customVoices } = await api("/api/config");
  cfg = config;
  $("#settingsError").hidden = true;
  for (const key of ["listener_name", "city", "temperature_unit", "ical_url"]) form.elements[key].value = cfg[key] ?? "";
  form.elements.show_minutes.value = String(cfg.show_minutes ?? 3);
  form.elements.headlines_per_topic.value = String(cfg.headlines_per_topic ?? 3);
  form.elements.news_topics.value = (cfg.news_topics || []).join(", ");
  $("#coords").textContent = `${cfg.latitude}, ${cfg.longitude}`;
  document.querySelectorAll(".host").forEach((el, i) => {
    const h = cfg.hosts[i];
    el.querySelector(".h-name").value = h.name;
    el.querySelector(".h-persona").value = h.persona;
    fillVoiceSelect(el, voices, customVoices, h.voice);
  });
  dlg.showModal();
};

const CUSTOM_ID = "__custom__";

function fillVoiceSelect(el, voices, customVoices, current) {
  const sel = el.querySelector(".h-voice");
  const input = el.querySelector(".h-custom");
  sel.innerHTML = "";
  const group = (label, items) => {
    const g = document.createElement("optgroup");
    g.label = label;
    for (const [value, text] of items) g.append(new Option(text, value));
    sel.append(g);
  };
  group("Built-in voices", voices.map((v) => [v, v]));
  if (customVoices.length) {
    group("My AI Studio voices", customVoices.map((v) => [v.id, `${v.name} (${v.type === "replicated" ? "cloned" : "designed"})`]));
  }
  group("Other", [[CUSTOM_ID, "Paste a voice ID…"]]);

  const known = [...sel.options].some((o) => o.value === current);
  sel.value = known ? current : CUSTOM_ID;
  input.value = known ? "" : current;
  input.hidden = sel.value !== CUSTOM_ID;
  input.required = !input.hidden;
  sel.onchange = () => {
    input.hidden = sel.value !== CUSTOM_ID;
    input.required = !input.hidden;
    if (!input.hidden) input.focus();
  };
}

function selectedVoice(el) {
  const v = el.querySelector(".h-voice").value;
  return v === CUSTOM_ID ? el.querySelector(".h-custom").value.trim() : v;
}

$("#findCity").onclick = async () => {
  const name = form.elements.city.value.trim();
  if (!name) return;
  $("#coords").textContent = "Searching…";
  const r = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(name)}&count=1`);
  const hit = (await r.json()).results?.[0];
  if (!hit) return ($("#coords").textContent = "City not found");
  cfg.latitude = hit.latitude;
  cfg.longitude = hit.longitude;
  form.elements.city.value = hit.name;
  $("#coords").textContent = `${hit.name}, ${hit.admin1 || ""} ${hit.country || ""} (${hit.latitude.toFixed(2)}, ${hit.longitude.toFixed(2)})`;
};

form.addEventListener("submit", async (e) => {
  if (e.submitter?.value === "cancel") return;
  e.preventDefault();
  const f = form.elements;
  if (f.city.value.trim() !== cfg.city) await const CUSTOM_ID = "__custom__";

function fillVoiceSelect(el, voices, customVoices, current) {
  const sel = el.querySelector(".h-voice");
  const input = el.querySelector(".h-custom");
  sel.innerHTML = "";
  const group = (label, items) => {
    const g = document.createElement("optgroup");
    g.label = label;
    for (const [value, text] of items) g.append(new Option(text, value));
    sel.append(g);
  };
  group("Built-in voices", voices.map((v) => [v, v]));
  if (customVoices.length) {
    group("My AI Studio voices", customVoices.map((v) => [v.id, `${v.name} (${v.type === "replicated" ? "cloned" : "designed"})`]));
  }
  group("Other", [[CUSTOM_ID, "Paste a voice ID…"]]);

  const known = [...sel.options].some((o) => o.value === current);
  sel.value = known ? current : CUSTOM_ID;
  input.value = known ? "" : current;
  input.hidden = sel.value !== CUSTOM_ID;
  input.required = !input.hidden;
  sel.onchange = () => {
    input.hidden = sel.value !== CUSTOM_ID;
    input.required = !input.hidden;
    if (!input.hidden) input.focus();
  };
}

function selectedVoice(el) {
  const v = el.querySelector(".h-voice").value;
  return v === CUSTOM_ID ? el.querySelector(".h-custom").value.trim() : v;
}

$("#findCity").onclick();
  const next = {
    ...cfg,
    listener_name: f.listener_name.value.trim(),
    city: f.city.value.trim(),
    temperature_unit: f.temperature_unit.value,
    ical_url: f.ical_url.value.trim(),
    show_minutes: Number(f.show_minutes.value),
    headlines_per_topic: Number(f.headlines_per_topic.value),
    news_topics: f.news_topics.value.split(",").map((s) => s.trim()).filter(Boolean),
    hosts: [...document.querySelectorAll(".host")].map((el) => ({
      name: el.querySelector(".h-name").value.trim(),
      voice: selectedVoice(el),
      persona: el.querySelector(".h-persona").value.trim(),
    })),
  };
  try {
    await api("/api/config", { method: "PUT", body: JSON.stringify(next) });
    dlg.close();
  } catch (err) {
    $("#settingsError").textContent = err.message;
    $("#settingsError").hidden = false;
  }
});

// ---------- boot ----------

(async () => {
  $("#today").textContent = prettyDate(todayId());
  setNeedle(todayId());
  const eps = await loadArchive();
  const s = await api("/api/status");
  if (s.state === "running") { setBusy(true); poll(); }
  else if (eps.length) await loadEpisode(eps[0].id);
})();
