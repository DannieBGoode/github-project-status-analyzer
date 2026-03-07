import test from "node:test";
import assert from "node:assert/strict";

const { buildReportMetadataCards, getTemporaryButtonState, openReportsEmptyTarget, selectTab, splitReportContent } = await import("../../webui/js/reports.js");

function createMockElement({ id = "", tab = "", classes = [] } = {}) {
  const classSet = new Set(classes);
  const attrs = {};
  return {
    id,
    dataset: { tab },
    classList: {
      toggle(name, force) {
        if (force) classSet.add(name);
        else classSet.delete(name);
      },
      contains(name) {
        return classSet.has(name);
      },
    },
    setAttribute(name, value) {
      attrs[name] = String(value);
    },
    getAttribute(name) {
      return attrs[name];
    },
    toggleAttribute(name, force) {
      if (force) attrs[name] = "";
      else delete attrs[name];
    },
  };
}

test("getTemporaryButtonState returns success transition shape", () => {
  const state = getTemporaryButtonState("Copy", "Copied", "Copy failed", false);
  assert.deepEqual(state, {
    text: "Copied",
    disabled: true,
    resetText: "Copy",
    resetDisabled: false,
    resetAfterMs: 1500,
  });
});

test("getTemporaryButtonState returns error transition shape", () => {
  const state = getTemporaryButtonState("Copy", "Copied", "Copy failed", true);
  assert.deepEqual(state, {
    text: "Copy failed",
    disabled: true,
    resetText: "Copy",
    resetDisabled: false,
    resetAfterMs: 1800,
  });
});

test("selectTab synchronizes class and aria states for tabs and panels", () => {
  const generatorTab = createMockElement({ tab: "generator", classes: ["nav-tab", "active"] });
  const reportsTab = createMockElement({ tab: "reports", classes: ["nav-tab"] });
  const settingsBtn = createMockElement({ tab: "settings", classes: ["utility-btn"] });
  const generatorPanel = createMockElement({ id: "tab-generator", classes: ["tab-panel", "active"] });
  const reportsPanel = createMockElement({ id: "tab-reports", classes: ["tab-panel"] });
  const settingsPanel = createMockElement({ id: "tab-settings", classes: ["tab-panel"] });

  global.document = {
    querySelectorAll(selector) {
      if (selector === "[data-tab]") return [generatorTab, reportsTab, settingsBtn];
      if (selector === ".tab-panel") return [generatorPanel, reportsPanel, settingsPanel];
      return [];
    },
  };

  selectTab("reports");

  assert.equal(generatorTab.classList.contains("active"), false);
  assert.equal(generatorTab.getAttribute("aria-selected"), "false");
  assert.equal(generatorTab.getAttribute("tabindex"), "-1");
  assert.equal(reportsTab.classList.contains("active"), true);
  assert.equal(reportsTab.getAttribute("aria-selected"), "true");
  assert.equal(reportsTab.getAttribute("tabindex"), "0");
  assert.equal(settingsBtn.classList.contains("active"), false);
  assert.equal(settingsBtn.getAttribute("aria-pressed"), "false");

  assert.equal(generatorPanel.classList.contains("active"), false);
  assert.equal(generatorPanel.getAttribute("aria-hidden"), "true");
  assert.equal(generatorPanel.getAttribute("hidden"), "");
  assert.equal(reportsPanel.classList.contains("active"), true);
  assert.equal(reportsPanel.getAttribute("aria-hidden"), "false");
  assert.equal(reportsPanel.getAttribute("hidden"), undefined);
});

test("splitReportContent extracts Executive Report preamble metadata and keeps report body", () => {
  const markdown = `# Executive Report

- Generated: 2026-Mar-04 20:20 GMT+1
- AI Provider: Gemini - Gemini 2.5 Flash-Lite Preview
- Project Name: Mithril Network
- Project URL: https://github.com/orgs/input-output-hk/projects/26

---

- Total Items Fetched: \`100\`
- Items Updated in Lookback Window: \`64\`
- Comments Created in Lookback Window: \`26\`

## Key Highlights
Body line.`;

  const result = splitReportContent(markdown);

  assert.equal(result.metadata.length, 7);
  assert.deepEqual(result.metadata[0], {
    label: "Generated",
    value: "2026-Mar-04 20:20 GMT+1",
  });
  assert.deepEqual(result.metadata[6], {
    label: "Comments Created in Lookback Window",
    value: "26",
  });
  assert.match(result.bodyMarkdown, /^## Key Highlights/);
  assert.doesNotMatch(result.bodyMarkdown, /Executive Report/);
  assert.doesNotMatch(result.bodyMarkdown, /Total Items Fetched/);
});

test("splitReportContent supports non-bulleted and indented metadata lines", () => {
  const markdown = `Executive Report

    Generated: 2026-Mar-04 20:20 GMT+1
    AI Provider: Gemini - Gemini 2.5 Flash-Lite Preview
    Project Name: Mithril Network
    Project URL: https://github.com/orgs/input-output-hk/projects/26

    Total Items Fetched: 100
    Items Updated in Lookback Window: 64
    Comments Created in Lookback Window: 26

## Risks
None`;

  const result = splitReportContent(markdown);

  assert.equal(result.metadata.length, 7);
  assert.equal(result.bodyMarkdown, "## Risks\nNone");
});

test("splitReportContent leaves markdown unchanged when report preamble is absent", () => {
  const markdown = "## Weekly Status\n\n- Done: item\n";
  const result = splitReportContent(markdown);
  assert.equal(result.metadata.length, 0);
  assert.equal(result.bodyMarkdown, markdown);
});
test("openReportsEmptyTarget clears report hash and activates generator tab", () => {
  const calls = [];
  global.history = {
    pushState(_state, _title, url) {
      calls.push(url);
    },
  };
  global.window = {
    location: {
      hash: "#report/report-9",
      pathname: "/",
    },
  };
  const generatorTab = createMockElement({ tab: "generator", classes: ["nav-tab"] });
  const reportsTab = createMockElement({ tab: "reports", classes: ["nav-tab", "active"] });
  const settingsBtn = createMockElement({ tab: "settings", classes: ["utility-btn"] });
  const generatorPanel = createMockElement({ id: "tab-generator", classes: ["tab-panel"] });
  const reportsPanel = createMockElement({ id: "tab-reports", classes: ["tab-panel", "active"] });
  const settingsPanel = createMockElement({ id: "tab-settings", classes: ["tab-panel"] });
  global.document = {
    querySelectorAll(selector) {
      if (selector === "[data-tab]") return [generatorTab, reportsTab, settingsBtn];
      if (selector === ".tab-panel") return [generatorPanel, reportsPanel, settingsPanel];
      return [];
    },
    getElementById() {
      return null;
    },
  };
  openReportsEmptyTarget("generator");
  assert.deepEqual(calls, ["/"]);
  assert.equal(generatorTab.classList.contains("active"), true);
  assert.equal(generatorPanel.classList.contains("active"), true);
  assert.equal(reportsPanel.classList.contains("active"), false);
});

test("buildReportMetadataCards returns labeled metadata cards", () => {
  const cards = buildReportMetadataCards({
    generated: "2026-Mar-07 14:14 GMT+1",
    provider: "Gemini - Gemini 2.5 Flash-Lite Preview",
    totalItems: "100",
    updatedItems: "62",
    newComments: "18",
  });

  assert.match(cards.generatedPart, /report-meta-card-context/);
  assert.match(cards.generatedPart, /Generated/);
  assert.match(cards.providerPart, /Model/);
  assert.match(cards.providerPart, /Gemini 2.5 Flash-Lite Preview/);
  assert.match(cards.fetchedUpdatedPart, /Activity/);
  assert.ok(cards.fetchedUpdatedPart.includes('62</strong><span class="meta-sep"')); 
  assert.match(cards.commentsPart, /Discussion/);
  assert.ok(cards.commentsPart.includes('18</strong> new comments')); 
});
