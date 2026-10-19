import { useEffect, useState } from "react";
import { deletePrayer, fetchPrayers, savePrayer } from "../api";
import { PRAYER_EXAMPLES } from "../content/prayers";
import { MONTHS, collapse } from "../content/records";

function formatSubmittedOn(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
  if (!match) return "";
  const month = MONTHS[Number(match[2]) - 1];
  if (!month) return "";
  return `${month} ${Number(match[3])}, ${match[1]}`;
}

function stripTags(value) {
  return String(value || "")
    .replace(/\u0000/g, "")
    .replace(/<[^>]*>/g, "");
}

function cleanTitle(value) {
  return collapse(stripTags(value));
}

function cleanBody(value) {
  const lines = stripTags(value)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .map((line) => line.replace(/[ \t\f\v]+/g, " ").trim());
  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

function searchText(item) {
  return collapse(`${item.author_name || ""} ${item.title || ""} ${item.body || ""}`)
    .toLowerCase()
    .replace(/[\u2013\u2014-]/g, "-");
}

function numericId(id) {
  return /^\d+$/.test(String(id || ""));
}

function PrayerForm({ initial, pending, onSave, onCancel, onError }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [body, setBody] = useState(initial?.body || "");
  const editing = Boolean(initial?.id);

  function submit(event) {
    event.preventDefault();
    if (pending) return;
    const cleanedTitle = cleanTitle(title);
    const cleanedBody = cleanBody(body);
    if (cleanedTitle.length > 120) {
      onError("Title must be 120 characters or fewer.");
      return;
    }
    if (!cleanedBody) {
      onError("Enter the prayer request.");
      return;
    }
    if (cleanedBody.length > 2000) {
      onError("Prayer request must be 2000 characters or fewer.");
      return;
    }
    onSave({ title: cleanedTitle, body: cleanedBody });
  }

  return (
    <form className="doc-form" onSubmit={submit}>
      <label className="signin-field">
        <span>Title</span>
        <input
          type="text"
          maxLength={120}
          value={title}
          disabled={pending}
          onChange={(event) => setTitle(event.target.value)}
        />
        <p className="settings-hint">Optional.</p>
      </label>
      <label className="signin-field">
        <span>Prayer request</span>
        <textarea
          rows={6}
          maxLength={2000}
          value={body}
          disabled={pending}
          onChange={(event) => setBody(event.target.value)}
        />
      </label>
      <div className="signin-actions recog-actions">
        <button type="submit" className="btn" disabled={pending}>
          {editing ? "Save request" : "Add prayer request"}
        </button>
        <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function PrayerList({ isAdmin }) {
  const [items, setItems] = useState([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [query, setQuery] = useState("");
  const admin = Boolean(isAdmin) && !fallback;

  useEffect(() => {
    let cancel = false;
    setLoaded(false);
    fetchPrayers()
      .then((rows) => {
        if (cancel) return;
        setItems(Array.isArray(rows) ? rows : []);
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setItems(PRAYER_EXAMPLES);
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (fallback) {
      setAdding(false);
      setEditing(null);
      setConfirmId(null);
    }
  }, [fallback]);

  async function reload() {
    const rows = await fetchPrayers();
    setItems(Array.isArray(rows) ? rows : []);
    setFallback(false);
  }

  async function onSave(fields) {
    if (editing && !numericId(editing.id)) return;
    setPending(true);
    setError("");
    try {
      await savePrayer(fields, editing ? editing.id : null);
      setAdding(false);
      setEditing(null);
      try {
        await reload();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Saved, but the list could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the prayer request.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove(id) {
    if (!numericId(id)) return;
    setPending(true);
    setError("");
    try {
      await deletePrayer(id);
      setConfirmId(null);
      setItems((current) => current.filter((item) => item.id !== id));
      try {
        await reload();
      } catch {
        /* The removed request is already hidden. */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the prayer request.");
    } finally {
      setPending(false);
    }
  }

  const needle = searchText({ author_name: query, title: "", body: "" });
  const shown = needle ? items.filter((item) => searchText(item).includes(needle)) : items;
  const formOpen = Boolean(adding || editing);

  return (
    <>
      {fallback ? (
        <p className="settings-hint">Showing the example list while the council records are unavailable.</p>
      ) : null}
      {error ? (
        <p className="signin-error" role="alert">
          {error}
        </p>
      ) : null}
      {!loaded ? <p className="settings-hint">Loading…</p> : null}
      {!fallback && !formOpen ? (
        <div className="signin-actions recog-actions">
          <button
            type="button"
            className="btn"
            disabled={pending}
            onClick={() => {
              setError("");
              setConfirmId(null);
              setEditing(null);
              setAdding(true);
            }}
          >
            Add prayer request
          </button>
        </div>
      ) : null}
      {!fallback && formOpen ? (
        <PrayerForm
          key={editing ? `edit-${editing.id}` : "new"}
          initial={editing || { title: "", body: "" }}
          pending={pending}
          onError={setError}
          onCancel={() => {
            setAdding(false);
            setEditing(null);
          }}
          onSave={onSave}
        />
      ) : null}
      {loaded && items.length === 0 ? <p className="settings-hint">None recorded yet.</p> : null}
      {items.length > 0 ? (
        <label className="signin-field doc-search">
          <span>Search</span>
          <input
            type="search"
            value={query}
            placeholder="Name or prayer"
            autoComplete="off"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      ) : null}
      {items.length > 0 ? (
        <div className="doc-scroll">
          {needle && shown.length === 0 ? (
            <p className="settings-hint" role="status">
              No matches.
            </p>
          ) : (
            <ul className="doc-list">
              {shown.map((item) => {
                const confirming = confirmId === item.id;
                const canEdit = Boolean(item.mine) && !fallback;
                const canRemove = (Boolean(item.mine) || admin) && !fallback;
                return (
                  <li key={item.id}>
                    <h3>{item.author_name || "Member"}</h3>
                    {item.submitted_on ? <p>{formatSubmittedOn(item.submitted_on)}</p> : null}
                    {item.title ? <p>{item.title}</p> : null}
                    {item.body ? <p className="prayer-text">{item.body}</p> : null}
                    {canEdit || canRemove ? (
                      <div className="signin-actions recog-actions">
                        {confirming ? (
                          <>
                            <button type="button" className="btn" disabled={pending} onClick={() => onRemove(item.id)}>
                              Remove
                            </button>
                            <button
                              type="button"
                              className="btn btn-quiet"
                              disabled={pending}
                              onClick={() => setConfirmId(null)}
                            >
                              Keep
                            </button>
                          </>
                        ) : (
                          <>
                            {canEdit ? (
                              <button
                                type="button"
                                className="btn btn-quiet"
                                disabled={pending}
                                onClick={() => {
                                  setAdding(false);
                                  setConfirmId(null);
                                  setError("");
                                  setEditing(item);
                                }}
                              >
                                Edit
                              </button>
                            ) : null}
                            {canRemove ? (
                              <button
                                type="button"
                                className="btn btn-quiet"
                                disabled={pending}
                                onClick={() => {
                                  setAdding(false);
                                  setEditing(null);
                                  setConfirmId(item.id);
                                }}
                              >
                                Remove
                              </button>
                            ) : null}
                          </>
                        )}
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
    </>
  );
}
