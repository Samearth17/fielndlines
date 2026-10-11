"use strict";

const STORAGE_KEY = "fieldlens-journal-v1";
const $ = (selector) => document.querySelector(selector);
let currentMission = null;
let timerInterval = null;

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => { toast.hidden = true; }, 2800);
}

async function updateModelStatus() {
  const status = $("#model-state");
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("status unavailable");
    const body = await response.json();
    const model = body.model;
    const labels = {disabled: "Fallback-only mode", not_loaded: "Local AI ready to load",
      loading: "Loading local AI", ready: "Local AI cached", error: "Fallback available"};
    status.className = "model-state " + (model.state === "ready" ? "ready" : model.state === "error" ? "error" : "");
    status.querySelector("strong").textContent = labels[model.state] || "Local status";
    status.title = model.last_error || model.name + " · " + model.state;
  } catch {
    status.className = "model-state error";
    status.querySelector("strong").textContent = "Offline fallback";
  }
}

function selected(name) {
  return [...document.querySelectorAll('input[name="' + name + '"]:checked')].map((item) => item.value);
}

$("#mission-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = $("#form-error");
  const interests = selected("interests");
  if (!interests.length) {
    error.textContent = "Choose at least one interest for your mission.";
    error.hidden = false;
    document.querySelector('input[name="interests"]').focus();
    return;
  }
  error.hidden = true;
  const button = $("#generate-button");
  button.disabled = true;
  button.classList.add("loading");
  button.querySelector(".button-text").textContent = "Growing your mission…";
  try {
    const response = await fetch("/api/missions/generate", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({duration: Number(selected("duration")[0]),
        environment: selected("environment")[0], interests}),
    });
    const body = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(body.detail) ? body.detail[0].msg : body.detail;
      throw new Error(detail || "Mission generation failed.");
    }
    currentMission = body;
    renderMission(body);
    updateModelStatus();
  } catch (err) {
    error.textContent = err.message || "FieldLens could not create a mission. Please try again.";
    error.hidden = false;
  } finally {
    button.disabled = false;
    button.classList.remove("loading");
    button.querySelector(".button-text").textContent = "Create my field mission";
  }
});

function fillList(selector, items) {
  const nodes = items.map((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    return li;
  });
  $(selector).replaceChildren(...nodes);
}

function renderMission(mission) {
  $("#mission-source").textContent = mission.source === "local_model"
    ? "Created by local model" : "Curated fallback · not AI-generated";
  $("#mission-title").textContent = mission.title;
  $("#mission-duration").textContent = mission.duration;
  $("#mission-environment").textContent = mission.environment;
  $("#mission-difficulty").textContent = mission.difficulty;
  $("#mission-interests").textContent = mission.interests.join(" · ");
  fillList("#mission-steps", mission.instructions);
  fillList("#mission-safety", mission.safety_notes);
  $("#entry-mission").value = mission.title;
  const output = $("#mission-output");
  output.hidden = false;
  output.scrollIntoView({behavior: "smooth", block: "start"});
}

$("#new-mission").addEventListener("click", () => {
  $("#mission-builder").scrollIntoView({behavior: "smooth"});
});

$("#start-mission").addEventListener("click", () => {
  if (!currentMission) return;
  $("#screen-free-copy").textContent = currentMission.title
    + " is ready. Pocket your phone, stay on permitted paths, and let attention do the work.";
  let seconds = currentMission.duration * 60;
  const renderTimer = () => {
    const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
    const remainder = (seconds % 60).toString().padStart(2, "0");
    $("#timer").textContent = minutes + ":" + remainder;
  };
  renderTimer();
  window.clearInterval(timerInterval);
  timerInterval = window.setInterval(() => {
    seconds = Math.max(0, seconds - 1);
    renderTimer();
    if (!seconds) {
      window.clearInterval(timerInterval);
      showToast("Mission time complete. Return when you are ready.");
    }
  }, 1000);
  $("#screen-free").hidden = false;
  document.body.style.overflow = "hidden";
  $("#complete-mission").focus();
});

function closeScreenFree(completed) {
  window.clearInterval(timerInterval);
  $("#screen-free").hidden = true;
  document.body.style.overflow = "";
  if (completed) {
    $("#journal").scrollIntoView({behavior: "smooth"});
    $("#entry-title").focus();
    showToast("Mission complete — capture one thing you noticed.");
  } else {
    $("#start-mission").focus();
  }
}
$("#complete-mission").addEventListener("click", () => closeScreenFree(true));
$("#exit-screen-free").addEventListener("click", () => closeScreenFree(false));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("#screen-free").hidden) closeScreenFree(false);
});

function readEntries() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(data) ? data : [];
  } catch {
    showToast("Saved journal data could not be read.");
    return [];
  }
}
function saveEntries(entries) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

function renderEntries() {
  const entries = readEntries();
  const list = $("#entries-list");
  list.replaceChildren();
  $("#journal-empty").hidden = entries.length > 0;
  $("#entry-count").textContent = entries.length + " " + (entries.length === 1 ? "entry" : "entries");
  entries.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).forEach((entry) => {
    const article = document.createElement("article");
    article.className = "entry-card";
    const meta = document.createElement("div");
    meta.className = "entry-meta";
    meta.textContent = new Date(entry.createdAt).toLocaleString()
      + (entry.mission ? " · " + entry.mission : "");
    const title = document.createElement("h4");
    title.textContent = entry.title;
    const notes = document.createElement("p");
    notes.textContent = entry.notes;
    const actions = document.createElement("div");
    actions.className = "entry-actions";
    [["Edit", "edit"], ["Delete", "delete"]].forEach(([label, action]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.dataset.action = action;
      button.dataset.id = entry.id;
      button.className = action;
      actions.appendChild(button);
    });
    article.append(meta, title, notes, actions);
    list.appendChild(article);
  });
}

$("#journal-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const title = $("#entry-title").value.trim();
  const notes = $("#entry-notes").value.trim();
  const error = $("#journal-error");
  if (!title || !notes) {
    error.textContent = "Add both a title and field notes before saving.";
    error.hidden = false;
    (!title ? $("#entry-title") : $("#entry-notes")).focus();
    return;
  }
  error.hidden = true;
  const entries = readEntries();
  const id = $("#entry-id").value;
  const now = new Date().toISOString();
  const record = {id: id || crypto.randomUUID(), title, notes,
    mission: $("#entry-mission").value.trim(), createdAt: now, updatedAt: now};
  const existing = entries.findIndex((entry) => entry.id === id);
  if (existing >= 0) record.createdAt = entries[existing].createdAt;
  if (existing >= 0) entries[existing] = record; else entries.push(record);
  try {
    saveEntries(entries);
    resetJournalForm();
    renderEntries();
    showToast(existing >= 0 ? "Observation updated." : "Observation saved in this browser.");
  } catch {
    error.textContent = "This browser could not save the entry. Local storage may be full or unavailable.";
    error.hidden = false;
  }
});

$("#entries-list").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const entries = readEntries();
  const entry = entries.find((item) => item.id === button.dataset.id);
  if (!entry) return;
  if (button.dataset.action === "edit") {
    $("#entry-id").value = entry.id;
    $("#entry-title").value = entry.title;
    $("#entry-notes").value = entry.notes;
    $("#entry-mission").value = entry.mission || "";
    $("#save-label").textContent = "Update observation";
    $("#cancel-edit").hidden = false;
    $("#entry-title").focus();
  } else if (window.confirm("Delete this observation from this browser?")) {
    saveEntries(entries.filter((item) => item.id !== entry.id));
    renderEntries();
    showToast("Observation deleted.");
  }
});

function resetJournalForm() {
  $("#journal-form").reset();
  $("#entry-id").value = "";
  $("#save-label").textContent = "Save observation";
  $("#cancel-edit").hidden = true;
  $("#journal-error").hidden = true;
  if (currentMission) $("#entry-mission").value = currentMission.title;
}
$("#cancel-edit").addEventListener("click", resetJournalForm);

updateModelStatus();
renderEntries();
