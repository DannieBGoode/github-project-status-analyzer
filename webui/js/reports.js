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
  const projectNameEntry = metadataMap.get("project name");
  const generatedEntry = metadataMap.get("generated");
  const providerEntry = metadataMap.get("ai provider");
  const totalItemsEntry = metadataMap.get("total items fetched");
  const updatedItemsEntry = metadataMap.get("items updated in lookback window");
  const newCommentsEntry = metadataMap.get("comments created in lookback window");
  const contextParts = [];
  if (generatedEntry) {
    contextParts.push(
      `<span class="meta-part"><span class="meta-icon" aria-hidden="true">&#9684;</span><span>${escapeHtml(
        generatedEntry.value
      )}</span></span>`
    );
  }
  if (providerEntry) {
    contextParts.push(
      `<span class="meta-part"><span class="meta-icon" aria-hidden="true">&#9783;</span><span>${escapeHtml(
        providerEntry.value
      )}</span></span>`
    );
  }

  container.innerHTML = `
    <article class="card report-card">
      <div class="report-toolbar">
        <div class="report-toolbar-main">
          <div class="report-identity">
            <strong>Report ${escapeHtml(activeReport.filename)}</strong>
            ${
              projectNameEntry
                ? `<div class="report-project-line">${
                    projectUrlEntry && /^https?:\/\//i.test(projectUrlEntry.value)
                      ? `<a class="report-meta-project-link" href="${escapeHtml(
                          projectUrlEntry.value
                        )}" target="_blank" rel="noopener noreferrer">${escapeHtml(projectNameEntry.value)}</a>`
                      : `<span>${escapeHtml(projectNameEntry.value)}</span>`
                  }</div>`
                : ""
            }
            ${
              contextParts.length
                ? `<ul class="report-title-meta" aria-label="Report generation context">
                     <li>${contextParts.join('<span class="meta-sep" aria-hidden="true">·</span>')}</li>
                   </ul>`
                : ""
            }
          </div>
          <ul class="report-inline-stats" aria-label="Report activity metrics">
            ${
              totalItemsEntry && updatedItemsEntry
                ? `<li><span class="stats-icon" aria-hidden="true">&#9783;</span><span class="stats-label">Items Fetched:</span> <span class="stats-total">${escapeHtml(
                    totalItemsEntry.value
                  )}</span> / <span class="stats-updated">${escapeHtml(updatedItemsEntry.value)} Updated</span></li>`
                : ""
            }
            ${
              newCommentsEntry
                ? `<li><span class="stats-icon" aria-hidden="true">&#9993;</span><span class="stats-label">New Comments:</span> <span class="stats-comments">${escapeHtml(
                    newCommentsEntry.value
                  )}</span></li>`
                : ""
            }
          </ul>
          <div class="report-actions-inline">
            <button type="button" class="primary" id="report-download-btn">Download .md</button>
          </div>
        </div>
      </div>
      <div class="markdown-shell">
        <button
          type="button"
          class="markdown-copy-btn"
          id="report-copy-btn"
          aria-label="Copy markdown report"
          title="Copy markdown report"
        >
          <svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" focusable="false">
            <path
              fill="currentColor"
              d="M0 6.75C0 5.78.78 5 1.75 5h5.5C8.22 5 9 5.78 9 6.75v7.5C9 15.22 8.22 16 7.25 16h-5.5A1.75 1.75 0 0 1 0 14.25v-7.5Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h5.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25h-5.5Z"
            ></path>
            <path
              fill="currentColor"
              d="M10.75 0A1.75 1.75 0 0 1 12.5 1.75v7.5A1.75 1.75 0 0 1 10.75 11h-.5V9.5h.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25h-5.5a.25.25 0 0 0-.25.25v.5H3.5v-.5A1.75 1.75 0 0 1 5.25 0h5.5Z"
            ></path>
          </svg>
        </button>
        <div class="markdown-render" id="report-render"></div>
      </div>
    </article>
  `;

  byId("report-render").innerHTML = renderMarkdown(activeReport.markdown);

  const copyButton = byId("report-copy-btn");
  const downloadButton = byId("report-download-btn");

  copyButton.addEventListener("click", async () => {
    if (copyButton.dataset.busy === "true") return;
    copyButton.dataset.busy = "true";
    try {
      await navigator.clipboard.writeText(activeReport.markdown);
      copyButton.classList.remove("is-error");
      copyButton.classList.add("is-copied");
      copyButton.setAttribute("aria-label", "Copied");
      copyButton.setAttribute("title", "Copied");
      setTimeout(() => {
        copyButton.classList.remove("is-copied");
        delete copyButton.dataset.busy;
        copyButton.setAttribute("aria-label", "Copy markdown report");
        copyButton.setAttribute("title", "Copy markdown report");
      }, 1500);
    } catch (_err) {
      copyButton.classList.remove("is-copied");
      copyButton.classList.add("is-error");
      copyButton.setAttribute("aria-label", "Copy failed");
      copyButton.setAttribute("title", "Copy failed");
      setTimeout(() => {
        copyButton.classList.remove("is-error");
        delete copyButton.dataset.busy;
        copyButton.setAttribute("aria-label", "Copy markdown report");
        copyButton.setAttribute("title", "Copy markdown report");
      }, 1800);
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
