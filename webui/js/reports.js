import { renderMarkdown } from "./markdown.js";
import { state } from "./state.js";
import { byId, escapeHtml } from "./utils.js";

export function selectTab(tabId) {
  document.querySelectorAll("[data-tab]").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach((el) => {
    el.classList.toggle("active", el.id === `tab-${tabId}`);
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

export function addReportTab(filename, markdown) {
  state.reportCounter += 1;
  const id = `report-${state.reportCounter}`;
  state.reports.push({ id, filename, markdown });

  const item = document.createElement("article");
  item.className = "card report-card";
  item.innerHTML = `
      <div class="report-toolbar">
        <div>
          <strong>Report ${state.reportCounter}: ${escapeHtml(filename)}</strong>
          <div class="report-meta">Generated and rendered in-app</div>
        </div>
        <div class="actions">
          <button type="button" class="ghost" data-copy="${id}">Copy</button>
          <button type="button" class="secondary" data-download="${id}">Download .md</button>
        </div>
      </div>
      <div class="markdown-render" data-render="${id}"></div>
  `;
  byId("reports-list").appendChild(item);
  byId("reports-empty").classList.add("hidden");

  item.querySelector(`[data-render="${id}"]`).innerHTML = renderMarkdown(markdown);

  item.querySelector(`[data-copy="${id}"]`).addEventListener("click", async () => {
    const btn = item.querySelector(`[data-copy="${id}"]`);
    const original = btn.textContent;
    try {
      await navigator.clipboard.writeText(markdown);
      btn.textContent = "Copied";
      btn.disabled = true;
      setTimeout(() => {
        btn.textContent = original;
        btn.disabled = false;
      }, 1500);
    } catch (_err) {
      btn.textContent = "Copy failed";
      btn.disabled = true;
      setTimeout(() => {
        btn.textContent = original;
        btn.disabled = false;
      }, 1800);
    }
  });
  item.querySelector(`[data-download="${id}"]`).addEventListener("click", () => {
    downloadMarkdown(filename, markdown);
  });

  selectTab("reports");
}
