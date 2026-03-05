import test from "node:test";
import assert from "node:assert/strict";

const { state } = await import("../../webui/js/state.js");
const { buildRunPayload, updateModelDropdown } = await import("../../webui/js/config.js");

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function makeInputEl(value = "") {
  return { value };
}

function makeSelectEl() {
  const children = [];
  let _value = "";
  return {
    set innerHTML(_v) {
      children.length = 0;
    },
    get value() {
      return _value;
    },
    set value(v) {
      _value = v;
    },
    appendChild(child) {
      children.push(child);
    },
    get _children() {
      return children;
    },
  };
}

function setupDom(overrides = {}) {
  const values = {
    max_items: "100",
    ai_provider: "gemini",
    model: "gemini-2.5-flash",
    project_url: "https://github.com/orgs/acme/projects/1",
    lookback_days: "14",
    max_comments_per_item: "20",
    github_token: "ghp_token",
    gemini_api_key: "g_key",
    openai_api_key: "o_key",
    ...overrides,
  };

  const elements = {};
  for (const [id, val] of Object.entries(values)) {
    elements[id] = makeInputEl(String(val));
  }

  global.document = {
    getElementById(id) {
      return elements[id] ?? null;
    },
    createElement(_tag) {
      return { value: "", textContent: "" };
    },
  };

  return elements;
}

// ---------------------------------------------------------------------------
// buildRunPayload — max_items clamping
// ---------------------------------------------------------------------------

test("buildRunPayload clamps max_items above 100 to 100", () => {
  const els = setupDom({ max_items: "200" });
  const payload = buildRunPayload();
  assert.equal(payload.max_items, "100");
  assert.equal(els.max_items.value, "100");
});

test("buildRunPayload clamps max_items of 0 up to 1", () => {
  const els = setupDom({ max_items: "0" });
  const payload = buildRunPayload();
  assert.equal(payload.max_items, "1");
  assert.equal(els.max_items.value, "1");
});

test("buildRunPayload defaults max_items to 100 for non-numeric input", () => {
  setupDom({ max_items: "abc" });
  const payload = buildRunPayload();
  assert.equal(payload.max_items, "100");
});

test("buildRunPayload keeps valid max_items within range unchanged", () => {
  setupDom({ max_items: "50" });
  const payload = buildRunPayload();
  assert.equal(payload.max_items, "50");
});

test("buildRunPayload returns all expected payload keys", () => {
  setupDom();
  const payload = buildRunPayload();
  const requiredKeys = [
    "ai_provider",
    "model",
    "project_url",
    "lookback_days",
    "max_items",
    "max_comments_per_item",
    "report_timezone",
    "report_timezone_label",
    "github_token",
    "gemini_api_key",
    "openai_api_key",
  ];
  for (const key of requiredKeys) {
    assert.ok(Object.hasOwn(payload, key), `payload missing key: ${key}`);
  }
});

// ---------------------------------------------------------------------------
// updateModelDropdown — model selection logic
// ---------------------------------------------------------------------------

const GEMINI_OPTIONS = [
  { id: "gemini-2.5-flash-lite-preview-09-2025", label: "Gemini 2.5 Flash-Lite Preview" },
  { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
];

function setupDropdownDom() {
  const select = makeSelectEl();
  global.document = {
    getElementById(id) {
      return id === "model" ? select : null;
    },
    createElement(_tag) {
      return { value: "", textContent: "" };
    },
  };
  state.modelOptions = { gemini: GEMINI_OPTIONS, openai: [] };
  return select;
}

test("updateModelDropdown appends one option per model entry", () => {
  const select = setupDropdownDom();
  updateModelDropdown("gemini");
  assert.equal(select._children.length, GEMINI_OPTIONS.length);
});

test("updateModelDropdown sets value to preferred model when it exists", () => {
  const select = setupDropdownDom();
  updateModelDropdown("gemini", "gemini-2.5-pro");
  assert.equal(select.value, "gemini-2.5-pro");
});

test("updateModelDropdown falls back to first model when preferred is absent", () => {
  const select = setupDropdownDom();
  updateModelDropdown("gemini", "nonexistent-model");
  assert.equal(select.value, GEMINI_OPTIONS[0].id);
});

test("updateModelDropdown falls back to first model when no preferred supplied", () => {
  const select = setupDropdownDom();
  updateModelDropdown("gemini");
  assert.equal(select.value, GEMINI_OPTIONS[0].id);
});

test("updateModelDropdown clears previous options before adding new ones", () => {
  const select = setupDropdownDom();
  // First call
  updateModelDropdown("gemini");
  assert.equal(select._children.length, GEMINI_OPTIONS.length);
  // Second call (empty provider) should clear
  state.modelOptions.openai = [];
  updateModelDropdown("openai");
  assert.equal(select._children.length, 0);
});
