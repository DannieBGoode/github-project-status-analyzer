import { escapeHtml } from "./utils.js";

function escapeHtmlAttr(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sanitizeHref(rawHref) {
  const href = String(rawHref || "").trim();
  if (!href) return "#";
  if (/^(javascript|data|vbscript):/i.test(href)) return "#";
  if (href.startsWith("#") || href.startsWith("/")) return escapeHtmlAttr(href);
  if (/^mailto:/i.test(href)) return escapeHtmlAttr(href);
  try {
    const parsed = new URL(href, window.location.origin);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return escapeHtmlAttr(parsed.href);
    }
  } catch (_err) {
    return "#";
  }
  return "#";
}

export function renderMarkdown(md) {
  const lines = md.split(/\r?\n/);
  const out = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };

  const inline = (text) => {
    let x = escapeHtml(text);
    x = x.replace(
      /\[(.*?)\]\((.*?)\)/g,
      (_m, label, href) =>
        `<a href="${sanitizeHref(href)}" target="_blank" rel="noopener noreferrer">${label}</a>`
    );
    x = x.replace(/`([^`]+)`/g, "<code>$1</code>");
    x = x.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    return x;
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      continue;
    }
    if (trimmed === "---") {
      closeList();
      out.push("<hr/>");
      continue;
    }
    if (trimmed.startsWith("### ")) {
      closeList();
      out.push(`<h3>${inline(trimmed.slice(4))}</h3>`);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      closeList();
      out.push(`<h2>${inline(trimmed.slice(3))}</h2>`);
      continue;
    }
    if (trimmed.startsWith("# ")) {
      closeList();
      out.push(`<h1>${inline(trimmed.slice(2))}</h1>`);
      continue;
    }
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${inline(trimmed.slice(2))}</li>`);
      continue;
    }
    closeList();
    out.push(`<p>${inline(trimmed)}</p>`);
  }

  closeList();
  return out.join("\n");
}
