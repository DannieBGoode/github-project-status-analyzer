import test from "node:test";
import assert from "node:assert/strict";

const { formatDuration, escapeHtml } = await import("../../webui/js/utils.js");

test("formatDuration formats ms to m:ss", () => {
  assert.equal(formatDuration(0), "0:00");
  assert.equal(formatDuration(90_000), "1:30");
  assert.equal(formatDuration(3_661_000), "61:01");
});

test("escapeHtml escapes core HTML chars", () => {
  assert.equal(escapeHtml("<a&b>"), "&lt;a&amp;b&gt;");
});
