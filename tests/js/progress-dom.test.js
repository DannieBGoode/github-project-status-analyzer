import test from "node:test";
import assert from "node:assert/strict";

const {
  evolveProgressState,
  updateFabState,
  findInProgressStep,
  minimizeProgress,
  expandProgress,
  showProgressSnapshot,
  stopProgressTimer,
} = await import("../../webui/js/progress.js");
const { progressSteps } = await import("../../webui/js/constants.js");

// ─── helpers ──────────────────────────────────────────────────────────────────

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
    focus() {},
  };
}

function setupDom(map = {}) {
  global.document = {
    getElementById: (id) => map[id] ?? null,
    querySelectorAll: () => [],
    activeElement: null,
  };
}

// ─── evolveProgressState — additional edge cases ──────────────────────────────

test("evolveProgressState second in_progress call does not reset startedAt", () => {
  const first = evolveProgressState(null, "in_progress", "Running", "", 1_000);
  const second = evolveProgressState(first, "in_progress", "Still running", "", 2_000);
  assert.equal(second.startedAt, 1_000, "startedAt should not be overwritten");
});

test("evolveProgressState completed→completed does not recalculate elapsedMs", () => {
  const inProgress = evolveProgressState(null, "in_progress", "Working", "", 1_000);
  const completed = evolveProgressState(inProgress, "completed", "Done", "", 3_000);
  // startedAt is now null; calling completed again should not change elapsedMs
  const completedAgain = evolveProgressState(completed, "completed", "Done again", "", 5_000);
  assert.equal(completedAgain.elapsedMs, 2_000, "elapsedMs should remain 2000");
  assert.equal(completedAgain.startedAt, null);
});

test("evolveProgressState clears errorText when not provided", () => {
  const withError = {
    status: "failed",
    startedAt: null,
    elapsedMs: 500,
    message: "Failed",
    error: "Previous error",
  };
  const next = evolveProgressState(withError, "pending", "Reset", "");
  assert.equal(next.error, "");
});

test("evolveProgressState errorText overrides existing error", () => {
  const prev = { status: "in_progress", startedAt: null, elapsedMs: 0, message: "Working", error: "old" };
  const next = evolveProgressState(prev, "failed", "Failed", "new error");
  assert.equal(next.error, "new error");
});

// ─── updateFabState ───────────────────────────────────────────────────────────

function makeFabDom() {
  const fab = makeMockEl();
  const expandBtn = makeMockEl();
  const dismissBtn = makeMockEl(["hidden"]);
  setupDom({
    "progress-fab": fab,
    "progress-fab-expand": expandBtn,
    "progress-fab-dismiss": dismissBtn,
  });
  return { fab, expandBtn, dismissBtn };
}

test("updateFabState in_progress: adds is-active, hides dismiss, clears innerHTML", () => {
  const { fab, expandBtn, dismissBtn } = makeFabDom();
  updateFabState("in_progress");
  assert.ok(fab.classList.contains("is-active"), "fab should have is-active");
  assert.ok(!fab.classList.contains("is-success"), "fab should not have is-success");
  assert.ok(!fab.classList.contains("is-error"), "fab should not have is-error");
  assert.equal(expandBtn.innerHTML, "");
  assert.ok(dismissBtn.classList.contains("hidden"), "dismiss should be hidden");
  assert.equal(expandBtn.getAttribute("aria-label"), "Show progress");
});

test("updateFabState completed: adds is-success, shows dismiss, sets non-empty innerHTML", () => {
  const { fab, expandBtn, dismissBtn } = makeFabDom();
  updateFabState("completed");
  assert.ok(fab.classList.contains("is-success"));
  assert.ok(!fab.classList.contains("is-active"));
  assert.ok(expandBtn.innerHTML.length > 0, "innerHTML should have check SVG");
  assert.ok(!dismissBtn.classList.contains("hidden"), "dismiss should be visible");
  assert.equal(expandBtn.getAttribute("aria-label"), "Show completed report");
});

test("updateFabState failed: adds is-error, shows dismiss, sets non-empty innerHTML", () => {
  const { fab, expandBtn, dismissBtn } = makeFabDom();
  updateFabState("failed");
  assert.ok(fab.classList.contains("is-error"));
  assert.ok(!fab.classList.contains("is-active"));
  assert.ok(expandBtn.innerHTML.length > 0, "innerHTML should have error SVG");
  assert.ok(!dismissBtn.classList.contains("hidden"), "dismiss should be visible");
  assert.equal(expandBtn.getAttribute("aria-label"), "Show error details");
});

test("updateFabState switching from failed to completed removes is-error", () => {
  const { fab } = makeFabDom();
  updateFabState("failed");
  assert.ok(fab.classList.contains("is-error"));
  updateFabState("completed");
  assert.ok(!fab.classList.contains("is-error"), "is-error should be removed");
  assert.ok(fab.classList.contains("is-success"), "is-success should be added");
});

test("updateFabState with missing fab element does not throw", () => {
  setupDom({}); // all null
  assert.doesNotThrow(() => updateFabState("completed"));
});

// ─── findInProgressStep ───────────────────────────────────────────────────────

function makeStepsDom(inProgressIds = []) {
  const map = {};
  for (const step of progressSteps) {
    const el = makeMockEl(
      inProgressIds.includes(step.id) ? ["in_progress"] : []
    );
    map[`step-${step.id}`] = el;
  }
  setupDom(map);
  return map;
}

test("findInProgressStep returns null when no step is in progress", () => {
  makeStepsDom([]);
  assert.equal(findInProgressStep(), null);
});

test("findInProgressStep returns the id of the first step in progress", () => {
  makeStepsDom([progressSteps[0].id]);
  assert.equal(findInProgressStep(), progressSteps[0].id);
});

test("findInProgressStep returns the correct middle step id", () => {
  const mid = progressSteps[2].id; // ai_send
  makeStepsDom([mid]);
  assert.equal(findInProgressStep(), mid);
});

test("findInProgressStep returns first match when multiple steps in progress", () => {
  makeStepsDom([progressSteps[0].id, progressSteps[2].id]);
  assert.equal(findInProgressStep(), progressSteps[0].id);
});

test("findInProgressStep returns null when all DOM elements are null", () => {
  setupDom({}); // all null
  assert.equal(findInProgressStep(), null);
});

// ─── minimizeProgress / expandProgress ───────────────────────────────────────

function makeMinimizeDom(loadingClasses = [], fabClasses = ["hidden"]) {
  const loading = makeMockEl(loadingClasses);
  const fab     = makeMockEl(fabClasses);
  const expandBtn = makeMockEl();
  const dismissBtn = makeMockEl(["hidden"]);
  setupDom({
    "loading": loading,
    "progress-fab": fab,
    "progress-fab-expand": expandBtn,
    "progress-fab-dismiss": dismissBtn,
    "loading-panel": makeMockEl(),
  });
  return { loading, fab };
}

test("minimizeProgress adds minimized class to loading", () => {
  const { loading } = makeMinimizeDom();
  minimizeProgress();
  assert.ok(loading.classList.contains("minimized"));
});

test("minimizeProgress removes hidden from FAB", () => {
  const { fab } = makeMinimizeDom();
  minimizeProgress();
  assert.ok(!fab.classList.contains("hidden"), "FAB should be visible after minimize");
});

test("expandProgress removes minimized class from loading", () => {
  const { loading } = makeMinimizeDom(["minimized"]);
  expandProgress();
  assert.ok(!loading.classList.contains("minimized"));
});

test("expandProgress adds hidden to FAB", () => {
  const { fab } = makeMinimizeDom([], []);
  expandProgress();
  assert.ok(fab.classList.contains("hidden"), "FAB should be hidden after expand");
});

test("minimizeProgress after error state: FAB gets is-error not is-active", () => {
  const { fab } = makeMinimizeDom();
  // First establish error state
  updateFabState("failed");
  // Now minimize — should preserve the error state, not reset to in_progress
  minimizeProgress();
  assert.ok(fab.classList.contains("is-error"), "FAB should have is-error after minimizing an error");
  assert.ok(!fab.classList.contains("is-active"), "FAB should NOT have is-active");
});

test("minimizeProgress and expandProgress with missing elements do not throw", () => {
  setupDom({});
  assert.doesNotThrow(() => minimizeProgress());
  assert.doesNotThrow(() => expandProgress());
});

// ─── showProgressSnapshot ────────────────────────────────────────────────────

function makeSnapshotDom(overrides = {}) {
  const progressList   = makeMockEl();
  const minimizeBtn    = makeMockEl();
  const goToReportBtn  = makeMockEl();
  const closeBtn       = makeMockEl(["hidden"]);
  const loading        = makeMockEl(["hidden", "minimized"]);
  const fab            = makeMockEl();
  const loadingPanel   = makeMockEl();
  setupDom({
    "progress-list":          progressList,
    "loading-minimize":       minimizeBtn,
    "loading-go-to-report":   goToReportBtn,
    "loading-close":          closeBtn,
    "loading":                loading,
    "progress-fab":           fab,
    "loading-panel":          loadingPanel,
    ...overrides,
  });
  return { progressList, minimizeBtn, goToReportBtn, closeBtn, loading, fab, loadingPanel };
}

test("showProgressSnapshot injects HTML into progress-list", () => {
  const { progressList } = makeSnapshotDom();
  showProgressSnapshot("<li>step</li>");
  assert.equal(progressList.innerHTML, "<li>step</li>");
});

test("showProgressSnapshot hides minimize button", () => {
  const { minimizeBtn } = makeSnapshotDom();
  showProgressSnapshot("<li>x</li>");
  assert.ok(minimizeBtn.classList.contains("hidden"), "minimize button should be hidden");
});

test("showProgressSnapshot hides go-to-report button", () => {
  const { goToReportBtn } = makeSnapshotDom();
  showProgressSnapshot("<li>x</li>");
  assert.ok(goToReportBtn.classList.contains("hidden"), "go-to-report button should be hidden");
});

test("showProgressSnapshot shows and enables close button", () => {
  const { closeBtn } = makeSnapshotDom();
  showProgressSnapshot("<li>x</li>");
  assert.ok(!closeBtn.classList.contains("hidden"), "close button should be visible");
  assert.equal(closeBtn.disabled, false);
});

test("showProgressSnapshot removes hidden and minimized from loading", () => {
  const { loading } = makeSnapshotDom();
  showProgressSnapshot("<li>x</li>");
  assert.ok(!loading.classList.contains("hidden"), "loading should not be hidden");
  assert.ok(!loading.classList.contains("minimized"), "loading should not be minimized");
});

test("showProgressSnapshot hides FAB", () => {
  const { fab } = makeSnapshotDom();
  fab.classList.remove("hidden"); // start visible
  showProgressSnapshot("<li>x</li>");
  assert.ok(fab.classList.contains("hidden"), "FAB should be hidden");
});

test("showProgressSnapshot with empty string clears progress list", () => {
  const { progressList } = makeSnapshotDom();
  progressList.innerHTML = "<li>old</li>";
  showProgressSnapshot("");
  assert.equal(progressList.innerHTML, "");
});

// clean up any timer that may have been started
stopProgressTimer();
