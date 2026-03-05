import test from "node:test";
import assert from "node:assert/strict";

const {
  startReport,
  completeReport,
  failReport,
  markReportRead,
  extractProjectLabel,
  updateReportsBadge,
} = await import("../../webui/js/reports.js");
const { state } = await import("../../webui/js/state.js");

// ─── helpers ──────────────────────────────────────────────────────────────────

function resetState() {
  state.reports.length = 0;
  state.reportCounter = 0;
  state.activeReportId = null;
}

function makeMockEl(initialClasses = []) {
  const classes = new Set(initialClasses);
  const attrs = {};
  let _html = "", _text = "";
  return {
    classList: {
      add(...c)    { c.forEach(x => classes.add(x)); },
      remove(...c) { c.forEach(x => classes.delete(x)); },
      toggle(c, f) { f ? classes.add(c) : classes.delete(c); },
      contains(c)  { return classes.has(c); },
    },
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k)    { return attrs[k]; },
    get innerHTML()    { return _html; },
    set innerHTML(v)   { _html = v; },
    get textContent()  { return _text; },
    set textContent(v) { _text = v; },
    disabled: false,
  };
}

// Null-returning document — prevents side-effect DOM calls from crashing
function makeNullDom(overrides = {}) {
  global.document = {
    getElementById: (id) => overrides[id] ?? null,
    querySelectorAll: () => [],
    createElement: (tag) => {
      const el = makeMockEl();
      el.tagName = tag.toUpperCase();
      el._children = [];
      el.appendChild = (child) => { el._children.push(child); return child; };
      return el;
    },
  };
}

// ─── extractProjectLabel ──────────────────────────────────────────────────────

test("extractProjectLabel parses org project URL", () => {
  const result = extractProjectLabel("https://github.com/orgs/myorg/projects/5");
  assert.equal(result, "myorg / #5");
});

test("extractProjectLabel parses user project URL", () => {
  const result = extractProjectLabel("https://github.com/users/alice/projects/3");
  assert.equal(result, "alice / #3");
});

test("extractProjectLabel returns hostname when no /projects/ segment", () => {
  const result = extractProjectLabel("https://github.com/orgs/myorg");
  assert.equal(result, "github.com");
});

test("extractProjectLabel truncates invalid URL longer than 32 chars", () => {
  const long = "not-a-url-but-a-very-long-string-indeed";
  const result = extractProjectLabel(long);
  assert.equal(result, long.slice(0, 32) + "…");
  assert.ok(long.length > 32);
});

test("extractProjectLabel returns short invalid URL as-is", () => {
  const result = extractProjectLabel("short-invalid");
  assert.equal(result, "short-invalid");
});

test("extractProjectLabel returns dash for null", () => {
  assert.equal(extractProjectLabel(null), "—");
});

test("extractProjectLabel returns dash for empty string", () => {
  assert.equal(extractProjectLabel(""), "—");
});

// ─── startReport ─────────────────────────────────────────────────────────────

test("startReport increments counter and returns id", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "https://github.com/orgs/x/projects/1" });
  assert.equal(state.reportCounter, 1);
  assert.equal(id, "report-1");
});

test("startReport second call increments counter to 2", () => {
  resetState();
  makeNullDom();
  startReport({ model: "gemini", project_url: "https://github.com/orgs/x/projects/1" });
  const id2 = startReport({ model: "openai", project_url: "https://github.com/orgs/x/projects/2" });
  assert.equal(state.reportCounter, 2);
  assert.equal(id2, "report-2");
});

test("startReport creates report with status in_progress and read false", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "https://github.com/orgs/x/projects/1" });
  const report = state.reports.find((r) => r.id === id);
  assert.ok(report, "report should exist in state");
  assert.equal(report.status, "in_progress");
  assert.equal(report.read, false);
});

test("startReport copies previewModel and previewUrl from payload", () => {
  resetState();
  makeNullDom();
  const payload = { model: "gemini-flash", project_url: "https://github.com/orgs/myorg/projects/7" };
  const id = startReport(payload);
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.previewModel, "gemini-flash");
  assert.equal(report.previewUrl, "https://github.com/orgs/myorg/projects/7");
});

test("startReport pushes report to state.reports", () => {
  resetState();
  makeNullDom();
  assert.equal(state.reports.length, 0);
  startReport({ model: "gemini", project_url: "" });
  assert.equal(state.reports.length, 1);
});

// ─── completeReport ───────────────────────────────────────────────────────────

const EXEC_MARKDOWN = `# Executive Report

- Generated: 2026-Mar-04 20:20 GMT+1
- AI Provider: Gemini - Gemini 2.5 Flash
- Project Name: Test Project
- Project URL: https://github.com/orgs/test/projects/1

---

- Total Items Fetched: \`50\`
- Items Updated in Lookback Window: \`20\`
- Comments Created in Lookback Window: \`5\`

## Key Highlights
Body content here.`;

test("completeReport sets status to completed", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  completeReport(id, "report.md", EXEC_MARKDOWN);
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.status, "completed");
});

test("completeReport stores filename on report", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  completeReport(id, "my-report.md", EXEC_MARKDOWN);
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.filename, "my-report.md");
});

test("completeReport parses Executive Report metadata", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  completeReport(id, "report.md", EXEC_MARKDOWN);
  const report = state.reports.find((r) => r.id === id);
  assert.ok(report.metadata.length > 0, "metadata should be populated");
});

test("completeReport bodyMarkdown strips Executive Report preamble", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  completeReport(id, "report.md", EXEC_MARKDOWN);
  const report = state.reports.find((r) => r.id === id);
  assert.ok(!report.markdown.includes("Executive Report"), "preamble should be stripped");
  assert.ok(report.markdown.includes("Key Highlights"), "body should remain");
});

test("completeReport with unknown id is a no-op", () => {
  resetState();
  makeNullDom();
  assert.doesNotThrow(() => completeReport("nonexistent", "f.md", "body"));
  assert.equal(state.reports.length, 0);
});

// ─── failReport ───────────────────────────────────────────────────────────────

test("failReport sets status to failed", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  failReport(id);
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.status, "failed");
});

test("failReport captures progress-list innerHTML as progressSnapshot", () => {
  resetState();
  const progressList = makeMockEl();
  progressList.innerHTML = "<li>step</li>";
  makeNullDom({ "progress-list": progressList });
  const id = startReport({ model: "gemini", project_url: "" });
  failReport(id);
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.progressSnapshot, "<li>step</li>");
});

test("failReport sets progressSnapshot to empty string when progress-list missing", () => {
  resetState();
  makeNullDom(); // progress-list returns null
  const id = startReport({ model: "gemini", project_url: "" });
  failReport(id);
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.progressSnapshot, "");
});

test("failReport with unknown id is a no-op", () => {
  resetState();
  makeNullDom();
  assert.doesNotThrow(() => failReport("nonexistent"));
  assert.equal(state.reports.length, 0);
});

// ─── markReportRead ───────────────────────────────────────────────────────────

test("markReportRead sets read to true", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.read, false);
  markReportRead(id);
  assert.equal(report.read, true);
});

test("markReportRead is idempotent", () => {
  resetState();
  makeNullDom();
  const id = startReport({ model: "gemini", project_url: "" });
  markReportRead(id);
  assert.doesNotThrow(() => markReportRead(id));
  const report = state.reports.find((r) => r.id === id);
  assert.equal(report.read, true);
});

test("markReportRead with unknown id is a no-op", () => {
  resetState();
  makeNullDom();
  assert.doesNotThrow(() => markReportRead("nonexistent"));
});

// ─── updateReportsBadge ───────────────────────────────────────────────────────

function makeBadgeEl() {
  return makeMockEl(["hidden"]);
}

function setupBadgeDom(badge) {
  makeNullDom({ "reports-count-badge": badge });
}

test("updateReportsBadge hides badge when all reports are in_progress", () => {
  resetState();
  state.reports.push({ id: "r1", status: "in_progress", read: false });
  state.reports.push({ id: "r2", status: "in_progress", read: false });
  const badge = makeBadgeEl();
  setupBadgeDom(badge);
  updateReportsBadge();
  assert.ok(badge.classList.contains("hidden"), "badge should be hidden");
});

test("updateReportsBadge shows count 1 for one unread completed report", () => {
  resetState();
  state.reports.push({ id: "r1", status: "completed", read: false });
  const badge = makeBadgeEl();
  setupBadgeDom(badge);
  updateReportsBadge();
  assert.ok(!badge.classList.contains("hidden"), "badge should be visible");
  assert.equal(badge.textContent, 1);
});

test("updateReportsBadge counts unread failed reports", () => {
  resetState();
  state.reports.push({ id: "r1", status: "failed", read: false });
  const badge = makeBadgeEl();
  setupBadgeDom(badge);
  updateReportsBadge();
  assert.equal(badge.textContent, 1);
  assert.ok(!badge.classList.contains("hidden"));
});

test("updateReportsBadge counts mixed unread, excludes read and in_progress", () => {
  resetState();
  state.reports.push({ id: "r1", status: "completed", read: false });
  state.reports.push({ id: "r2", status: "failed",    read: false });
  state.reports.push({ id: "r3", status: "completed", read: true  });
  state.reports.push({ id: "r4", status: "in_progress", read: false });
  const badge = makeBadgeEl();
  setupBadgeDom(badge);
  updateReportsBadge();
  assert.equal(badge.textContent, 2);
});

test("updateReportsBadge hides badge when all finished reports are read", () => {
  resetState();
  state.reports.push({ id: "r1", status: "completed", read: true });
  state.reports.push({ id: "r2", status: "completed", read: true });
  state.reports.push({ id: "r3", status: "completed", read: true });
  const badge = makeBadgeEl();
  setupBadgeDom(badge);
  updateReportsBadge();
  assert.ok(badge.classList.contains("hidden"));
});

test("updateReportsBadge hides badge when no reports exist", () => {
  resetState();
  const badge = makeBadgeEl();
  setupBadgeDom(badge);
  updateReportsBadge();
  assert.ok(badge.classList.contains("hidden"));
});
