import { loadConfig, updateModelDropdown, buildRunPayload } from "./config.js";
import { addReportTab, selectTab } from "./reports.js";
import {
  findInProgressStep,
  initProgress,
  setLoading,
  stopProgressTimer,
  updateProgress,
} from "./progress.js";
import { byId } from "./utils.js";

const THEME_STORAGE_KEY = "webui-theme";

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
  if (icon) icon.textContent = safeTheme === "dark" ? "\u2600" : "\u263E";
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

  try {
    await loadConfig();
  } catch (_err) {
    showAppError("Failed to load configuration. Check API availability and refresh.");
  }
});
