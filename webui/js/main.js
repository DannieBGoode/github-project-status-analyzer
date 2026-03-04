import { loadConfig, updateModelDropdown, buildRunPayload } from "./config.js";
import { addReportTab, initReportPicker, selectTab } from "./reports.js";
import {
  findInProgressStep,
  initProgress,
  setLoading,
  stopProgressTimer,
  updateProgress,
} from "./progress.js";
import { byId } from "./utils.js";

const THEME_STORAGE_KEY = "webui-theme";
const THEME_ICON_SUN = `
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <circle cx="12" cy="12" r="4.4" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
    <path d="M12 2.5v3M12 18.5v3M21.5 12h-3M5.5 12h-3M18.8 5.2l-2.1 2.1M7.3 16.7l-2.1 2.1M18.8 18.8l-2.1-2.1M7.3 7.3 5.2 5.2" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
  </svg>`;
const THEME_ICON_MOON = `
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      fill="currentColor"
      d="M20.62 15.34A9 9 0 1 1 8.66 3.38a1 1 0 0 1 1.23 1.28 7 7 0 0 0 8.82 8.82 1 1 0 0 1 1.29 1.24Z"
    ></path>
  </svg>`;

function showAppError(message) {
  const el = byId("app-error");
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
}

function getInitialTheme() {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch (_err) {
    // Ignore storage access issues and fall back to system preference.
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  const safeTheme = theme === "dark" ? "dark" : "light";
  document.body.setAttribute("data-theme", safeTheme);
  const toggle = byId("theme-toggle");
  const icon = byId("theme-icon");
  const label = byId("theme-label");
  if (!toggle) return;
  const nextLabel = safeTheme === "dark" ? "Light mode" : "Dark mode";
  if (icon) icon.innerHTML = safeTheme === "dark" ? THEME_ICON_SUN : THEME_ICON_MOON;
  if (label) label.textContent = safeTheme === "dark" ? "Light" : "Dark";
  toggle.setAttribute("aria-label", `Switch to ${nextLabel.toLowerCase()}`);
  toggle.setAttribute("title", `Switch to ${nextLabel.toLowerCase()}`);
}

function persistTheme(theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (_err) {
    // Ignore storage access issues.
  }
}

function playSuccessChime() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;
    const master = ctx.createGain();
    master.gain.setValueAtTime(0.0001, now);
    master.gain.exponentialRampToValueAtTime(0.4, now + 0.012);
    master.gain.exponentialRampToValueAtTime(0.0001, now + 0.85);
    master.connect(ctx.destination);

    const notes = [
      { freq: 880, start: 0.0, dur: 0.13 },
      { freq: 1175, start: 0.16, dur: 0.16 },
    ];
    notes.forEach(({ freq, start, dur }) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, now + start);
      gain.gain.setValueAtTime(0.0001, now + start);
      gain.gain.exponentialRampToValueAtTime(1.35, now + start + 0.016);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + start + dur);
      osc.connect(gain);
      gain.connect(master);
      osc.start(now + start);
      osc.stop(now + start + dur + 0.02);
    });

    setTimeout(() => {
      ctx.close().catch(() => {});
    }, 1200);
  } catch (_err) {
    // Ignore audio failures; report generation remains unaffected.
  }
}

function playErrorChime() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;
    const master = ctx.createGain();
    master.gain.setValueAtTime(0.0001, now);
    master.gain.exponentialRampToValueAtTime(0.45, now + 0.012);
    master.gain.exponentialRampToValueAtTime(0.0001, now + 0.95);
    master.connect(ctx.destination);

    const notes = [
      { freq: 620, start: 0.0, dur: 0.16 },
      { freq: 460, start: 0.2, dur: 0.22 },
    ];
    notes.forEach(({ freq, start, dur }) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, now + start);
      gain.gain.setValueAtTime(0.0001, now + start);
      gain.gain.exponentialRampToValueAtTime(1.45, now + start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + start + dur);
      osc.connect(gain);
      gain.connect(master);
      osc.start(now + start);
      osc.stop(now + start + dur + 0.02);
    });

    setTimeout(() => {
      ctx.close().catch(() => {});
    }, 1300);
  } catch (_err) {
    // Ignore audio failures; report generation remains unaffected.
  }
}

async function runReport(event) {
  if (!event || event.type !== "click" || !event.isTrusted) return;
  event.preventDefault();

  setLoading(true);
  initProgress();
  let hasError = false;

  try {
    const payload = buildRunPayload();
    let res = await fetch("/api/run-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const txt = await res.text();
      throw new Error(txt || `Failed to start report run (HTTP ${res.status}).`);
    }

    if (!res.body || typeof res.body.getReader !== "function") {
      res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Run failed.");
      updateProgress("github_request", "completed", "GitHub request completed.");
      updateProgress("github_response", "completed", "GitHub response received.");
      updateProgress("ai_send", "completed", "Items sent successfully.");
      updateProgress("ai_wait", "completed", "AI response received.");
      updateProgress("markdown_build", "completed", "Markdown report built.");
      addReportTab(data.filename || "report.md", data.markdown || "");
      playSuccessChime();
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let completed = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        const msg = JSON.parse(line);

        if (msg.type === "step" && msg.step) {
          updateProgress(msg.step.step_id, msg.step.status, msg.step.message || "");
        } else if (msg.type === "result" && msg.data) {
          completed = true;
          addReportTab(msg.data.filename || "report.md", msg.data.markdown || "");
          playSuccessChime();
        } else if (msg.type === "error") {
          const failedStep = findInProgressStep() || "ai_wait";
          updateProgress(
            failedStep,
            "failed",
            "Failed",
            msg.error || "Unknown error."
          );
          throw new Error(msg.error || "Run failed.");
        }
      }
    }

    if (!completed) throw new Error("Run ended without result.");
  } catch (err) {
    hasError = true;
    const failedStep = findInProgressStep() || "ai_wait";
    updateProgress(failedStep, "failed", "Failed", err.message);
    playErrorChime();
  } finally {
    stopProgressTimer();
    if (hasError) {
      byId("loading-close").classList.remove("hidden");
      byId("run-btn").disabled = false;
    } else {
      setLoading(false);
    }
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  applyTheme(getInitialTheme());

  byId("report-form").addEventListener("submit", (e) => e.preventDefault());
  byId("run-btn").addEventListener("click", runReport);
  byId("loading-close").addEventListener("click", () => setLoading(false));
  byId("theme-toggle").addEventListener("click", () => {
    const current = document.body.getAttribute("data-theme") === "dark" ? "dark" : "light";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    persistTheme(next);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const loading = byId("loading");
    const closeBtn = byId("loading-close");
    if (!loading || loading.classList.contains("hidden")) return;
    if (closeBtn && !closeBtn.classList.contains("hidden")) {
      setLoading(false);
    }
  });
  byId("ai_provider").addEventListener("change", () => {
    updateModelDropdown(byId("ai_provider").value);
  });
  byId("settings-btn").addEventListener("click", () => {
    selectTab("settings");
  });
  byId("primary-tabs").addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    selectTab(btn.dataset.tab);
  });
  initReportPicker();

  try {
    await loadConfig();
  } catch (_err) {
    showAppError("Failed to load configuration. Check API availability and refresh.");
  }
});
