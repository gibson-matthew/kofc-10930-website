import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { fetchPage, saveMember } from "../api";
import { memberBlocks, publicBlocks, serialize, toMap } from "./seed";
import { DEFAULT_YEAR, YEAR_KEY, withFraternalYear } from "./year";

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

export function ContentProvider({ slug, canEdit = false, children }) {
  const blocks = slug === "member" ? memberBlocks : publicBlocks;
  const blocksRef = useRef(blocks);
  blocksRef.current = blocks;
  const canEditRef = useRef(canEdit);
  canEditRef.current = canEdit;
  const [saved, setSaved] = useState(() =>
    slug === "member" && canEdit ? overlay(blocks, readLocal()) : toMap(blocks),
  );
  const savedRef = useRef(saved);
  savedRef.current = saved;
  const draftRef = useRef(saved);
  const [editing, setEditing] = useState(false);
  const editingRef = useRef(false);
  const [epoch, setEpoch] = useState(0);
  const saveQueue = useRef(Promise.resolve());

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
        if (slug === "member" && canEditRef.current) writeLocal(map);
      })
      .catch(() => {
        /* Seed and any local member edits stay on screen. */
      });
    return () => {
      cancel = true;
    };
  }, [slug, canEdit]);

  useEffect(() => {
    if (canEdit || !editingRef.current) return;
    draftRef.current = { ...savedRef.current };
    editingRef.current = false;
    setEditing(false);
  }, [canEdit]);

  useEffect(() => {
    document.body.classList.toggle("is-editing", editing);
    return () => document.body.classList.remove("is-editing");
  }, [editing]);

  const actionsRef = useRef(null);
  if (!actionsRef.current) {
    async function persistFields(ids) {
      if (!canEditRef.current) throw new Error("Admin access is required.");
      const keys = Array.isArray(ids) ? ids.filter(Boolean) : [];
      if (!keys.length) return;
      const savedBefore = savedRef.current;
      const draftBefore = draftRef.current;
      const next = { ...savedBefore };
      for (const id of keys) {
        if (id === YEAR_KEY) continue;
        const raw = Object.prototype.hasOwnProperty.call(draftBefore, id) ? draftBefore[id] : next[id];
        const block = blocksRef.current.find((item) => item.key === id);
        next[id] = normalizeValue(block ? block.field_type : "text", raw);
      }
      if (keys.includes(YEAR_KEY)) {
        const raw = Object.prototype.hasOwnProperty.call(draftBefore, YEAR_KEY)
          ? draftBefore[YEAR_KEY]
          : next[YEAR_KEY];
        const applied = withFraternalYear(next, raw);
        if (!applied) throw new Error("Use a fraternal year such as 2026\u201327.");
        Object.assign(next, applied);
      }
      await saveMember(serialize(blocksRef.current, next));
      const latest = draftRef.current;
      const merged = { ...next };
      for (const key of Object.keys(latest)) {
        const typedDuringSave = latest[key] !== draftBefore[key];
        if (keys.includes(key)) {
          if (typedDuringSave) merged[key] = latest[key];
          continue;
        }
        if (typedDuringSave || latest[key] !== savedBefore[key]) merged[key] = latest[key];
      }
      savedRef.current = next;
      draftRef.current = merged;
      setSaved(next);
      setEpoch((value) => value + 1);
      writeLocal(next);
    }

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
      setFraternalYear(raw) {
        const trimmed = String(raw ?? "").slice(0, 9);
        draftRef.current = { ...draftRef.current, [YEAR_KEY]: trimmed };
        setEpoch((value) => value + 1);
      },
      applyFraternalYear() {
        const raw = Object.prototype.hasOwnProperty.call(draftRef.current, YEAR_KEY)
          ? draftRef.current[YEAR_KEY]
          : DEFAULT_YEAR;
        const next = withFraternalYear(draftRef.current, raw);
        if (!next) throw new Error("Use a fraternal year such as 2026\u201327.");
        draftRef.current = next;
        setEpoch((value) => value + 1);
      },
      startEdit() {
        if (!canEditRef.current) return;
        draftRef.current = { ...savedRef.current };
        editingRef.current = true;
        setEditing(true);
        setEpoch((value) => value + 1);
      },
      exitEdit() {
        draftRef.current = { ...savedRef.current };
        editingRef.current = false;
        setEditing(false);
      },
      async saveFields(ids) {
        const job = saveQueue.current.then(() => persistFields(ids));
        saveQueue.current = job.then(
          () => undefined,
          () => undefined,
        );
        return job;
      },
    };
  }

  const state = useMemo(
    () => ({
      editing: Boolean(canEdit) && editing,
      epoch,
      saved,
    }),
    [canEdit, editing, epoch, saved],
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
