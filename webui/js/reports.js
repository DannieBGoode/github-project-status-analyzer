import { renderMarkdown } from "./markdown.js";
import { state } from "./state.js";
import { byId, escapeHtml } from "./utils.js";
import { showProgressSnapshot } from "./progress.js";

const CALENDAR_ICON = `
<svg class="inline-icon" aria-hidden="true" viewBox="0 0 16 16" focusable="false">
  <rect x="2.25" y="3.25" width="11.5" height="10.5" rx="1.75" ry="1.75" fill="none" stroke="currentColor" stroke-width="1.5"></rect>
  <path d="M4.75 1.75v3M11.25 1.75v3M2.75 6.25h10.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path>
</svg>`;

const MODEL_ICON = `
<svg class="inline-icon" aria-hidden="true" viewBox="0 0 16 16" focusable="false">
  <path d="M8 1.5 9.2 6.8 14.5 8 9.2 9.2 8 14.5 6.8 9.2 1.5 8 6.8 6.8Z" fill="currentColor" opacity="0.85"></path>
</svg>`;

const FETCHED_ICON = `
<svg class="inline-icon" aria-hidden="true" viewBox="0 0 16 16" focusable="false">
  <path d="M2.75 3.75h10.5M2.75 8h10.5M2.75 12.25h10.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path>
</svg>`;

const COMMENTS_ICON = `
<svg class="inline-icon" aria-hidden="true" viewBox="0 0 16 16" focusable="false">
  <path d="M3.5 3.25h9a1.75 1.75 0 0 1 1.75 1.75v4.5a1.75 1.75 0 0 1-1.75 1.75H8l-2.5 2v-2H3.5A1.75 1.75 0 0 1 1.75 9.5V5A1.75 1.75 0 0 1 3.5 3.25Z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"></path>
</svg>`;

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

function formatGeneratedDate(raw) {
  const match = raw.match(/^(\d{4})-([A-Za-z]+)-(\d{2})\s+(\d{2}):(\d{2})/);
  if (!match) return raw;
  const [, year, mon, day, h, min] = match;
  const hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${mon} ${parseInt(day, 10)}, ${year} · ${hour12}:${min} ${ampm}`;
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

function parseReportHash() {
  const hash = window.location.hash;
  const match = hash.match(/^#report\/(.+)$/);
  return match ? match[1] : null;
}

function showTableView() {
  const tableView = byId("reports-table-view");
  const detailView = byId("reports-detail-view");
  if (tableView) tableView.classList.remove("hidden");
  if (detailView) detailView.classList.add("hidden");
}

function showDetailView() {
  const tableView = byId("reports-table-view");
  const detailView = byId("reports-detail-view");
  if (tableView) tableView.classList.add("hidden");
  if (detailView) detailView.classList.remove("hidden");
}

function renderReportTable() {
  const empty = byId("reports-empty");
  const tableCard = byId("reports-table-card");
  const tbody = byId("reports-table-body");
  if (!empty || !tableCard || !tbody) return;

  if (!state.reports.length) {
    empty.classList.remove("hidden");
    tableCard.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");
  tableCard.classList.remove("hidden");

  tbody.innerHTML = state.reports
    .map((report) => {
      if (report.status === "in_progress") {
        const projectLabel = extractProjectLabel(report.previewUrl);
        return `<tr class="reports-table-row is-loading" data-report-id="${escapeHtml(report.id)}" data-report-status="in_progress">
          <td class="col-status"><span class="row-status-dot is-loading"></span></td>
          <td class="col-num">${report.order}</td>
          <td class="col-project">${escapeHtml(projectLabel)}</td>
          <td class="col-generated">In progress…</td>
          <td class="col-model">${escapeHtml(report.previewModel)}</td>
          <td class="col-items">—</td>
          <td class="col-comments">—</td>
        </tr>`;
      }

      const metadataMap = new Map(report.metadata.map((e) => [e.label.toLowerCase(), e.value]));
      const projectName = metadataMap.get("project name") || extractProjectLabel(report.previewUrl);
      const generated = metadataMap.get("generated") || "";
      const aiProvider = metadataMap.get("ai provider") || report.previewModel || "—";
      const totalItems = metadataMap.get("total items fetched") || "—";
      const updatedItems = metadataMap.get("items updated in lookback window") || "";
      const comments = metadataMap.get("comments created in lookback window") || "—";
      const modelName = aiProvider.includes(" - ")
        ? aiProvider.split(" - ").slice(1).join(" - ")
        : aiProvider;
      const itemsDisplay = updatedItems ? `${updatedItems} / ${totalItems}` : totalItems;
      const generatedDisplay = generated ? formatGeneratedDate(generated) : "—";

      if (report.status === "failed") {
        const statusDot = !report.read
          ? `<span class="row-status-dot is-failed"></span>`
          : "";
        return `<tr class="reports-table-row is-failed" data-report-id="${escapeHtml(report.id)}" data-report-status="failed" tabindex="0">
          <td class="col-status">${statusDot}</td>
          <td class="col-num">${report.order}</td>
          <td class="col-project col-failed-label">${escapeHtml(projectName)}</td>
          <td class="col-generated col-failed-label">Failed</td>
          <td class="col-model">${escapeHtml(modelName)}</td>
          <td class="col-items">—</td>
          <td class="col-comments">—</td>
        </tr>`;
      }

      // completed
      const statusDot = !report.read
        ? `<span class="row-status-dot is-new"></span>`
        : "";
      return `<tr class="reports-table-row" data-report-id="${escapeHtml(report.id)}" data-report-status="completed" tabindex="0">
        <td class="col-status">${statusDot}</td>
        <td class="col-num">${report.order}</td>
        <td class="col-project">${escapeHtml(projectName)}</td>
        <td class="col-generated">${escapeHtml(generatedDisplay)}</td>
        <td class="col-model">${escapeHtml(modelName)}</td>
        <td class="col-items">${escapeHtml(itemsDisplay)}</td>
        <td class="col-comments">${escapeHtml(comments)}</td>
      </tr>`;
    })
    .join("");

  tbody.querySelectorAll(".reports-table-row[data-report-status]").forEach((row) => {
    const { reportId, reportStatus } = row.dataset;
    if (reportStatus === "in_progress") return;

    const handleActivate = () => {
      if (reportStatus === "failed") {
        const report = state.reports.find((r) => r.id === reportId);
        if (report) showFailedReport(report);
      } else {
        window.location.hash = `#report/${reportId}`;
      }
    };

    row.addEventListener("click", handleActivate);
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleActivate();
      }
    });
  });
}

function renderActiveReport() {
  const container = byId("reports-list");
  if (!container) return;

  const report = state.reports.find((r) => r.id === state.activeReportId);
  if (!report || report.status !== "completed") return;

  markReportRead(report.id);

  const orderedMetadata = [...report.metadata].sort(
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
  const generatedPart = generatedEntry
    ? `<span class="meta-part">${CALENDAR_ICON}<span>${escapeHtml(formatGeneratedDate(generatedEntry.value))}</span></span>`
    : "";
  const modelName = providerEntry
    ? (providerEntry.value.includes(" - ")
        ? providerEntry.value.split(" - ").slice(1).join(" - ")
        : providerEntry.value)
    : "";
  const providerPart = providerEntry
    ? `<span class="meta-part meta-model">${MODEL_ICON}<span>${escapeHtml(modelName)}</span></span>`
    : "";
  let fetchedUpdatedPart = "";
  if (totalItemsEntry || updatedItemsEntry) {
    if (updatedItemsEntry && totalItemsEntry) {
      fetchedUpdatedPart = `<span class="stats-segment">${FETCHED_ICON}<strong>${escapeHtml(updatedItemsEntry.value)}</strong><span class="meta-sep" aria-hidden="true">/</span>${escapeHtml(totalItemsEntry.value)} updates</span>`;
    } else if (totalItemsEntry) {
      fetchedUpdatedPart = `<span class="stats-segment">${FETCHED_ICON}<strong>${escapeHtml(totalItemsEntry.value)}</strong> fetched</span>`;
    } else {
      fetchedUpdatedPart = `<span class="stats-segment">${FETCHED_ICON}<strong>${escapeHtml(updatedItemsEntry.value)}</strong> updated</span>`;
    }
  }
  const commentsPart = newCommentsEntry
    ? `<span class="stats-segment">${COMMENTS_ICON}<strong class="stats-comments">${escapeHtml(newCommentsEntry.value)}</strong> new comments</span>`
    : "";

  container.innerHTML = `
    <article class="card report-card">
      <div class="report-toolbar">
        <div class="report-toolbar-main">
          <div class="report-identity">
            ${
              projectNameEntry
                ? `<strong class="report-title-main">${
                    projectUrlEntry && /^https?:\/\//i.test(projectUrlEntry.value)
                      ? `<a class="report-title-link report-meta-project-link" href="${escapeHtml(
                          projectUrlEntry.value
                        )}" target="_blank" rel="noopener noreferrer">${escapeHtml(projectNameEntry.value)}</a>`
                      : `<span>${escapeHtml(projectNameEntry.value)}</span>`
                  }</strong>`
                : ""
            }
            <div class="report-file">${escapeHtml(report.filename)}</div>
          </div>
          <ul class="report-inline-stats" aria-label="Report activity metrics">
            ${generatedPart ? `<li class="stats-context">${generatedPart}</li>` : ""}
            ${fetchedUpdatedPart ? `<li class="stats-summary-main">${fetchedUpdatedPart}</li>` : ""}
            ${providerPart ? `<li class="stats-context-model">${providerPart}</li>` : ""}
            ${commentsPart ? `<li class="stats-summary-comments">${commentsPart}</li>` : ""}
          </ul>
        </div>
      </div>
      <div class="markdown-shell">
        <div class="markdown-actions">
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
          <button
            type="button"
            class="markdown-download-btn"
            id="report-download-btn"
            aria-label="Download .md"
            title="Download .md"
          >
            <svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" focusable="false">
              <path fill="currentColor" d="M7.47 10.78a.75.75 0 0 0 1.06 0l3.75-3.75a.75.75 0 0 0-1.06-1.06L8.75 8.44V1.75a.75.75 0 0 0-1.5 0v6.69L4.78 5.97a.75.75 0 0 0-1.06 1.06l3.75 3.75Z"></path>
              <path fill="currentColor" d="M1.75 13.5a.75.75 0 0 0 0 1.5h12.5a.75.75 0 0 0 0-1.5H1.75Z"></path>
            </svg>
          </button>
        </div>
        <div class="markdown-render" id="report-render"></div>
      </div>
    </article>
  `;

  byId("report-render").innerHTML = renderMarkdown(report.markdown);

  const copyButton = byId("report-copy-btn");
  const downloadButton = byId("report-download-btn");

  copyButton.addEventListener("click", async () => {
    if (copyButton.dataset.busy === "true") return;
    copyButton.dataset.busy = "true";
    try {
      await navigator.clipboard.writeText(report.markdown);
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
    downloadMarkdown(report.filename, report.markdown);
  });
}

export function updateReportsBadge() {
  const badge = byId("reports-count-badge");
  if (!badge) return;
  const count = state.reports.filter((r) => r.status !== "in_progress" && !r.read).length;
  if (count === 0) {
    badge.classList.add("hidden");
  } else {
    badge.textContent = count;
    badge.classList.remove("hidden");
  }
}

function handleHashChange() {
  const reportId = parseReportHash();
  if (reportId) {
    const report = state.reports.find((r) => r.id === reportId);
    if (report) {
      state.activeReportId = reportId;
      selectTab("reports");
      showDetailView();
      renderActiveReport();
    } else {
      history.pushState(null, "", window.location.pathname);
      showTableView();
      renderReportTable();
    }
  } else {
    showTableView();
    renderReportTable();
  }
}

export function extractProjectLabel(url) {
  if (!url) return "—";
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    const projectIdx = parts.indexOf("projects");
    if (projectIdx > 0) {
      return `${parts[projectIdx - 1]} / #${parts[projectIdx + 1] || "?"}`;
    }
    return u.hostname;
  } catch (_e) {
    return url.length > 32 ? url.slice(0, 32) + "…" : url;
  }
}

export function startReport(payload) {
  state.reportCounter += 1;
  const id = `report-${state.reportCounter}`;
  state.reports.push({
    id,
    order: state.reportCounter,
    status: "in_progress",
    read: false,
    filename: "",
    markdown: "",
    metadata: [],
    previewModel: payload.model || "",
    previewUrl: payload.project_url || "",
    progressSnapshot: null,
  });
  renderReportTable();
  return id;
}

export function completeReport(id, filename, markdown) {
  const report = state.reports.find((r) => r.id === id);
  if (!report) return;
  const { bodyMarkdown, metadata } = splitReportContent(markdown);
  report.filename = filename;
  report.markdown = bodyMarkdown;
  report.metadata = metadata;
  report.status = "completed";
  renderReportTable();
  updateReportsBadge();
}

export function failReport(id) {
  const report = state.reports.find((r) => r.id === id);
  if (!report) return;
  const progressList = byId("progress-list");
  report.progressSnapshot = progressList ? progressList.innerHTML : "";
  report.status = "failed";
  renderReportTable();
  updateReportsBadge();
}

export function markReportRead(id) {
  const report = state.reports.find((r) => r.id === id);
  if (!report || report.read) return;
  report.read = true;
  updateReportsBadge();
}

function showFailedReport(report) {
  markReportRead(report.id);
  showProgressSnapshot(report.progressSnapshot || "");
}

export function navigateToReport(id) {
  state.activeReportId = id;
  history.pushState(null, "", `#report/${id}`);
  selectTab("reports");
  showDetailView();
  renderActiveReport();
}

export function initReports() {
  window.addEventListener("hashchange", handleHashChange);

  const backBtn = byId("reports-back-btn");
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      history.pushState(null, "", window.location.pathname);
      showTableView();
      renderReportTable();
    });
  }

  const reportsTabBtn = byId("tab-trigger-reports");
  if (reportsTabBtn) {
    reportsTabBtn.addEventListener("click", () => {
      if (window.location.hash.startsWith("#report/")) {
        history.pushState(null, "", window.location.pathname);
      }
      showTableView();
      renderReportTable();
    });
  }

  updateReportsBadge();
  handleHashChange();
}
