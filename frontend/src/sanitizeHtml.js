const ALLOWED = new Set([
  "p",
  "br",
  "strong",
  "b",
  "em",
  "i",
  "u",
  "mark",
  "h2",
  "h3",
  "h4",
  "ul",
  "ol",
  "li",
  "a",
  "span",
  "div",
]);

const DROP = new Set([
  "script",
  "style",
  "iframe",
  "object",
  "embed",
  "noscript",
  "template",
  "svg",
  "math",
  "link",
  "meta",
  "form",
  "input",
  "button",
  "textarea",
  "select",
  "img",
  "video",
  "audio",
  "canvas",
]);

function safeColor(value) {
  if (/^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i.test(value)) return true;
  const match = /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i.exec(value);
  if (!match) return false;
  return match.slice(1).every((part) => Number(part) <= 255);
}

function safeStyle(value) {
  const kept = [];
  for (const part of String(value || "").split(";")) {
    const index = part.indexOf(":");
    if (index < 0) continue;
    const prop = part.slice(0, index).trim().toLowerCase();
    const val = part.slice(index + 1).trim().toLowerCase();
    if (/url|expression|javascript|\\|@|\/\*/.test(val)) continue;
    if (prop === "text-align" && (val === "left" || val === "center" || val === "right")) {
      kept.push(`text-align: ${val}`);
    } else if (prop === "background-color" && safeColor(val)) {
      kept.push(`background-color: ${val}`);
    } else if (prop === "font-weight" && (val === "bold" || val === "700")) {
      kept.push("font-weight: bold");
    } else if (prop === "font-style" && val === "italic") {
      kept.push("font-style: italic");
    } else if ((prop === "text-decoration" || prop === "text-decoration-line") && val === "underline") {
      kept.push("text-decoration: underline");
    }
  }
  return kept.join("; ");
}

export function safeHref(value) {
  const text = String(value || "").trim();
  if (!text || text.length > 500 || /[\u0000-\u001f\s]/.test(text)) return "";
  const lower = text.toLowerCase();
  if (lower.startsWith("https://") || lower.startsWith("http://")) return text;
  if (lower.startsWith("mailto:")) {
    const rest = text.slice(7);
    if (rest && rest.includes("@") && !rest.includes("/") && !rest.includes(" ")) return text;
  }
  return "";
}

function styleFor(source) {
  let style = safeStyle(source.getAttribute("style") || "");
  const align = String(source.getAttribute("align") || "").toLowerCase();
  if ((align === "left" || align === "center" || align === "right") && !style.includes("text-align:")) {
    style = style ? `${style}; text-align: ${align}` : `text-align: ${align}`;
  }
  return style;
}

function walk(node, out, depth) {
  if (node.nodeType === Node.TEXT_NODE) {
    out.appendChild(document.createTextNode(node.textContent || ""));
    return;
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return;
  const tag = node.tagName.toLowerCase();
  if (DROP.has(tag)) return;
  if (!ALLOWED.has(tag) || depth > 12) {
    for (const child of node.childNodes) walk(child, out, depth + 1);
    return;
  }
  if (tag === "a") {
    const href = safeHref(node.getAttribute("href"));
    if (!href) {
      for (const child of node.childNodes) walk(child, out, depth + 1);
      return;
    }
    const link = document.createElement("a");
    link.setAttribute("href", href);
    if (href.toLowerCase().startsWith("http://") || href.toLowerCase().startsWith("https://")) {
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");
    }
    const style = styleFor(node);
    if (style) link.setAttribute("style", style);
    for (const child of node.childNodes) walk(child, link, depth + 1);
    out.appendChild(link);
    return;
  }
  const el = document.createElement(tag);
  const style = styleFor(node);
  if (style) el.setAttribute("style", style);
  if (tag !== "br") {
    for (const child of node.childNodes) walk(child, el, depth + 1);
  }
  out.appendChild(el);
}

export function sanitizeHtml(value) {
  const raw = String(value || "").replace(/\u0000/g, "");
  const limited = raw.length > 40000 ? raw.slice(0, 40000) : raw;
  let doc;
  try {
    doc = new DOMParser().parseFromString(limited, "text/html");
  } catch {
    return "";
  }
  const clean = document.createElement("div");
  for (const child of doc.body.childNodes) walk(child, clean, 1);
  const html = clean.innerHTML.trim();
  return html.length > 20000 ? html.slice(0, 20000) : html;
}

export function htmlText(value) {
  let doc;
  try {
    doc = new DOMParser().parseFromString(sanitizeHtml(value), "text/html");
  } catch {
    return "";
  }
  return String(doc.body.textContent || "").replace(/\s+/g, " ").trim();
}
