import { progressSteps } from "./constants.js";
import { state } from "./state.js";
import { byId, formatDuration } from "./utils.js";

const FAB_CHECK_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
const FAB_ERROR_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor"><rect x="10.5" y="4" width="3" height="11" rx="1.5"/><circle cx="12" cy="20" r="1.75"/></svg>`;

const STEP_STATUSES = ["pending", "in_progress", "completed", "failed"];

let lastFabStatus = "in_progress";

function createDefaultStepState() {
  return {
    status: "pending",
    startedAt: null,
    elapsedMs: 0,
    message: "Pending",
    error: "",
  };
}

function applyStatusClass(el, status) {
  if (!el) return;
  el.classList.remove(...STEP_STATUSES);
  el.classList.add(status);
}

function resolveStepIcon(status) {
  if (status === "completed") return "\u2713";
  if (status === "failed") return "!";
  return "";
}

export function evolveProgressState(previous, status, message, errorText = "", now = Date.now()) {
  const p = previous ? { ...previous } : createDefaultStepState();
  if (status === "in_progress" && !p.startedAt) {
    p.startedAt = now;
    p.elapsedMs = 0;
  }
  if ((status === "completed" || status === "failed") && p.startedAt) {
    p.elapsedMs = now - p.startedAt;
    p.startedAt = null;
  }

  p.status = status;
  p.message = message || p.message;
  p.error = errorText || "";
  return p;
}

export function setLoading(isLoading) {
  const loading = byId("loading");
  const loadingPanel = byId("loading-panel");
  loading.classList.toggle("hidden", !isLoading);
  loading.classList.remove("minimized");
  loading.setAttribute("aria-hidden", String(!isLoading));
  byId("run-btn").disabled = isLoading;
  byId("loading-close").classList.add("hidden");
  byId("loading-close").disabled = !isLoading;

  if (!isLoading) {
    const fab = byId("progress-fab");
    if (fab) {
      fab.classList.add("hidden");
      fab.classList.remove("is-active", "is-success", "is-error");
      const dismiss = byId("progress-fab-dismiss");
      if (dismiss) dismiss.classList.add("hidden");
    }
    const goToReport = byId("loading-go-to-report");
    if (goToReport) goToReport.classList.add("hidden");
    const minimizeBtn = byId("loading-minimize");
    if (minimizeBtn) minimizeBtn.classList.remove("hidden");
  }

  if (isLoading) {
    const fab = byId("progress-fab");
    if (fab) {
      fab.classList.add("hidden");
      fab.classList.remove("is-active", "is-success", "is-error");
      const dismiss = byId("progress-fab-dismiss");
      if (dismiss) dismiss.classList.add("hidden");
    }
    lastFabStatus = "in_progress";
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

export function minimizeProgress() {
  const loading = byId("loading");
  const fab = byId("progress-fab");
  if (!loading || !fab) return;
  loading.classList.add("minimized");
  fab.classList.remove("hidden");
  updateFabState(lastFabStatus);
}

export function expandProgress() {
  const loading = byId("loading");
  const fab = byId("progress-fab");
  const loadingPanel = byId("loading-panel");
  if (!loading || !fab) return;
  loading.classList.remove("minimized");
  fab.classList.add("hidden");
  if (loadingPanel) loadingPanel.focus();
}

export function updateFabState(status) {
  lastFabStatus = status;
  const fab = byId("progress-fab");
  const expandBtn = byId("progress-fab-expand");
  const dismissBtn = byId("progress-fab-dismiss");
  if (!fab || !expandBtn) return;

  fab.classList.remove("is-active", "is-success", "is-error");

  if (status === "in_progress") {
    fab.classList.add("is-active");
    expandBtn.innerHTML = "";
    expandBtn.setAttribute("aria-label", "Show progress");
    if (dismissBtn) dismissBtn.classList.add("hidden");
  } else if (status === "completed") {
    fab.classList.add("is-success");
    expandBtn.innerHTML = FAB_CHECK_SVG;
    expandBtn.setAttribute("aria-label", "Show completed report");
    if (dismissBtn) dismissBtn.classList.remove("hidden");
  } else if (status === "failed") {
    fab.classList.add("is-error");
    expandBtn.innerHTML = FAB_ERROR_SVG;
    expandBtn.setAttribute("aria-label", "Show error details");
    if (dismissBtn) dismissBtn.classList.remove("hidden");
  }
}

export function showProgressSnapshot(htmlSnapshot) {
  const loading = byId("loading");
  const loadingPanel = byId("loading-panel");
  const progressList = byId("progress-list");
  const minimizeBtn = byId("loading-minimize");
  const closeBtn = byId("loading-close");
  const goToReportBtn = byId("loading-go-to-report");

  if (progressList) progressList.innerHTML = htmlSnapshot || "";
  if (minimizeBtn) minimizeBtn.classList.add("hidden");
  if (goToReportBtn) goToReportBtn.classList.add("hidden");
  if (closeBtn) {
    closeBtn.classList.remove("hidden");
    closeBtn.disabled = false;
  }

  if (loading) {
    loading.classList.remove("hidden");
    loading.classList.remove("minimized");
    loading.setAttribute("aria-hidden", "false");
  }

  const fab = byId("progress-fab");
  if (fab) fab.classList.add("hidden");

  state.lastFocusedElement = document.activeElement;
  if (loadingPanel) loadingPanel.focus();
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
    state.progress[step.id] = createDefaultStepState();
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

  const p = evolveProgressState(state.progress[stepId], status, message, errorText);
  state.progress[stepId] = p;

  applyStatusClass(item, status);
  applyStatusClass(icon, status);
  icon.textContent = resolveStepIcon(status);
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

  if (status === "completed") {
    const allDone = progressSteps.every((step) => {
      const s = state.progress[step.id];
      return s && s.status === "completed";
    });
    if (allDone) {
      const panel = byId("loading-panel");
      if (panel) {
        panel.classList.remove("all-done");
        void panel.offsetWidth;
        panel.classList.add("all-done");
      }
      updateFabState("completed");
    }
  }

  if (status === "failed") {
    updateFabState("failed");
  }
}

export function findInProgressStep() {
  for (const step of progressSteps) {
    const el = byId(`step-${step.id}`);
    if (el && el.classList.contains("in_progress")) return step.id;
  }
  return null;
}
