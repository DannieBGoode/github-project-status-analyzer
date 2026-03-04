import { renderMarkdown } from "./markdown.js";
import { state } from "./state.js";
import { byId, escapeHtml } from "./utils.js";

export function selectTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach((el) => {
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

  const tabs = byId("tabs");
  const tabBtn = document.createElement("button");
  tabBtn.className = "tab-btn";
  tabBtn.dataset.tab = id;
  tabBtn.textContent = `Report ${state.reportCounter}`;
  tabBtn.addEventListener("click", () => selectTab(id));
  const spacer = tabs.querySelector(".tabs-spacer");
  if (spacer) {
    tabs.insertBefore(tabBtn, spacer);
  } else {
    tabs.appendChild(tabBtn);
  }

  const panel = document.createElement("section");
  panel.id = `tab-${id}`;
  panel.className = "tab-panel";
  panel.innerHTML = `
    <div class="card">
      <div class="report-toolbar">
        <div>
          <strong>${escapeHtml(filename)}</strong>
          <div class="report-meta">Generated and rendered in-app</div>
        </div>
        <div class="actions">
          <button type="button" class="secondary" data-copy="${id}">Copy</button>
          <button type="button" class="primary" data-download="${id}">Download .md</button>
        </div>
      </div>
      <div class="markdown-render" data-render="${id}"></div>
    </div>
  `;
  byId("reports-container").appendChild(panel);
  panel.querySelector(`[data-render="${id}"]`).innerHTML = renderMarkdown(markdown);

  panel.querySelector(`[data-copy="${id}"]`).addEventListener("click", async () => {
    const btn = panel.querySelector(`[data-copy="${id}"]`);
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
  panel.querySelector(`[data-download="${id}"]`).addEventListener("click", () => {
    downloadMarkdown(filename, markdown);
  });

  selectTab(id);
}
