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

const LOG_PREVIEW = 2;

const DAY_LABEL = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  month: "short",
  day: "numeric",
});

const CHANGE_VERBS = {
  "admin.content_create": "Created",
  "admin.content_update": "Updated",
  "admin.content_delete": "Removed",
};

function calendarDay(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  if (!match) return String(iso || "");
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  try {
    return DAY_LABEL.format(date);
  } catch {
    return iso;
  }
}

function contentLabel(value) {
  const text = String(value || "").replace(/_/g, " ").trim();
  return text || "item";
}

function windowTotal(rows, key) {
  return rows.reduce((sum, row) => sum + (Number(row[key]) || 0), 0);
}

function ColumnChart({ points, series, caption, description }) {
  const width = 140;
  const height = 64;
  const gap = 3;
  const barWidth = (width - gap * Math.max(points.length - 1, 0)) / Math.max(points.length, 1);
  const max = Math.max(
    1,
    ...points.map((point) => point.values.reduce((sum, value) => sum + value, 0)),
  );
  return (
    <figure className="log-chart">
      <figcaption>{caption}</figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={description}>
        {points.map((point, index) => {
          let y = height;
          const x = index * (barWidth + gap);
          return (
            <g key={point.day}>
              {point.values.map((value, seriesIndex) => {
                const barHeight = (value / max) * height;
                y -= barHeight;
                if (barHeight <= 0) return null;
                return (
                  <rect
                    key={series[seriesIndex].key}
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    className={series[seriesIndex].bar}
                  />
                );
              })}
            </g>
          );
        })}
      </svg>
      <p className="log-legend">
        {series.map((item) => (
          <span key={item.key}>
            <i className={item.swatch} /> {item.label}
          </span>
        ))}
        <span>
          {calendarDay(points[0]?.day)} – {calendarDay(points[points.length - 1]?.day)}
        </span>
      </p>
    </figure>
  );
}

function ActivitySummary({ summary }) {
  const consentTotal = (summary.consent_accepted || 0) + (summary.consent_declined || 0);
  if (!summary.events && !consentTotal) {
    return (
      <p className="settings-hint" role="status">
        No activity recorded.
      </p>
    );
  }
  const loginDays = Array.isArray(summary.logins_by_day) ? summary.logins_by_day : [];
  const viewDays = Array.isArray(summary.page_views_by_day) ? summary.page_views_by_day : [];
  const loginWindow = windowTotal(loginDays, "success") + windowTotal(loginDays, "failure");
  const viewWindow = windowTotal(viewDays, "count");
  const top = Array.isArray(summary.top_events) ? summary.top_events : [];
  const topMax = Math.max(1, ...top.map((item) => item.count || 0));
  const changes = Array.isArray(summary.content_changes) ? summary.content_changes : [];
  const metrics = [
    ["Sign-ins", summary.login_success || 0],
    ["Failed sign-ins", summary.login_failure || 0],
    ["Failure bursts", summary.login_bursts || 0],
    ["Accepted", summary.consent_accepted || 0],
    ["Declined", summary.consent_declined || 0],
    ["Downloads", summary.document_downloads || 0],
    ["Document opens", summary.document_previews || 0],
    ["Page views", summary.page_views || 0],
  ];
  return (
    <div className="log-summary">
      <p className="settings-hint">
        {summary.necessary || 0} necessary events. {summary.accept || 0} optional events. Counts include every
        stored row. Charts cover the last 14 days.
      </p>
      <ul className="log-metrics">
        {metrics.map(([label, count]) => (
          <li className="log-metric" key={label}>
            <b>{count}</b>
            <span>{label}</span>
          </li>
        ))}
      </ul>
      <div className="log-charts">
        {loginWindow > 0 ? (
          <ColumnChart
            caption="Sign-ins, last 14 days"
            description={`${windowTotal(loginDays, "success")} sign-ins and ${windowTotal(loginDays, "failure")} failed sign-ins in the last 14 days.`}
            series={[
              { key: "success", label: "Sign-ins", bar: "log-bar is-ok", swatch: "log-swatch is-ok" },
              { key: "failure", label: "Failed", bar: "log-bar is-bad", swatch: "log-swatch is-bad" },
            ]}
            points={loginDays.map((day) => ({
              day: day.day,
              values: [day.success || 0, day.failure || 0],
            }))}
          />
        ) : null}
        {top.length > 0 ? (
          <figure className="log-chart">
            <figcaption>Top events</figcaption>
            <ul className="log-types">
              {top.map((item) => (
                <li className="log-type" key={item.event_type}>
                  <span>{item.event_type}</span>
                  <span className="log-type-track">
                    <span style={{ width: `${Math.max(4, Math.round(((item.count || 0) / topMax) * 100))}%` }} />
                  </span>
                  <b>{item.count}</b>
                </li>
              ))}
            </ul>
          </figure>
        ) : null}
        {consentTotal > 0 ? (
          <figure className="log-chart">
            <figcaption>Cookie choice</figcaption>
            <div
              className="log-split"
              role="img"
              aria-label={`${summary.consent_accepted || 0} accepted, ${summary.consent_declined || 0} declined.`}
            >
              <span className="is-accepted" style={{ flex: summary.consent_accepted || 0 }} />
              <span className="is-declined" style={{ flex: summary.consent_declined || 0 }} />
            </div>
            <p className="log-legend">
              <span>
                <i className="log-swatch is-ok" /> Accepted {summary.consent_accepted || 0}
              </span>
              <span>
                <i className="log-swatch is-bad" /> Declined {summary.consent_declined || 0}
              </span>
            </p>
          </figure>
        ) : null}
        {viewWindow > 0 ? (
          <ColumnChart
            caption="Page views, last 14 days"
            description={`${viewWindow} page views in the last 14 days.`}
            series={[{ key: "count", label: "Page views", bar: "log-bar is-view", swatch: "log-swatch is-view" }]}
            points={viewDays.map((day) => ({ day: day.day, values: [day.count || 0] }))}
          />
        ) : null}
        {changes.length > 0 ? (
          <figure className="log-chart log-chart-wide">
            <figcaption>Recent content changes</figcaption>
            <ul className="log-changes">
              {changes.map((change, index) => (
                <li key={`${change.event_type}-${change.created_at}-${change.record_id}-${index}`}>
                  <strong>
                    {CHANGE_VERBS[change.event_type] || "Changed"} {contentLabel(change.content_type)}
                  </strong>
                  <span>
                    {[change.display_name, change.membership_id, formatWhen(change.created_at)]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </li>
              ))}
            </ul>
          </figure>
        ) : null}
      </div>
    </div>
  );
}

function LogRow({ row, members }) {
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
    <article className="log-row">
      <div className="log-row-head">
        <strong>{row.kind === "consent" ? "Cookie choice" : row.event_type}</strong>
        <time dateTime={row.created_at || undefined}>{formatWhen(row.created_at)}</time>
      </div>
      <p className="log-meta">{meta}</p>
      <pre className="log-details">{detailsText(row.details)}</pre>
    </article>
  );
}

export default function ActivityLog({ members = [] }) {
  const [eventType, setEventType] = useState("");
  const [memberId, setMemberId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [truncated, setTruncated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [problem, setProblem] = useState("");
  const [open, setOpen] = useState(false);

  function onToggle() {
    if (open) {
      setEventType("");
      setMemberId("");
      setDateFrom("");
      setDateTo("");
      setQuery("");
      setOpen(false);
      return;
    }
    setOpen(true);
  }

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
            setSummary(null);
            setTruncated(false);
            setProblem("Activity records are unavailable right now.");
            return;
          }
          setProblem("");
          setRows(Array.isArray(payload.rows) ? payload.rows : []);
          setSummary(payload.summary || null);
          setTruncated(Boolean(payload.truncated));
        })
        .catch(() => {
          if (cancel) return;
          setRows([]);
          setSummary(null);
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
  const visible = open ? rows : rows.slice(0, LOG_PREVIEW);
  const summaryEmpty = Boolean(
    summary && !summary.events && !(summary.consent_accepted || 0) && !(summary.consent_declined || 0),
  );

  return (
    <div>
      {summary && !problem ? <ActivitySummary summary={summary} /> : null}
      <div className="signin-actions recog-actions">
        <button type="button" className="btn btn-quiet" aria-expanded={open} onClick={onToggle}>
          {open ? "View less" : "View all"}
        </button>
      </div>
      {open ? (
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
      ) : null}
      {open && datesReversed ? <p className="settings-hint">The From date is after the To date.</p> : null}
      {problem ? (
        <p className="signin-error" role="alert">
          {problem}
        </p>
      ) : null}
      {loading && rows.length === 0 && !problem ? <p className="settings-hint">Loading activity…</p> : null}
      {open && !loading && !problem && truncated ? (
        <p className="settings-hint" role="status">
          Showing the newest 200 matching rows.
        </p>
      ) : null}
      {!loading && !problem && rows.length === 0 && !(summaryEmpty && !filtered) ? (
        <p className="settings-hint" role="status">
          {filtered ? "No matches." : "No activity recorded."}
        </p>
      ) : null}
      {visible.length > 0 ? (
        <div className={open ? "log-scroll" : undefined} tabIndex={open ? 0 : undefined} aria-label="Activity log">
          {visible.map((row) => (
            <LogRow key={`${row.kind || "event"}-${row.id}`} row={row} members={members} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
