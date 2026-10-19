import { useEffect, useRef, useState } from "react";
import { deleteAnnouncement, fetchAnnouncements, saveAnnouncement } from "../api";
import RichTextEditor from "../components/RichTextEditor";
import { ANNOUNCEMENT_EXAMPLES } from "../content/announcements";
import { MONTHS, collapse } from "../content/records";
import { htmlText, sanitizeHtml } from "../sanitizeHtml";

function formatPostedOn(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
  if (!match) return "";
  const month = MONTHS[Number(match[2]) - 1];
  if (!month) return "";
  return `${month} ${Number(match[3])}, ${match[1]}`;
}

function searchText(item) {
  const shownDate = formatPostedOn(item.posted_on);
  return collapse(`${item.title || ""} ${item.summary || ""} ${shownDate} ${item.posted_on || ""}`)
    .toLowerCase()
    .replace(/[\u2013\u2014-]/g, "-");
}

function AnnouncementForm({ initial, pending, onSave, onCancel, onError }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [summary, setSummary] = useState(initial?.summary || "");
  const editorRef = useRef(null);

  function submit(event) {
    event.preventDefault();
    if (pending) return;
    const cleanedTitle = collapse(title);
    const cleanedSummary = collapse(summary);
    if (!cleanedTitle) {
      onError("Enter a title.");
      return;
    }
    if (cleanedTitle.length > 120) {
      onError("Title must be 120 characters or fewer.");
      return;
    }
    if (cleanedSummary.length > 280) {
      onError("Summary must be 280 characters or fewer.");
      return;
    }
    const body = sanitizeHtml(editorRef.current ? editorRef.current.innerHTML : "");
    if (!htmlText(body)) {
      onError("Enter the announcement.");
      return;
    }
    if (body.length > 20000) {
      onError("Announcement is too long.");
      return;
    }
    onSave({ title: cleanedTitle, summary: cleanedSummary, body });
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
      </label>
      <label className="signin-field">
        <span>Summary</span>
        <input
          type="text"
          maxLength={280}
          value={summary}
          disabled={pending}
          onChange={(event) => setSummary(event.target.value)}
        />
        <p className="settings-hint">Optional.</p>
      </label>
      <div className="signin-field">
        <span>Body</span>
        <RichTextEditor
          editorRef={editorRef}
          initial={initial?.body || ""}
          disabled={pending}
          onError={onError}
        />
      </div>
      <div className="signin-actions recog-actions">
        <button type="submit" className="btn" disabled={pending}>
          Save announcement
        </button>
        <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function AnnouncementList({ canManage }) {
  const [items, setItems] = useState([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [query, setQuery] = useState("");
  const manage = Boolean(canManage) && !fallback;

  useEffect(() => {
    let cancel = false;
    setLoaded(false);
    fetchAnnouncements()
      .then((rows) => {
        if (cancel) return;
        setItems(Array.isArray(rows) ? rows : []);
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setItems(ANNOUNCEMENT_EXAMPLES);
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!manage) {
      setAdding(false);
      setEditing(null);
      setConfirmId(null);
    }
  }, [manage]);

  async function reload() {
    const rows = await fetchAnnouncements();
    setItems(Array.isArray(rows) ? rows : []);
    setFallback(false);
  }

  async function onSave(fields) {
    setPending(true);
    setError("");
    try {
      await saveAnnouncement(fields, editing ? editing.id : null);
      setAdding(false);
      setEditing(null);
      try {
        await reload();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Saved, but the list could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the announcement.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove(id) {
    setPending(true);
    setError("");
    try {
      await deleteAnnouncement(id);
      setConfirmId(null);
      setItems((current) => current.filter((item) => item.id !== id));
      try {
        await reload();
      } catch {
        /* The removed announcement is already hidden. */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the announcement.");
    } finally {
      setPending(false);
    }
  }

  const needle = searchText({ title: query, summary: "", posted_on: "" });
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
      {manage && !formOpen ? (
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
            Add announcement
          </button>
        </div>
      ) : null}
      {manage && formOpen ? (
        <AnnouncementForm
          key={editing ? `edit-${editing.id}` : "new"}
          initial={editing || { title: "", summary: "", body: "" }}
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
            placeholder="Title, date, or summary"
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
                const href = `/member/announcements/${encodeURIComponent(item.id)}`;
                return (
                  <li key={item.id}>
                    <h3>
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {item.title}
                      </a>
                    </h3>
                    {item.posted_on ? <p>{formatPostedOn(item.posted_on)}</p> : null}
                    {item.summary ? <p>{item.summary}</p> : null}
                    <div className="signin-actions recog-actions">
                      <a className="btn" href={href} target="_blank" rel="noopener noreferrer">
                        Read
                      </a>
                      {manage ? (
                        confirming ? (
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
                          </>
                        )
                      ) : null}
                    </div>
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
