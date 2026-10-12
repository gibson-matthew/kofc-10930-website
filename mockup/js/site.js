/* Demo sign-in on the public page. Copy editing runs on the member page only. Text is stored as text, never as HTML. */
(function () {
  "use strict";

  var PAGE = document.body.getAttribute("data-page") || "page";
  var COPY_KEY = "koc10930.copy.v1";
  var SELECTOR = [
    "h1",
    "h2",
    "h3",
    "p",
    "li",
    ".eyebrow",
    ".place",
    ".yr",
    ".role",
    ".when",
    ".sub",
    ".name",
    ".profile-name",
    ".more",
    ".stat b",
    ".stat span",
    ".footer-bottom span",
    "a.btn",
    "button.btn",
    ".footer-nav a",
    ".banner-stripe",
    "strong",
    "p a"
  ].join(",");

  var editMode = false;
  var registry = [];
  var savedTimer = 0;

  function readJSON(key) {
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return {};
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
      return parsed;
    } catch (err) {
      return {};
    }
  }

  function writeJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
      /* Private mode or a full store: the page still shows the saved text. */
    }
  }

  function collapse(value) {
    return String(value == null ? "" : value).replace(/[ \t\f\v\u00a0]+/g, " ").replace(/^\s+|\s+$/g, "");
  }

  function excluded(el) {
    if (!el || el.nodeType !== 1) return true;
    if (el.closest("svg, .corner, .signin-dialog, .profile-menu, .carousel-dots, .carousel-btn, .nav-toggle, .copy-dialog, .save-status, .edit-mark")) return true;
    if (el.id === "signInBtn" || el.id === "editToggle" || el.id === "saveEdits" || el.id === "signInCancel") return true;
    if (el.classList.contains("edit-toggle") || el.classList.contains("save-edits") || el.classList.contains("nav-toggle") || el.classList.contains("carousel-btn") || el.classList.contains("nav-signin")) return true;
    if (el.closest("header") && el.closest("nav")) return true;
    return false;
  }

  function keyFor(el) {
    var parts = [];
    var node = el;
    while (node && node.nodeType === 1 && node !== document.body) {
      var part = node.tagName.toLowerCase();
      var parent = node.parentElement;
      if (parent) {
        var index = 0;
        var count = 0;
        for (var i = 0; i < parent.children.length; i++) {
          var sibling = parent.children[i];
          if (sibling.tagName !== node.tagName) continue;
          if (sibling.classList.contains("copy-edit") || sibling.classList.contains("edit-mark") || sibling.classList.contains("text-part") || sibling.classList.contains("inline-input")) continue;
          if (sibling === node) index = count;
          count++;
        }
        if (count > 1) part += "[" + index + "]";
      }
      parts.unshift(part);
      if (node.id) {
        parts[0] = node.tagName.toLowerCase() + "#" + node.id;
        break;
      }
      node = node.parentElement;
    }
    return PAGE + ":" + parts.join(">");
  }

  function lineBreakOnly(el) {
    if (!el.children.length) return false;
    for (var i = 0; i < el.children.length; i++) {
      if (el.children[i].tagName !== "BR") return false;
    }
    return true;
  }

  function textWithoutMark(el) {
    var out = "";
    for (var i = 0; i < el.childNodes.length; i++) {
      var n = el.childNodes[i];
      if (n.nodeType === 3) out += n.textContent;
      else if (n.nodeType === 1 && (n.classList.contains("edit-mark") || n.classList.contains("inline-input"))) continue;
      else if (n.nodeType === 1 && n.tagName === "BR") out += "\n";
      else if (n.nodeType === 1) out += textWithoutMark(n);
    }
    return out;
  }

  function readLines(el) {
    var chunks = [];
    function walk(node) {
      for (var i = 0; i < node.childNodes.length; i++) {
        var n = node.childNodes[i];
        if (n.nodeType === 3) chunks.push(n.textContent);
        else if (n.nodeType !== 1 || n.classList.contains("edit-mark") || n.classList.contains("inline-input")) continue;
        else if (n.tagName === "BR") chunks.push("\n");
        else {
          if ((n.tagName === "DIV" || n.tagName === "P") && chunks.length && chunks[chunks.length - 1] !== "\n") chunks.push("\n");
          walk(n);
        }
      }
    }
    walk(el);
    return chunks.join("").replace(/\u00a0/g, " ").replace(/[ \t]+\n/g, "\n").replace(/\n[ \t]+/g, "\n").replace(/\n{3,}/g, "\n\n").replace(/^\n+|\n+$/g, "");
  }

  function writeLines(el, value) {
    var lines = String(value == null ? "" : value).replace(/\r\n?/g, "\n").split("\n");
    while (el.firstChild) el.removeChild(el.firstChild);
    for (var n = 0; n < lines.length; n++) {
      if (n) el.appendChild(document.createElement("br"));
      el.appendChild(document.createTextNode(lines[n].replace(/[ \t\f\v\u00a0]+/g, " ").replace(/^\s+|\s+$/g, "")));
    }
  }

  function readItem(item) {
    if (item.input) return item.input.value;
    if (item.kind === "lines") return readLines(item.el);
    if (item.kind === "part") return collapse(item.el.textContent);
    return collapse(textWithoutMark(item.el));
  }

  function writeItem(item, value) {
    if (item.kind === "part") {
      var clean = collapse(value);
      item.el.textContent = clean ? item.lead + clean + item.tail : "";
      return;
    }
    if (item.kind === "lines") {
      writeLines(item.el, value);
      return;
    }
    item.el.textContent = collapse(value);
  }

  function buildRegistry() {
    var list = [];
    var seen = [];
    var nodes = document.querySelectorAll(SELECTOR);
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (seen.indexOf(el) !== -1) continue;
      if (excluded(el)) continue;
      seen.push(el);
      if (el.classList.contains("eyebrow")) {
        var eyebrowText = collapse(el.textContent);
        if (!eyebrowText) continue;
        var holder = document.createElement("span");
        holder.className = "text-part";
        while (el.firstChild) holder.appendChild(el.firstChild);
        el.appendChild(holder);
        list.push({ el: holder, key: keyFor(el), kind: "plain", seed: eyebrowText, lead: "", tail: "", input: null });
        continue;
      }
      if (el.tagName === "A" || el.tagName === "BUTTON") {
        var label = collapse(el.textContent);
        if (!label) continue;
        list.push({ el: el, key: keyFor(el), kind: "control", seed: label, lead: "", tail: "", input: null });
        continue;
      }
      if (lineBreakOnly(el)) {
        var lines = readLines(el);
        if (!collapse(lines)) continue;
        list.push({ el: el, key: keyFor(el), kind: "lines", seed: lines, lead: "", tail: "", input: null });
        continue;
      }
      if (el.children.length === 0) {
        var plain = collapse(el.textContent);
        if (!plain) continue;
        list.push({ el: el, key: keyFor(el), kind: "plain", seed: plain, lead: "", tail: "", input: null });
        continue;
      }
      var parentKey = keyFor(el);
      var textNodes = [];
      for (var c = 0; c < el.childNodes.length; c++) {
        var node = el.childNodes[c];
        if (node.nodeType === 3 && node.textContent.replace(/\s+/g, "").length) textNodes.push(node);
      }
      for (var t = 0; t < textNodes.length; t++) {
        var raw = textNodes[t].textContent;
        var seed = collapse(raw);
        if (!seed) continue;
        var span = document.createElement("span");
        span.className = "text-part";
        textNodes[t].parentNode.insertBefore(span, textNodes[t]);
        span.appendChild(textNodes[t]);
        list.push({
          el: span,
          key: parentKey + "::" + t,
          kind: "part",
          seed: seed,
          lead: (raw.match(/^\s*/) || [""])[0],
          tail: (raw.match(/\s*$/) || [""])[0],
          input: null
        });
      }
    }
    return list;
  }

  function applyStored() {
    var store = readJSON(COPY_KEY);
    for (var i = 0; i < registry.length; i++) {
      var item = registry[i];
      var has = Object.prototype.hasOwnProperty.call(store, item.key) && typeof store[item.key] === "string";
      writeItem(item, has ? store[item.key] : item.seed);
    }
  }

  function allowChip(el) {
    if (el.closest("header, .signin-dialog")) return false;
    var tag = el.tagName;
    return tag === "H1" || tag === "H2" || tag === "H3" || tag === "P" || tag === "LI" || tag === "DIV";
  }

  function addChip(el) {
    var existing = el.children;
    for (var i = 0; i < existing.length; i++) {
      if (existing[i].classList.contains("edit-mark")) return;
    }
    el.classList.add("has-chip");
    var mark = document.createElement("button");
    mark.type = "button";
    mark.className = "edit-mark";
    mark.setAttribute("contenteditable", "false");
    mark.setAttribute("aria-hidden", "true");
    mark.tabIndex = -1;
    mark.textContent = "Edit";
    el.appendChild(mark);
  }

  function fitInput(input) {
    input.size = Math.max(4, Math.min(48, input.value.length + 1));
  }

  function armControl(item) {
    var el = item.el;
    var value = readItem(item);
    el.textContent = "";
    var input = document.createElement("input");
    input.type = "text";
    input.className = "inline-input";
    input.value = value;
    input.autocomplete = "off";
    input.setAttribute("aria-label", "Edit text");
    fitInput(input);
    input.addEventListener("input", function () { fitInput(input); });
    el.appendChild(input);
    item.input = input;
    el.classList.add("inline-edit-control");
  }

  function armItem(item) {
    if (item.kind === "control") {
      armControl(item);
      return;
    }
    var el = item.el;
    el.setAttribute("contenteditable", "true");
    el.classList.add("inline-edit");
    if (item.kind === "lines") el.classList.add("inline-edit-lines");
    if (allowChip(el)) addChip(el);
    else if (el.parentElement && el.parentElement.classList.contains("eyebrow") && !el.parentElement.closest("header, .signin-dialog")) addChip(el.parentElement);
  }

  function armAll() {
    for (var i = 0; i < registry.length; i++) armItem(registry[i]);
  }

  function disarmAll() {
    var marks = document.querySelectorAll(".edit-mark");
    for (var i = marks.length - 1; i >= 0; i--) {
      if (marks[i].parentNode) marks[i].parentNode.removeChild(marks[i]);
    }
    var inputs = document.querySelectorAll(".inline-input");
    for (var j = inputs.length - 1; j >= 0; j--) {
      if (inputs[j].parentNode) inputs[j].parentNode.removeChild(inputs[j]);
    }
    var fields = document.querySelectorAll(".inline-edit, .inline-edit-control, .has-chip");
    for (var k = 0; k < fields.length; k++) {
      fields[k].classList.remove("inline-edit", "inline-edit-lines", "inline-edit-control", "has-chip");
      fields[k].removeAttribute("contenteditable");
    }
    for (var n = 0; n < registry.length; n++) registry[n].input = null;
  }

  function normalized(item, value) {
    if (item.kind === "lines") {
      return String(value == null ? "" : value).replace(/\r\n?/g, "\n").replace(/^\n+|\n+$/g, "");
    }
    return collapse(value);
  }

  function saveEdits() {
    var next = [];
    for (var i = 0; i < registry.length; i++) next.push(readItem(registry[i]));
    disarmAll();
    var store = readJSON(COPY_KEY);
    for (var j = 0; j < registry.length; j++) {
      var item = registry[j];
      var value = normalized(item, next[j]);
      writeItem(item, value);
      if (value === item.seed) delete store[item.key];
      else store[item.key] = value;
    }
    writeJSON(COPY_KEY, store);
    if (editMode) armAll();
    showSaved();
  }

  function updateChrome() {
    var toggle = document.getElementById("editToggle");
    if (toggle) {
      toggle.setAttribute("aria-pressed", editMode ? "true" : "false");
      toggle.textContent = editMode ? "Cancel changes" : "Edit Page";
      toggle.setAttribute("aria-label", editMode ? "Cancel changes" : "Edit page");
    }
    var save = document.getElementById("saveEdits");
    if (save) save.hidden = !editMode;
    document.body.classList.toggle("is-editing", editMode);
  }

  function setEditMode(on) {
    if (editMode && !on) {
      disarmAll();
      applyStored();
      hideSaved();
    }
    editMode = on;
    updateChrome();
    if (on) armAll();
  }

  function ensureStatus() {
    var status = document.getElementById("saveStatus");
    if (status) return status;
    status = document.createElement("div");
    status.id = "saveStatus";
    status.className = "save-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.hidden = true;
    document.body.appendChild(status);
    return status;
  }

  function showSaved() {
    var status = ensureStatus();
    status.textContent = "Saved";
    status.hidden = false;
    window.clearTimeout(savedTimer);
    savedTimer = window.setTimeout(hideSaved, 2200);
  }

  function hideSaved() {
    window.clearTimeout(savedTimer);
    var status = document.getElementById("saveStatus");
    if (status) status.hidden = true;
  }

  function eventElement(event) {
    var node = event && event.target;
    if (!node) return null;
    if (node.nodeType !== 1) node = node.parentElement;
    return node && node.closest ? node : null;
  }

  function insertText(text) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;
    var range = sel.getRangeAt(0);
    range.deleteContents();
    var node = document.createTextNode(text);
    range.insertNode(node);
    range.setStartAfter(node);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }

  function closeSignIn(dialog, form) {
    form.reset();
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function bindSignIn() {
    var btn = document.getElementById("signInBtn");
    var dialog = document.getElementById("signInDialog");
    var form = document.getElementById("signInForm");
    var cancel = document.getElementById("signInCancel");
    if (!btn || !dialog || !form || !cancel) return;

    btn.addEventListener("click", function () {
      var nav = document.getElementById("primaryNav");
      var navToggle = document.getElementById("navToggle");
      if (nav) nav.classList.remove("open");
      if (navToggle) navToggle.setAttribute("aria-expanded", "false");
      if (typeof dialog.showModal === "function") {
        if (!dialog.open) dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
      var first = form.querySelector("input");
      if (first) first.focus();
    });

    cancel.addEventListener("click", function () {
      closeSignIn(dialog, form);
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      window.location.href = "member_mockup.html";
    });

    dialog.addEventListener("close", function () {
      form.reset();
    });
  }

  function bindEditing() {
    var toggle = document.getElementById("editToggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        setEditMode(!editMode);
      });
    }
    var save = document.getElementById("saveEdits");
    if (save) {
      save.addEventListener("click", function () {
        saveEdits();
      });
    }

    document.addEventListener("mousedown", function (event) {
      if (!editMode) return;
      var el = eventElement(event);
      if (!el) return;
      var control = el.closest(".inline-edit-control");
      if (control) {
        if (!el.classList.contains("inline-input")) {
          event.preventDefault();
          var input = control.querySelector(".inline-input");
          if (input) input.focus();
        }
        return;
      }
      var editable = el.closest(".inline-edit");
      if (!editable) return;
      var parentControl = editable.closest("a, button");
      if (parentControl && parentControl !== editable) event.stopPropagation();
    }, true);

    document.addEventListener("click", function (event) {
      if (!editMode) return;
      var el = eventElement(event);
      if (!el) return;
      var mark = el.closest(".edit-mark");
      if (mark) {
        event.preventDefault();
        event.stopPropagation();
        if (mark.parentNode && mark.parentNode.focus) mark.parentNode.focus();
        return;
      }
      var control = el.closest(".inline-edit-control");
      if (control) {
        event.preventDefault();
        event.stopPropagation();
        var input = control.querySelector(".inline-input");
        if (input && document.activeElement !== input) input.focus();
        return;
      }
      var editable = el.closest(".inline-edit");
      if (!editable) return;
      var parentControl = editable.closest("a, button");
      if (parentControl && parentControl !== editable) {
        event.preventDefault();
        event.stopPropagation();
      }
    }, true);

    document.addEventListener("keydown", function (event) {
      if (!editMode || event.key !== "Enter") return;
      var el = eventElement(event);
      var field = el && el.closest(".inline-edit");
      if (!field || field.classList.contains("inline-edit-lines")) return;
      event.preventDefault();
    }, true);

    document.addEventListener("beforeinput", function (event) {
      if (!editMode) return;
      var el = eventElement(event);
      var field = el && el.closest(".inline-edit");
      if (!field) return;
      if (event.inputType === "formatBold" || event.inputType === "formatItalic" || event.inputType === "formatUnderline" || event.inputType === "insertUnorderedList" || event.inputType === "insertOrderedList" || event.inputType === "insertHorizontalRule") {
        event.preventDefault();
      }
    });

    document.addEventListener("paste", function (event) {
      var el = eventElement(event);
      var field = el && el.closest(".inline-edit");
      if (!field) return;
      event.preventDefault();
      var text = "";
      if (event.clipboardData) text = event.clipboardData.getData("text/plain") || "";
      if (!field.classList.contains("inline-edit-lines")) text = collapse(text);
      else text = text.replace(/\r\n?/g, "\n");
      insertText(text);
    });

    window.addEventListener("storage", function (event) {
      if (event.key !== COPY_KEY || editMode) return;
      applyStored();
    });

    window.addEventListener("pageshow", function () {
      if (!editMode) applyStored();
    });
  }

  bindSignIn();
  if (PAGE !== "member") return;
  registry = buildRegistry();
  applyStored();
  updateChrome();
  bindEditing();
})();
