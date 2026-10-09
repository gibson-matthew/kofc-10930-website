import { Fragment, memo, useLayoutEffect, useRef } from "react";
import { useContentActions, useContentState } from "../content/ContentContext";

const CHIP_TAGS = new Set(["h1", "h2", "h3", "p", "li", "div"]);

function joinClass(...parts) {
  return parts.filter(Boolean).join(" ");
}

function textWithoutMark(el) {
  let out = "";
  for (const node of el.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) out += node.textContent;
    else if (node.nodeType !== 1) continue;
    else if (node.classList.contains("edit-mark") || node.classList.contains("inline-input")) continue;
    else if (node.tagName === "BR") out += "\n";
    else out += textWithoutMark(node);
  }
  return out;
}

function readLines(el) {
  const chunks = [];
  function walk(node) {
    for (const child of node.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) chunks.push(child.textContent);
      else if (child.nodeType !== 1 || child.classList.contains("edit-mark") || child.classList.contains("inline-input")) continue;
      else if (child.tagName === "BR") chunks.push("\n");
      else {
        if ((child.tagName === "DIV" || child.tagName === "P") && chunks.length && chunks[chunks.length - 1] !== "\n") {
          chunks.push("\n");
        }
        walk(child);
      }
    }
  }
  walk(el);
  return chunks
    .join("")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^\n+|\n+$/g, "");
}

function insertPlainText(text) {
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount) return;
  const range = selection.getRangeAt(0);
  range.deleteContents();
  const node = document.createTextNode(text);
  range.insertNode(node);
  range.setStartAfter(node);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
}

function ensureChip(el) {
  if (el.querySelector(":scope > .edit-mark")) return;
  const mark = document.createElement("button");
  mark.type = "button";
  mark.className = "edit-mark";
  mark.setAttribute("contenteditable", "false");
  mark.setAttribute("aria-hidden", "true");
  mark.tabIndex = -1;
  mark.textContent = "Edit";
  mark.addEventListener("mousedown", (event) => event.preventDefault());
  mark.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (el.focus) el.focus();
  });
  el.appendChild(mark);
}

function fillEditable(el, value, lines, chip) {
  while (el.firstChild) el.removeChild(el.firstChild);
  if (lines) {
    const parts = String(value ?? "").replace(/\r\n?/g, "\n").split("\n");
    parts.forEach((line, index) => {
      if (index) el.appendChild(document.createElement("br"));
      el.appendChild(document.createTextNode(line));
    });
  } else {
    el.appendChild(document.createTextNode(String(value ?? "")));
  }
  if (chip) ensureChip(el);
}

function ReadValue({ value, lines, Tag, className, style, htmlId, href, target, rel, onClick, ariaExpanded, ariaControls }) {
  if (href != null) {
    return (
      <a
        id={htmlId}
        className={className}
        style={style}
        href={href}
        target={target}
        rel={rel}
        onClick={onClick}
        aria-expanded={ariaExpanded}
        aria-controls={ariaControls}
      >
        {value}
      </a>
    );
  }
  if (Tag === "button") {
    return (
      <button
        id={htmlId}
        type="button"
        className={className}
        style={style}
        onClick={onClick}
        aria-expanded={ariaExpanded}
        aria-controls={ariaControls}
      >
        {value}
      </button>
    );
  }
  if (lines) {
    const parts = String(value ?? "").split("\n");
    return (
      <Tag id={htmlId} className={className} style={style}>
        {parts.map((line, index) => (
          <Fragment key={index}>
            {index > 0 ? <br /> : null}
            {line}
          </Fragment>
        ))}
      </Tag>
    );
  }
  return (
    <Tag id={htmlId} className={className} style={style}>
      {value}
    </Tag>
  );
}

function sameStyle(left, right) {
  if (left === right) return true;
  if (!left || !right) return !left && !right;
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) return false;
  return leftKeys.every((key) => left[key] === right[key]);
}

function editorPropsEqual(prev, next) {
  return (
    prev.blockKey === next.blockKey &&
    prev.Tag === next.Tag &&
    prev.className === next.className &&
    prev.htmlId === next.htmlId &&
    prev.lines === next.lines &&
    prev.chip === next.chip &&
    prev.href === next.href &&
    prev.target === next.target &&
    prev.rel === next.rel &&
    prev.ariaExpanded === next.ariaExpanded &&
    prev.ariaControls === next.ariaControls &&
    prev.revision === next.revision &&
    sameStyle(prev.style, next.style)
  );
}

const EditText = memo(function EditText({ blockKey, Tag, className, style, htmlId, lines, chip }) {
  const { draftText, setDraft } = useContentActions();
  const ref = useRef(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const current = lines ? readLines(el) : textWithoutMark(el);
    const next = String(draftText(blockKey) ?? "");
    if (current !== next) fillEditable(el, next, lines, chip);
    else if (chip && !el.querySelector(":scope > .edit-mark")) ensureChip(el);
  });

  function publish() {
    if (!ref.current) return;
    const raw = lines ? readLines(ref.current) : textWithoutMark(ref.current);
    setDraft(blockKey, raw);
    if (chip) ensureChip(ref.current);
  }

  return (
    <Tag
      ref={ref}
      id={htmlId}
      className={joinClass(className, "inline-edit", lines && "inline-edit-lines", chip && "has-chip")}
      style={style}
      contentEditable
      suppressContentEditableWarning
      spellCheck={false}
      onInput={publish}
      onBlur={publish}
      onKeyDown={(event) => {
        if (event.key === "Enter" && !lines) event.preventDefault();
      }}
      onMouseDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        if (event.currentTarget.closest("a")) event.preventDefault();
      }}
      onBeforeInput={(event) => {
        const blocked = [
          "formatBold",
          "formatItalic",
          "formatUnderline",
          "insertUnorderedList",
          "insertOrderedList",
          "insertHorizontalRule",
        ];
        if (blocked.includes(event.inputType)) event.preventDefault();
      }}
      onPaste={(event) => {
        event.preventDefault();
        let pasted = event.clipboardData ? event.clipboardData.getData("text/plain") || "" : "";
        if (!lines) pasted = pasted.replace(/[ \t\f\v\u00a0]+/g, " ").replace(/^\s+|\s+$/g, "");
        else pasted = pasted.replace(/\r\n?/g, "\n");
        insertPlainText(pasted);
        publish();
      }}
    />
  );
}, editorPropsEqual);

const EditControl = memo(function EditControl({ blockKey, className, style, htmlId, href, target, rel, ariaExpanded, ariaControls }) {
  const { draftText, setDraft } = useContentActions();
  const inputRef = useRef(null);

  useLayoutEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    const next = String(draftText(blockKey) ?? "");
    if (document.activeElement === input) return;
    if (input.value !== next) {
      input.value = next;
      input.size = Math.max(4, Math.min(48, input.value.length + 1));
    }
  });

  const input = (
    <input
      ref={inputRef}
      className="inline-input"
      type="text"
      defaultValue={draftText(blockKey)}
      autoComplete="off"
      aria-label="Edit text"
      onMouseDown={(event) => event.stopPropagation()}
      onClick={(event) => event.stopPropagation()}
      onInput={(event) => {
        const field = event.currentTarget;
        field.size = Math.max(4, Math.min(48, field.value.length + 1));
        setDraft(blockKey, field.value);
      }}
    />
  );

  if (href != null) {
    return (
      <a
        id={htmlId}
        className={joinClass(className, "inline-edit-control")}
        style={style}
        href={href}
        target={target}
        rel={rel}
        onMouseDown={(event) => {
          if (event.target !== inputRef.current) event.preventDefault();
        }}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          inputRef.current?.focus();
        }}
      >
        {input}
      </a>
    );
  }

  return (
    <button
      id={htmlId}
      type="button"
      className={joinClass(className, "inline-edit-control")}
      style={style}
      aria-expanded={ariaExpanded}
      aria-controls={ariaControls}
      onMouseDown={(event) => {
        if (event.target !== inputRef.current) event.preventDefault();
      }}
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        inputRef.current?.focus();
      }}
    >
      {input}
    </button>
  );
}, editorPropsEqual);

export function Block({
  id,
  as,
  className,
  style,
  htmlId,
  lines = false,
  href,
  control = false,
  locked = false,
  onClick,
  target,
  rel,
  chip,
  ariaExpanded,
  ariaControls,
}) {
  const { editing, epoch } = useContentState();
  const { text } = useContentActions();
  const isControl = control || href != null;
  const Tag = as || (isControl ? (href != null ? "a" : "button") : "span");
  const showChip = chip != null ? chip : CHIP_TAGS.has(Tag) && !isControl;

  if (!editing || locked) {
    return (
      <ReadValue
        value={text(id)}
        lines={lines}
        Tag={isControl && href == null ? "button" : Tag}
        className={className}
        style={style}
        htmlId={htmlId}
        href={href}
        target={target}
        rel={rel}
        onClick={onClick}
        ariaExpanded={ariaExpanded}
        ariaControls={ariaControls}
      />
    );
  }

  if (isControl) {
    return (
      <EditControl
        blockKey={id}
        className={className}
        style={style}
        htmlId={htmlId}
        href={href}
        target={target}
        rel={rel}
        ariaExpanded={ariaExpanded}
        ariaControls={ariaControls}
        revision={epoch}
      />
    );
  }

  return (
    <EditText
      blockKey={id}
      Tag={Tag}
      className={className}
      style={style}
      htmlId={htmlId}
      lines={lines}
      chip={showChip}
      revision={epoch}
    />
  );
}

export function Eyebrow({ id, className = "eyebrow", style }) {
  const { editing } = useContentState();
  const { text } = useContentActions();
  if (!editing) {
    return (
      <div className={className} style={style}>
        {text(id)}
      </div>
    );
  }
  return (
    <div className={joinClass(className, "has-chip")} style={style}>
      <Block id={id} className="text-part" chip={false} />
      <button
        type="button"
        className="edit-mark"
        contentEditable={false}
        aria-hidden="true"
        tabIndex={-1}
        onMouseDown={(event) => event.preventDefault()}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          event.currentTarget.parentElement?.querySelector(".inline-edit")?.focus();
        }}
      >
        Edit
      </button>
    </div>
  );
}
