import test from "node:test";
import assert from "node:assert/strict";

global.window = { location: { origin: "https://example.test" } };

const { renderMarkdown } = await import("../../webui/js/markdown.js");

test("renderMarkdown escapes HTML in plain text", () => {
  const html = renderMarkdown("<script>alert('x')</script>");
  assert.match(html, /&lt;script&gt;alert\('x'\)&lt;\/script&gt;/);
});

test("renderMarkdown blocks javascript links", () => {
  const html = renderMarkdown("[click](javascript:alert(1))");
  assert.match(html, /href="#"/);
});

test("renderMarkdown renders safe http links with noreferrer", () => {
  const html = renderMarkdown("[site](https://example.com/path)");
  assert.match(html, /href="https:\/\/example\.com\/path"/);
  assert.match(html, /rel="noopener noreferrer"/);
});
