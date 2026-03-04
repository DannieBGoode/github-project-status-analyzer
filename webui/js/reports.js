import { renderMarkdown } from "./markdown.js";
import { state } from "./state.js";
import { byId, escapeHtml } from "./utils.js";

const REPORT_METADATA_LABELS = [
  "Generated",
  "AI Provider",
  "Project Name",
  "Project URL",
  "Total Items Fetched",
  "Items Updated in Lookback Window",
  "Comments Created in Lookback Window",
];

const REPORT_METADATA_LOOKUP = new Set(REPORT_METADATA_LABELS.map((label) => label.toLowerCase()));
const REPORT_METADATA_ORDER = new Map(REPORT_METADATA_LABELS.map((label, idx) => [label.toLowerCase(), idx]));
const REPORT_METADATA_NUMERIC = new Set([
  "total items fetched",
  "items updated in lookback window",
  "comments created in lookback window",
]);

function normalizeMetadataLine(line) {
  return line.replace(/^[-*]\s+/, "").trim();
}

function parseMetadataLine(line) {
  const normalized = normalizeMetadataLine(line);
  const separatorIndex = normalized.indexOf(":");
  if (separatorIndex < 1) return null;

  const label = normalized.slice(0, separatorIndex).trim();
  const value = normalized.slice(separatorIndex + 1).trim();
  if (!REPORT_METADATA_LOOKUP.has(label.toLowerCase()) || !value) return null;

  return {
    label,
    value: value.replace(/^`(.+)`$/, "$1"),
  };
}

function isExecutiveReportHeading(line) {
  const normalized = line.trim().replace(/^#+\s*/, "");
  return normalized.toLowerCase() === "executive report";
}

export function splitReportContent(markdown) {
  const safeMarkdown = typeof markdown === "string" ? markdown : "";
  if (!safeMarkdown.trim()) {
    return { bodyMarkdown: "", metadata: [] };
  }

  const normalized = safeMarkdown.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  let cursor = 0;
  while (cursor < lines.length && !lines[cursor].trim()) cursor += 1;

  if (cursor >= lines.length || !isExecutiveReportHeading(lines[cursor])) {
    return { bodyMarkdown: normalized, metadata: [] };
  }

  const metadata = [];
  const seenLabels = new Set();
  let index = cursor + 1;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed || trimmed === "---") {
      index += 1;
      continue;
    }

    const parsed = parseMetadataLine(line);
    if (!parsed) break;

    const key = parsed.label.toLowerCase();
    if (!seenLabels.has(key)) {
      metadata.push(parsed);
      seenLabels.add(key);
    }
    index += 1;
  }

  if (!metadata.length) {
    return { bodyMarkdown: normalized, metadata: [] };
  }

  while (index < lines.length && !lines[index].trim()) index += 1;
  const bodyMarkdown = lines.slice(index).join("\n");
  return { bodyMarkdown, metadata };
}

export function getTemporaryButtonState(originalLabel, successLabel, failureLabel, isError) {
  return {
    text: isError ? failureLabel : successLabel,
    disabled: true,
    resetText: originalLabel,
    resetDisabled: false,
    resetAfterMs: isError ? 1800 : 1500,
  };
}

export function selectTab(tabId) {
  document.querySelectorAll("[data-tab]").forEach((el) => {
    const isActive = el.dataset.tab === tabId;
    el.classList.toggle("active", isActive);
    if (el.classList.contains("nav-tab")) {
      el.setAttribute("aria-selected", String(isActive));
      el.setAttribute("tabindex", isActive ? "0" : "-1");
    }
    if (el.classList.contains("utility-btn")) {
      el.setAttribute("aria-pressed", String(isActive));
    }
  });
  document.querySelectorAll(".tab-panel").forEach((el) => {
    const isActive = el.id === `tab-${tabId}`;
    el.classList.toggle("active", isActive);
    el.setAttribute("aria-hidden", String(!isActive));
    el.toggleAttribute("hidden", !isActive);
  });
}

function downloadMarkdown(filename, markdown) {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function getActiveReport() {
  if (!state.reports.length) return null;
  return state.reports.find((report) => report.id === state.activeReportId) || state.reports[state.reports.length - 1];
}

function renderReportPicker() {
  const picker = byId("report-picker");
  if (!picker) return;

  if (!state.reports.length) {
    picker.innerHTML = "";
    picker.disabled = true;
    return;
  }

  picker.disabled = false;
  picker.innerHTML = state.reports
    .map(
      (report) =>
        `<option value="${report.id}">Report ${report.order}: ${escapeHtml(report.filename)}</option>`
    )
    .join("");
  picker.value = state.activeReportId;
}

function renderActiveReport() {
  const container = byId("reports-list");
  const empty = byId("reports-empty");
  const controls = byId("reports-controls");
  if (!container || !empty || !controls) return;

  const activeReport = getActiveReport();
  if (!activeReport) {
    container.innerHTML = "";
    empty.classList.remove("hidden");
    controls.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");
  controls.classList.remove("hidden");
  const orderedMetadata = [...activeReport.metadata].sort(
    (a, b) =>
      (REPORT_METADATA_ORDER.get(a.label.toLowerCase()) ?? Number.MAX_SAFE_INTEGER) -
      (REPORT_METADATA_ORDER.get(b.label.toLowerCase()) ?? Number.MAX_SAFE_INTEGER)
  );
  const metadataMap = new Map(orderedMetadata.map((entry) => [entry.label.toLowerCase(), entry]));
  const projectUrlEntry = metadataMap.get("project url");
  const contextualMetadata = ["generated", "ai provider", "project name"]
    .map((key) => metadataMap.get(key))
    .filter(Boolean);
  if (!metadataMap.get("project name") && projectUrlEntry) {
    contextualMetadata.push({ label: "Project", value: projectUrlEntry.value });
  }
  const metricMetadata = orderedMetadata.filter(({ label }) => REPORT_METADATA_NUMERIC.has(label.toLowerCase()));

  container.innerHTML = `
    <article class="card report-card">
      <div class="report-toolbar">
        <div>
          <strong>Report ${activeReport.order}: ${escapeHtml(activeReport.filename)}</strong>
        </div>
      </div>
      ${
        orderedMetadata.length
          ? `<section class="report-metadata" aria-label="Report metadata">
               <h3>Report metadata</h3>
               <dl class="report-metadata-facts">
                   ${contextualMetadata
                     .map(({ label, value }) => {
                      const lowerLabel = label.toLowerCase();
                      const linkProjectName =
                        lowerLabel === "project name" &&
                        projectUrlEntry &&
                        /^https?:\/\//i.test(projectUrlEntry.value);
                      const safeValue = escapeHtml(value);
                       const valueHtml = linkProjectName
                         ? `<a class="report-meta-project-link" href="${escapeHtml(
                             projectUrlEntry.value
                           )}" target="_blank" rel="noopener noreferrer">${safeValue}</a>`
                        : /^https?:\/\//i.test(value)
                          ? `<a href="${safeValue}" target="_blank" rel="noopener noreferrer">${safeValue}</a>`
                          : `<span>${safeValue}</span>`;
                       return `<div class="report-meta-fact"><dt>${escapeHtml(label)}</dt><dd>${valueHtml}</dd></div>`;
                     })
                     .join("")}
                </dl>
                ${
                  metricMetadata.length
                    ? `<dl class="report-metadata-kpis">
                  ${metricMetadata
                     .map(({ label, value }) => {
                      const safeValue = escapeHtml(value);
                      return `<div class="report-kpi"><dt>${escapeHtml(label)}</dt><dd>${safeValue}</dd></div>`;
                     })
                     .join("")}
                </dl>`
                    : ""
                }
             </section>`
          : ""
      }
      <section class="report-export-toolbar" aria-label="Markdown report export">
        <div class="report-export-copy">
          <h3>Markdown report</h3>
          <p>Copy or download the body exactly as shown below.</p>
        </div>
        <div class="actions">
          <button type="button" class="ghost" id="report-copy-btn">Copy</button>
          <button type="button" class="secondary" id="report-download-btn">Download .md</button>
        </div>
      </section>
      <div class="markdown-render" id="report-render"></div>
    </article>
  `;

  byId("report-render").innerHTML = renderMarkdown(activeReport.markdown);

  const copyButton = byId("report-copy-btn");
  const downloadButton = byId("report-download-btn");

  copyButton.addEventListener("click", async () => {
    const original = copyButton.textContent;
    try {
      await navigator.clipboard.writeText(activeReport.markdown);
      const temp = getTemporaryButtonState(original, "Copied", "Copy failed", false);
      copyButton.textContent = temp.text;
      copyButton.disabled = temp.disabled;
      setTimeout(() => {
        copyButton.textContent = temp.resetText;
        copyButton.disabled = temp.resetDisabled;
      }, temp.resetAfterMs);
    } catch (_err) {
      const temp = getTemporaryButtonState(original, "Copied", "Copy failed", true);
      copyButton.textContent = temp.text;
      copyButton.disabled = temp.disabled;
      setTimeout(() => {
        copyButton.textContent = temp.resetText;
        copyButton.disabled = temp.resetDisabled;
      }, temp.resetAfterMs);
    }
  });

  downloadButton.addEventListener("click", () => {
    downloadMarkdown(activeReport.filename, activeReport.markdown);
  });
}

export function addReportTab(filename, markdown) {
  const { bodyMarkdown, metadata } = splitReportContent(markdown);
  state.reportCounter += 1;
  const id = `report-${state.reportCounter}`;
  state.reports.push({ id, order: state.reportCounter, filename, markdown: bodyMarkdown, metadata });
  state.activeReportId = id;
  renderReportPicker();
  renderActiveReport();

  selectTab("reports");
}

export function initReportPicker() {
  const picker = byId("report-picker");
  if (!picker) return;
  picker.addEventListener("change", (event) => {
    state.activeReportId = event.target.value;
    renderActiveReport();
  });
  renderReportPicker();
  renderActiveReport();
}
