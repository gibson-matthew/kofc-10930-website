import { useRef } from "react";
import { htmlText, safeHref, sanitizeHtml } from "../sanitizeHtml";

const COMMANDS = [
  ["bold", "Bold"],
  ["italic", "Italic"],
  ["underline", "Underline"],
  ["highlight", "Highlight"],
  ["h2", "Heading"],
  ["h3", "Subheading"],
  ["p", "Text"],
  ["ul", "Bullets"],
  ["ol", "Numbered"],
  ["left", "Left"],
  ["center", "Center"],
  ["right", "Right"],
  ["link", "Link"],
];

function escapePlain(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function editorHtml(initial) {
  const clean = sanitizeHtml(initial);
  return htmlText(clean) ? clean : "<p><br></p>";
}

function selectionInside(node) {
  const selection = window.getSelection();
  if (!node || !selection || selection.rangeCount === 0) return false;
  return node.contains(selection.getRangeAt(0).commonAncestorContainer);
}

function highlightSelection(node) {
  const selection = window.getSelection();
  if (selection && selection.rangeCount && !selection.isCollapsed && selectionInside(node)) {
    const range = selection.getRangeAt(0);
    try {
      range.surroundContents(document.createElement("mark"));
      return;
    } catch {
      /* A selection that crosses blocks falls through to the color command. */
    }
  }
  document.execCommand("hiliteColor", false, "#F3E6B8");
}

function runCommand(command, node) {
  if (command === "bold") document.execCommand("bold");
  else if (command === "italic") document.execCommand("italic");
  else if (command === "underline") document.execCommand("underline");
  else if (command === "highlight") highlightSelection(node);
  else if (command === "h2") document.execCommand("formatBlock", false, "<h2>");
  else if (command === "h3") document.execCommand("formatBlock", false, "<h3>");
  else if (command === "p") document.execCommand("formatBlock", false, "<p>");
  else if (command === "ul") document.execCommand("insertUnorderedList");
  else if (command === "ol") document.execCommand("insertOrderedList");
  else if (command === "left") document.execCommand("justifyLeft");
  else if (command === "center") document.execCommand("justifyCenter");
  else if (command === "right") document.execCommand("justifyRight");
}

export default function RichTextEditor({ initial = "", disabled = false, onError, editorRef }) {
  const localRef = useRef(null);
  const ref = editorRef || localRef;
  const html = editorHtml(initial);

  function onPaste(event) {
    event.preventDefault();
    const data = event.clipboardData;
    const htmlClip = data ? data.getData("text/html") : "";
    const text = data ? data.getData("text/plain") : "";
    const fromHtml = htmlClip ? sanitizeHtml(htmlClip) : "";
    const clean = htmlText(fromHtml)
      ? fromHtml
      : sanitizeHtml(`<p>${escapePlain(text).replace(/\n/g, "<br>")}</p>`);
    if (clean && htmlText(clean)) document.execCommand("insertHTML", false, clean);
  }

  function onCommand(command) {
    const node = ref.current;
    if (!node || disabled) return;
    node.focus();
    if (command === "link") {
      const selection = window.getSelection();
      const range = selection && selection.rangeCount ? selection.getRangeAt(0).cloneRange() : null;
      const raw = window.prompt("Link address (https:// or mailto:)");
      if (raw == null || !String(raw).trim()) return;
      const href = safeHref(String(raw).trim());
      node.focus();
      if (range && selection) {
        selection.removeAllRanges();
        selection.addRange(range);
      }
      if (!href) {
        if (onError) onError("Enter an https:// or mailto: link.");
        return;
      }
      if (onError) onError("");
      document.execCommand("createLink", false, href);
      return;
    }
    if (onError) onError("");
    runCommand(command, node);
  }

  return (
    <div className="rte">
      <div className="rte-toolbar" role="toolbar" aria-label="Formatting">
        {COMMANDS.map(([command, label]) => (
          <button
            key={command}
            type="button"
            className="btn btn-quiet"
            disabled={disabled}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => onCommand(command)}
          >
            {label}
          </button>
        ))}
      </div>
      <div
        ref={ref}
        className="rte-editor"
        contentEditable={disabled ? "false" : "true"}
        role="textbox"
        aria-multiline="true"
        aria-label="Announcement"
        aria-disabled={disabled ? "true" : "false"}
        onPaste={onPaste}
        suppressContentEditableWarning
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
