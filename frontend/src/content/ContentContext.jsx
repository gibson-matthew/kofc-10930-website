import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { fetchPage, saveMember } from "../api";
import { memberBlocks, publicBlocks, serialize, toMap } from "./seed";

const StateContext = createContext(null);
const ActionsContext = createContext(null);
const LOCAL_KEY = "koc10930.member.blocks";

export function collapse(value) {
  return String(value ?? "")
    .replace(/[ \t\f\v\u00a0]+/g, " ")
    .replace(/^\s+|\s+$/g, "");
}

function normalizeValue(fieldType, value) {
  if (fieldType === "lines") {
    return String(value ?? "")
      .replace(/\r\n?/g, "\n")
      .replace(/^\n+|\n+$/g, "");
  }
  return collapse(value);
}

function readLocal() {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeLocal(map) {
  try {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(map));
  } catch {
    /* Private mode still keeps the text in memory for this visit. */
  }
}

function overlay(blocks, extra) {
  const map = toMap(blocks);
  if (!extra) return map;
  for (const block of blocks) {
    if (typeof extra[block.key] === "string") map[block.key] = extra[block.key];
  }
  return map;
}

export function ContentProvider({ slug, children }) {
  const blocks = slug === "member" ? memberBlocks : publicBlocks;
  const blocksRef = useRef(blocks);
  blocksRef.current = blocks;
  const [saved, setSaved] = useState(() =>
    slug === "member" ? overlay(blocks, readLocal()) : toMap(blocks),
  );
  const savedRef = useRef(saved);
  savedRef.current = saved;
  const draftRef = useRef(saved);
  const [editing, setEditing] = useState(false);
  const editingRef = useRef(false);
  const [epoch, setEpoch] = useState(0);
  const [savedFlash, setSavedFlash] = useState(false);
  const [saveCount, setSaveCount] = useState(0);

  useEffect(() => {
    let cancel = false;
    fetchPage(slug)
      .then((page) => {
        if (cancel || editingRef.current) return;
        const incoming = {};
        for (const block of page.blocks || []) {
          if (typeof block.value === "string") incoming[block.key] = block.value;
        }
        const map = overlay(blocksRef.current, incoming);
        setSaved(map);
        draftRef.current = map;
        if (slug === "member") writeLocal(map);
      })
      .catch(() => {
        /* Seed and any local member edits stay on screen. */
      });
    return () => {
      cancel = true;
    };
  }, [slug]);

  useEffect(() => {
    if (!savedFlash) return undefined;
    const timer = window.setTimeout(() => setSavedFlash(false), 2200);
    return () => window.clearTimeout(timer);
  }, [savedFlash, saveCount]);

  useEffect(() => {
    document.body.classList.toggle("is-editing", editing);
    return () => document.body.classList.remove("is-editing");
  }, [editing]);

  const actionsRef = useRef(null);
  if (!actionsRef.current) {
    actionsRef.current = {
      text(id) {
        return savedRef.current[id] ?? "";
      },
      draftText(id) {
        if (Object.prototype.hasOwnProperty.call(draftRef.current, id)) {
          return draftRef.current[id];
        }
        return savedRef.current[id] ?? "";
      },
      setDraft(id, value) {
        draftRef.current = { ...draftRef.current, [id]: value };
      },
      startEdit() {
        draftRef.current = { ...savedRef.current };
        editingRef.current = true;
        setEditing(true);
        setEpoch((value) => value + 1);
      },
      cancelEdit() {
        draftRef.current = { ...savedRef.current };
        editingRef.current = false;
        setEditing(false);
        setSavedFlash(false);
      },
      async saveEdits() {
        const next = { ...savedRef.current };
        for (const block of blocksRef.current) {
          const raw = Object.prototype.hasOwnProperty.call(draftRef.current, block.key)
            ? draftRef.current[block.key]
            : next[block.key];
          next[block.key] = normalizeValue(block.field_type, raw);
        }
        draftRef.current = next;
        savedRef.current = next;
        setSaved(next);
        setEpoch((value) => value + 1);
        writeLocal(next);
        setSavedFlash(true);
        setSaveCount((value) => value + 1);
        try {
          await saveMember(serialize(blocksRef.current, next));
        } catch {
          /* The text is already stored in memory and localStorage. */
        }
      },
    };
  }

  const state = useMemo(
    () => ({
      editing: slug === "member" && editing,
      epoch,
      savedFlash,
      saved,
    }),
    [slug, editing, epoch, savedFlash, saved],
  );

  return (
    <ActionsContext.Provider value={actionsRef.current}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}

export function useContentActions() {
  const value = useContext(ActionsContext);
  if (!value) throw new Error("Content is unavailable");
  return value;
}

export function useContentState() {
  const value = useContext(StateContext);
  if (!value) throw new Error("Content is unavailable");
  return value;
}

export function useContent() {
  return { ...useContentState(), ...useContentActions() };
}
