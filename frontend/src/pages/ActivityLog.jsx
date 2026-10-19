import { useEffect, useState } from "react";
import { fetchActivity } from "../api";

const EVENT_TYPES = [
  "auth.login_success",
  "auth.login_failure",
  "auth.admin_login",
  "auth.logout",
  "session.start",
  "session.end",
  "consent.choice",
  "security.login_burst",
  "security.admin_denied",
  "error.backend",
  "error.frontend",
  "file.upload",
  "file.remove",
  "admin.content_create",
  "admin.content_update",
  "admin.content_delete",
  "admin.flag_change",
  "admin.title_change",
  "page.view",
  "page.leave",
  "ui.click",
  "search.query",
  "search.use",
  "document.preview",
  "document.download",
  "feature.use",
];

const WHEN = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Chicago",
  month: "long",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function formatWhen(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || "");
  try {
    return WHEN.format(date);
  } catch {
    return date.toLocaleString();
  }
}

function choiceLabel(choice) {
  if (choice === "accepted") return "Accepted";
  if (choice === "declined") return "Declined";
  return "";
}

function tierLabel(tier) {
  if (tier === "accept") return "Optional";
  if (tier === "necessary") return "Necessary";
  return "";
}

function personText(row, members) {
  const attempted = row.details && typeof row.details.attempted_id === "string" ? row.details.attempted_id : "";
  const id = row.membership_id || attempted;
  const fromList = id ? members.find((item) => item.memberid === id) : null;
  const name = row.display_name || (fromList && fromList.display_name) || "";
  if (name && id) return `${name} (${id})`;
  if (id) return id;
  return "No member";
}

function detailsText(details) {
  const value = details && typeof details === "object" ? details : {};
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

export default function ActivityLog({ members = [] }) {
  const [eventType, setEventType] = useState("");
  const [memberId, setMemberId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState([]);
  const [truncated, setTruncated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [problem, setProblem] = useState("");

  useEffect(() => {
    let cancel = false;
    const handle = window.setTimeout(() => {
      setLoading(true);
      fetchActivity({
        event_type: eventType,
        member_id: memberId.trim(),
        date_from: dateFrom,
        date_to: dateTo,
        q: query.trim(),
      })
        .then((payload) => {
          if (cancel) return;
          if (!payload || payload.available === false) {
            setRows([]);
            setTruncated(false);
            setProblem("Activity records are unavailable right now.");
            return;
          }
          setProblem("");
          setRows(Array.isArray(payload.rows) ? payload.rows : []);
          setTruncated(Boolean(payload.truncated));
        })
        .catch(() => {
          if (cancel) return;
          setRows([]);
          setTruncated(false);
          setProblem("Activity records are unavailable right now.");
        })
        .finally(() => {
          if (!cancel) setLoading(false);
        });
    }, 250);
    return () => {
      cancel = true;
      window.clearTimeout(handle);
    };
  }, [eventType, memberId, dateFrom, dateTo, query]);

  const filtered = Boolean(eventType || memberId.trim() || dateFrom || dateTo || query.trim());
  const datesReversed = Boolean(dateFrom && dateTo && dateFrom > dateTo);

  return (
    <div>
      <div className="log-filters">
        <label className="signin-field">
          <span>Event type</span>
          <select value={eventType} onChange={(event) => setEventType(event.target.value)}>
            <option value="">All</option>
            {EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <label className="signin-field">
          <span>From</span>
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </label>
        <label className="signin-field">
          <span>To</span>
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </label>
        <label className="signin-field">
          <span>Member</span>
          <input
            type="text"
            name="log-member"
            autoComplete="off"
            spellCheck={false}
            maxLength={80}
            placeholder="Name or membership ID"
            value={memberId}
            onChange={(event) => setMemberId(event.target.value)}
          />
        </label>
        <label className="signin-field">
          <span>Search</span>
          <input
            type="search"
            name="log-search"
            autoComplete="off"
            spellCheck={false}
            maxLength={120}
            placeholder="Event, member, or details"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>
      {datesReversed ? <p className="settings-hint">The From date is after the To date.</p> : null}
      {problem ? (
        <p className="signin-error" role="alert">
          {problem}
        </p>
      ) : null}
      {loading && rows.length === 0 && !problem ? <p className="settings-hint">Loading activity…</p> : null}
      {!loading && !problem && truncated ? (
        <p className="settings-hint" role="status">
          Showing the newest 200 matching rows.
        </p>
      ) : null}
      {!loading && !problem && rows.length === 0 ? (
        <p className="settings-hint" role="status">
          {filtered ? "No matches." : "No activity recorded."}
        </p>
      ) : null}
      {rows.length > 0 ? (
        <div className="log-scroll" tabIndex={0} aria-label="Activity log">
          {rows.map((row) => {
            const choice = choiceLabel(row.choice);
            const meta = [
              row.kind === "consent" && choice ? choice : "",
              row.kind === "consent" ? `version ${row.version || "1"}` : "",
              tierLabel(row.tier),
              personText(row, members),
              row.ip || "",
              row.user_agent || "",
            ]
              .filter(Boolean)
              .join(" · ");
            return (
              <article className="log-row" key={`${row.kind || "event"}-${row.id}`}>
                <div className="log-row-head">
                  <strong>{row.kind === "consent" ? "Cookie choice" : row.event_type}</strong>
                  <time dateTime={row.created_at || undefined}>{formatWhen(row.created_at)}</time>
                </div>
                <p className="log-meta">{meta}</p>
                <pre className="log-details">{detailsText(row.details)}</pre>
              </article>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
