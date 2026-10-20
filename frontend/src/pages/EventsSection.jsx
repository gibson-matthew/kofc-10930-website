import { useEffect, useState } from "react";
import { createEvent, deleteEvent, fetchEvents, updateEvent } from "../api";
import CalendarField, { formatLongDate } from "../components/CalendarField";
import { useContent } from "../content/ContentContext";
import { EVENT_FALLBACK, collapse } from "../content/records";
import { trackClick, trackFeature } from "../tracking";

const READ_MORE = "Read More...";

function formatWhen(event) {
  const day = formatLongDate(event.event_date) || event.event_date || "";
  return [day, event.event_time, event.location].filter(Boolean).join(" · ");
}

function eventProblem(draft) {
  const title = collapse(draft.title);
  if (!title) return "Title is required.";
  if (title.length > 120) return "Title is too long.";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.event_date || "")) return "Choose a date on the calendar.";
  const year = Number(String(draft.event_date).slice(0, 4));
  if (year < 1900 || year > 2100) return "Choose a date on the calendar.";
  const time = collapse(draft.event_time);
  if (time.length > 40) return "Time is too long.";
  const location = collapse(draft.location);
  if (location.length > 120) return "Location is too long.";
  const description = String(draft.description || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
  if (!description) return "Description is required.";
  if (description.length > 2000) return "Description is too long.";
  return "";
}

function payloadFrom(draft) {
  return {
    title: collapse(draft.title),
    event_date: draft.event_date,
    event_time: collapse(draft.event_time) || null,
    location: collapse(draft.location) || null,
    description: String(draft.description || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim(),
  };
}

function emptyDraft() {
  return { title: "", event_date: "", event_time: "", location: "", description: "" };
}

function draftFrom(event) {
  return {
    title: event.title || "",
    event_date: event.event_date || "",
    event_time: event.event_time || "",
    location: event.location || "",
    description: event.description || "",
  };
}

function EventForm({ initial, pending, onSave, onCancel, onError }) {
  const [draft, setDraft] = useState(() => (initial ? draftFrom(initial) : emptyDraft()));

  function setField(key, value) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function submit(event) {
    event.preventDefault();
    if (pending) return;
    const problem = eventProblem(draft);
    if (problem) {
      onError(problem);
      return;
    }
    onSave(payloadFrom(draft));
  }

  const canSave = Boolean(collapse(draft.title) && draft.event_date && String(draft.description || "").trim());

  return (
    <article className="event is-form">
      <form onSubmit={submit}>
        <label className="signin-field">
          <span>Title</span>
          <input
            type="text"
            maxLength={120}
            value={draft.title}
            disabled={pending}
            onChange={(event) => setField("title", event.target.value)}
          />
        </label>
        <div className="signin-field">
          <span>Date</span>
          <CalendarField value={draft.event_date} disabled={pending} onChange={(iso) => setField("event_date", iso)} />
        </div>
        <label className="signin-field">
          <span>Time</span>
          <input
            type="text"
            maxLength={40}
            value={draft.event_time}
            disabled={pending}
            onChange={(event) => setField("event_time", event.target.value)}
          />
          <p className="settings-hint">Optional. For example, 7:00 p.m.</p>
        </label>
        <label className="signin-field">
          <span>Location</span>
          <input
            type="text"
            maxLength={120}
            value={draft.location}
            disabled={pending}
            onChange={(event) => setField("location", event.target.value)}
          />
          <p className="settings-hint">Optional.</p>
        </label>
        <label className="signin-field">
          <span>Description</span>
          <textarea
            maxLength={2000}
            value={draft.description}
            disabled={pending}
            onChange={(event) => setField("description", event.target.value)}
          />
        </label>
        <div className="signin-actions recog-actions">
          <button type="submit" className="btn" disabled={pending || !canSave}>
            Save event
          </button>
          <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </article>
  );
}

function EventCard({ event, editing, open, onToggle, canManage, pending, confirming, onEdit, onAskRemove, onRemove, onKeep }) {
  const showDetail = editing || open;
  return (
    <article className="event">
      <div className="when">{formatWhen(event)}</div>
      <strong>{event.title}</strong>
      {showDetail ? <p>{event.description}</p> : null}
      {editing ? (
        <span className="more">{READ_MORE}</span>
      ) : (
        <button
          type="button"
          className="more"
          aria-expanded={open ? "true" : "false"}
          onClick={onToggle}
        >
          {open ? "Show less" : READ_MORE}
        </button>
      )}
      {canManage ? (
        confirming ? (
          <div className="signin-actions recog-actions">
            <button type="button" className="btn" disabled={pending} onClick={onRemove}>
              Remove
            </button>
            <button type="button" className="btn btn-quiet" disabled={pending} onClick={onKeep}>
              Keep
            </button>
          </div>
        ) : (
          <div className="signin-actions recog-actions">
            <button type="button" className="btn btn-quiet" disabled={pending} onClick={onEdit}>
              Edit
            </button>
            <button type="button" className="btn btn-quiet" disabled={pending} onClick={onAskRemove}>
              Remove
            </button>
          </div>
        )
      ) : null}
    </article>
  );
}

export default function EventsSection() {
  const { editing } = useContent();
  const [events, setEvents] = useState([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [editor, setEditor] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [openIds, setOpenIds] = useState({});
  const canManage = Boolean(editing) && !fallback;

  useEffect(() => {
    let cancel = false;
    fetchEvents()
      .then((rows) => {
        if (cancel) return;
        setEvents(Array.isArray(rows) ? rows : []);
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setEvents(EVENT_FALLBACK);
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!editing) {
      setEditor(null);
      setConfirmId(null);
    }
  }, [editing]);

  async function reload() {
    const rows = await fetchEvents();
    setEvents(Array.isArray(rows) ? rows : []);
    setFallback(false);
  }

  async function onSave(payload, id) {
    setPending(true);
    setError("");
    setNotice("");
    try {
      if (id) await updateEvent(id, payload);
      else await createEvent(payload);
      setEditor(null);
      try {
        await reload();
        setNotice("Saved");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Saved, but the list could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the event.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove(id) {
    setPending(true);
    setError("");
    setNotice("");
    try {
      await deleteEvent(id);
      setConfirmId(null);
      setEvents((current) => current.filter((item) => item.id !== id));
      setNotice("Saved");
      try {
        await reload();
      } catch {
        /* The removed entry is already hidden. */
      }
    } catch (err) {
      setNotice("");
      setError(err instanceof Error ? err.message : "Could not remove the event.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      {fallback ? (
        <p className="settings-hint">Showing the example list while the council records are unavailable.</p>
      ) : null}
      {notice ? (
        <p className="settings-notice is-confirm" role="status">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p className="signin-error" role="alert">
          {error}
        </p>
      ) : null}
      {canManage && editor?.mode !== "add" ? (
        <div className="signin-actions recog-actions">
          <button
            type="button"
            className="btn"
            disabled={pending}
            onClick={() => {
              setError("");
              setConfirmId(null);
              setEditor({ mode: "add" });
            }}
          >
            Add event
          </button>
        </div>
      ) : null}
      {canManage && editor?.mode === "add" ? (
        <EventForm
          pending={pending}
          onError={setError}
          onCancel={() => setEditor(null)}
          onSave={(payload) => onSave(payload)}
        />
      ) : null}
      {!loaded ? <p className="settings-hint">Loading…</p> : null}
      <div className="card-grid" id="eventList">
        {loaded && events.length === 0 ? <p className="settings-hint">None scheduled.</p> : null}
        {events.map((event) => {
          if (editor?.mode === "edit" && editor.id === event.id) {
            return (
              <EventForm
                key={event.id}
                initial={event}
                pending={pending}
                onError={setError}
                onCancel={() => setEditor(null)}
                onSave={(payload) => onSave(payload, event.id)}
              />
            );
          }
          return (
            <EventCard
              key={event.id}
              event={event}
              editing={canManage}
              open={Boolean(openIds[event.id])}
              pending={pending}
              confirming={confirmId === event.id}
              canManage={canManage}
              onToggle={() =>
                setOpenIds((current) => {
                  const next = !current[event.id];
                  trackClick(next ? "read_more" : "show_less", { target: "event", event_id: event.id });
                  if (next) trackFeature("event_expand", { event_id: event.id });
                  return { ...current, [event.id]: next };
                })
              }
              onEdit={() => {
                setError("");
                setConfirmId(null);
                setEditor({ mode: "edit", id: event.id });
              }}
              onAskRemove={() => {
                setEditor(null);
                setConfirmId(event.id);
              }}
              onRemove={() => onRemove(event.id)}
              onKeep={() => setConfirmId(null)}
            />
          );
        })}
      </div>
    </>
  );
}
