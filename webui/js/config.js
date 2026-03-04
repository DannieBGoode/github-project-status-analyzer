import { state } from "./state.js";
import { byId } from "./utils.js";

function getBrowserTimezoneLabel() {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZoneName: "short",
    }).formatToParts(new Date());
    const tz = parts.find((p) => p.type === "timeZoneName");
    return tz ? tz.value : "";
  } catch (_err) {
    return "";
  }
}

export function updateModelDropdown(provider, preferred = "") {
  const select = byId("model");
  const options = state.modelOptions[provider] || [];
  select.innerHTML = "";
  options.forEach((entry) => {
    const modelName = typeof entry === "string" ? entry : entry.id;
    const modelLabel = typeof entry === "string" ? entry : entry.label;
    const opt = document.createElement("option");
    opt.value = modelName;
    opt.textContent = modelLabel || modelName;
    select.appendChild(opt);
  });
  const ids = options.map((entry) => (typeof entry === "string" ? entry : entry.id));
  if (preferred && ids.includes(preferred)) {
    select.value = preferred;
  } else if (ids.length > 0) {
    select.value = ids[0];
  }
}

export async function loadConfig() {
  const res = await fetch("/api/config");
  const cfg = await res.json();
  state.modelOptions = cfg.model_options || { gemini: [], openai: [] };

  byId("ai_provider").value = cfg.ai_provider || "gemini";
  byId("project_url").value = cfg.project_url || "";
  byId("lookback_days").value = cfg.lookback_days ?? 14;
  byId("max_items").value = cfg.max_items ?? 100;
  byId("max_comments_per_item").value = cfg.max_comments_per_item ?? 20;
  byId("github_token").value = cfg.github_token || "";
  byId("gemini_api_key").value = cfg.gemini_api_key || "";
  byId("openai_api_key").value = cfg.openai_api_key || "";

  const provider = byId("ai_provider").value;
  const preferred = provider === "gemini" ? cfg.gemini_model : cfg.openai_model;
  updateModelDropdown(provider, preferred);
}

export function buildRunPayload() {
  const maxItemsRaw = Number(byId("max_items").value);
  const maxItems = Number.isFinite(maxItemsRaw)
    ? Math.max(1, Math.min(100, maxItemsRaw))
    : 100;
  byId("max_items").value = String(maxItems);

  return {
    ai_provider: byId("ai_provider").value,
    model: byId("model").value,
    project_url: byId("project_url").value.trim(),
    lookback_days: byId("lookback_days").value,
    max_items: String(maxItems),
    max_comments_per_item: byId("max_comments_per_item").value,
    report_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
    report_timezone_label: getBrowserTimezoneLabel(),
    github_token: byId("github_token").value.trim(),
    gemini_api_key: byId("gemini_api_key").value.trim(),
    openai_api_key: byId("openai_api_key").value.trim(),
  };
}
