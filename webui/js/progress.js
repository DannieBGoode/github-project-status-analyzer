import { progressSteps } from "./constants.js";
import { state } from "./state.js";
import { byId, formatDuration } from "./utils.js";

export function setLoading(isLoading) {
  const loading = byId("loading");
  const loadingPanel = byId("loading-panel");
  loading.classList.toggle("hidden", !isLoading);
  loading.setAttribute("aria-hidden", String(!isLoading));
  byId("run-btn").disabled = isLoading;
  byId("loading-close").classList.add("hidden");
  byId("loading-close").disabled = !isLoading;

  if (isLoading) {
    state.lastFocusedElement = document.activeElement;
    if (loadingPanel) loadingPanel.focus();
  } else if (
    state.lastFocusedElement &&
    typeof state.lastFocusedElement.focus === "function"
  ) {
    state.lastFocusedElement.focus();
    state.lastFocusedElement = null;
  }
}

function ensureProgressTimer() {
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerInterval = setInterval(() => {
    for (const step of progressSteps) {
      const p = state.progress[step.id];
      if (!p || p.status !== "in_progress" || !p.startedAt) continue;
      const elapsed = Date.now() - p.startedAt;
      const timer = byId(`step-time-${step.id}`);
      if (timer) timer.textContent = `Time Spent: ${formatDuration(elapsed)}`;
    }
  }, 300);
}

export function stopProgressTimer() {
  if (state.timerInterval) {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }
}

export function initProgress() {
  const list = byId("progress-list");
  list.innerHTML = "";
  state.progress = {};

  for (const step of progressSteps) {
    state.progress[step.id] = {
      status: "pending",
      startedAt: null,
      elapsedMs: 0,
      message: "Pending",
      error: "",
    };
    const li = document.createElement("li");
    li.id = `step-${step.id}`;
    li.className = "progress-item pending";
    li.innerHTML = `
      <div class="progress-main">
        <span id="step-icon-${step.id}" class="progress-icon pending"></span>
        <div class="progress-content">
          <span class="progress-label">${step.label}</span>
          <span id="step-msg-${step.id}" class="progress-message">Pending</span>
        </div>
        <span id="step-time-${step.id}" class="progress-time">Time Spent: 0:00</span>
      </div>
    `;
    list.appendChild(li);
  }
  ensureProgressTimer();
}

export function updateProgress(stepId, status, message, errorText = "") {
  const item = byId(`step-${stepId}`);
  const icon = byId(`step-icon-${stepId}`);
  const msg = byId(`step-msg-${stepId}`);
  const timer = byId(`step-time-${stepId}`);
  if (!item || !icon || !msg || !timer) return;

  const p = state.progress[stepId] || {
    status: "pending",
    startedAt: null,
    elapsedMs: 0,
    message: "Pending",
    error: "",
  };

  if (status === "in_progress" && !p.startedAt) {
    p.startedAt = Date.now();
    p.elapsedMs = 0;
  }
  if ((status === "completed" || status === "failed") && p.startedAt) {
    p.elapsedMs = Date.now() - p.startedAt;
    p.startedAt = null;
  }

  p.status = status;
  p.message = message || p.message;
  p.error = errorText || "";
  state.progress[stepId] = p;

  item.classList.remove("pending", "in_progress", "completed", "failed");
  item.classList.add(status);
  icon.classList.remove("pending", "in_progress", "completed", "failed");
  icon.classList.add(status);
  if (status === "completed") {
    icon.textContent = "\u2713";
  } else if (status === "failed") {
    icon.textContent = "!";
  } else {
    icon.textContent = "";
  }
  msg.textContent = p.message;
  timer.textContent = `Time Spent: ${formatDuration(
    p.startedAt ? Date.now() - p.startedAt : p.elapsedMs
  )}`;

  const previousErr = item.querySelector(".progress-error");
  if (previousErr) previousErr.remove();
  if (p.error) {
    const e = document.createElement("span");
    e.className = "progress-error";
    e.textContent = p.error;
    item.appendChild(e);
  }
}

export function findInProgressStep() {
  for (const step of progressSteps) {
    const el = byId(`step-${step.id}`);
    if (el && el.classList.contains("in_progress")) return step.id;
  }
  return null;
}
