import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { fetchEmailAudience, fetchSentMail, sendCouncilEmail } from "../api";
import { OFFICER_TITLES } from "../titles";
import logoUrl from "../../../logo_email_example.png";

const DISCLAIMER =
  "You received this message as you are a member of Knights of Columbus Father Emil Gerlich of Fort Worth Council # 10930 in Fort Worth, TX. If you have questions, comments, or concerns please contact the current Grand Knight or Financial Secretary.";

function titleName(abbrev) {
  const found = OFFICER_TITLES.find((row) => row[1] === abbrev);
  return found ? found[0] : "";
}

function when(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function searchNeedle(value) {
  return String(value || "").trim().toLowerCase().replace(/[\u2013\u2014-]/g, "-");
}

export default function EmailCompose() {
  const { user } = useAuth();
  const editorRef = useRef(null);
  const [members, setMembers] = useState([]);
  const [officerIds, setOfficerIds] = useState([]);
  const [directorIds, setDirectorIds] = useState([]);
  const [domain, setDomain] = useState("mistymountains.dev");
  const [sent, setSent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [subject, setSubject] = useState("");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState(() => new Set());
  const [officers, setOfficers] = useState(false);
  const [directors, setDirectors] = useState(false);
  const [allMembers, setAllMembers] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const [filter, setFilter] = useState("all");

  function loadSent() {
    return fetchSentMail().then((payload) => {
      setSent(Array.isArray(payload.items) ? payload.items : []);
    });
  }

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    Promise.all([fetchEmailAudience(), fetchSentMail()])
      .then(([audience, history]) => {
        if (cancel) return;
        setMembers(Array.isArray(audience.members) ? audience.members : []);
        setOfficerIds(Array.isArray(audience.officer_ids) ? audience.officer_ids : []);
        setDirectorIds(Array.isArray(audience.director_ids) ? audience.director_ids : []);
        setDomain(audience.domain || "mistymountains.dev");
        setSent(Array.isArray(history.items) ? history.items : []);
        setLoading(false);
      })
      .catch((err) => {
        if (cancel) return;
        setError(err instanceof Error ? err.message : "Could not load email.");
        setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  const signature = useMemo(() => {
    const name = String(user?.display_name || "").trim() || "Member";
    const label = titleName(user?.title);
    return [name, label, "Council 10930", domain].filter(Boolean);
  }, [user?.display_name, user?.title, domain]);

  const greetingName = useMemo(() => {
    const ids = new Set(picked);
    if (allMembers) members.forEach((member) => ids.add(member.memberid));
    if (officers) officerIds.forEach((id) => ids.add(id));
    if (directors) directorIds.forEach((id) => ids.add(id));
    if (ids.size !== 1) return "";
    const only = members.find((member) => ids.has(member.memberid));
    return String(only?.display_name || "").trim() || "Member";
  }, [picked, allMembers, officers, directors, members, officerIds, directorIds]);

  const selectedCount = useMemo(() => {
    const ids = new Set(picked);
    if (allMembers) members.forEach((member) => ids.add(member.memberid));
    if (officers) officerIds.forEach((id) => ids.add(id));
    if (directors) directorIds.forEach((id) => ids.add(id));
    return ids.size;
  }, [picked, allMembers, officers, directors, members, officerIds, directorIds]);

  const needle = searchNeedle(query);
  const shown = needle
    ? members.filter((member) =>
        searchNeedle(`${member.display_name} ${member.memberid} ${member.title || ""} ${titleName(member.title)}`).includes(needle),
      )
    : members;

  function togglePerson(memberid) {
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(memberid)) next.delete(memberid);
      else next.add(memberid);
      return next;
    });
  }

  function format(command, value) {
    editorRef.current?.focus();
    if (typeof document.execCommand === "function") document.execCommand(command, false, value);
  }

  function addLink() {
    const url = linkUrl.trim();
    if (!/^https?:\/\//i.test(url)) {
      setError("Enter a link that starts with http:// or https://.");
      return;
    }
    setError("");
    format("createLink", url);
    setLinkOpen(false);
    setLinkUrl("");
  }

  async function onSend() {
    setError("");
    setNotice("");
    const body = editorRef.current ? editorRef.current.innerHTML : "";
    setBusy(true);
    try {
      const result = await sendCouncilEmail({
        subject: subject.trim(),
        body,
        officers,
        directors,
        all_members: allMembers,
        member_ids: Array.from(picked),
      });
      const summary = `Sent to ${result.sent}, skipped ${result.skipped} (no email).`;
      if (result.error) {
        setError(result.error);
        setNotice(summary);
      } else {
        setNotice(summary);
        if (result.sent > 0) {
          setSubject("");
          if (editorRef.current) editorRef.current.innerHTML = "";
        }
      }
      try {
        await loadSent();
      } catch {
        /* The send result is already on the card. */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send the message.");
    } finally {
      setBusy(false);
    }
  }

  const visibleSent = sent.filter((item) => {
    if (filter === "sent") return item.success;
    if (filter === "failed") return !item.success;
    return true;
  });

  return (
    <section className="block" id="council-email" aria-labelledby="emailHeading">
      <div className="section-head">
        <div className="eyebrow left-only">Cloudflare</div>
        <h2 id="emailHeading">Email</h2>
        <p>Messages leave from the council address. Each member is greeted by name. The signature is the member who is signed in.</p>
      </div>
      {loading ? <p>Loading email…</p> : null}
      {loading ? null : (
        <div className="settings-stack">
          <article className="card settings-card mail-compose">
            <div className="mail-line">
              <span>To</span>
              <div className="mail-picks">
                <button type="button" className="btn btn-quiet mail-pick" aria-pressed={officers} onClick={() => setOfficers((on) => !on)}>
                  All officers
                </button>
                <button type="button" className="btn btn-quiet mail-pick" aria-pressed={directors} onClick={() => setDirectors((on) => !on)}>
                  All directors
                </button>
                <button type="button" className="btn btn-quiet mail-pick" aria-pressed={allMembers} onClick={() => setAllMembers((on) => !on)}>
                  All members
                </button>
              </div>
            </div>
            <p className="settings-hint">{selectedCount === 1 ? "1 person selected." : `${selectedCount} people selected.`}</p>
            <label className="signin-field">
              <span>People</span>
              <input
                type="search"
                value={query}
                placeholder="Name or membership ID"
                autoComplete="off"
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <div className="settings-scroll">
              <ul className="mail-people">
                {shown.map((member) => (
                  <li key={member.memberid}>
                    <label>
                      <input
                        type="checkbox"
                        checked={picked.has(member.memberid)}
                        onChange={() => togglePerson(member.memberid)}
                      />
                      <span>
                        {member.display_name || "Member"}
                        {member.title ? ` · ${member.title}` : ""}
                        <span className="mail-id"> {member.memberid}</span>
                        {member.has_email ? null : <span className="mail-missing"> No email</span>}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              {shown.length ? null : <p className="settings-hint">No matches.</p>}
            </div>
            <label className="signin-field">
              <span>Subject</span>
              <input
                type="text"
                value={subject}
                maxLength={200}
                autoComplete="off"
                disabled={busy}
                onChange={(event) => setSubject(event.target.value)}
              />
            </label>
            <div className="mail-toolbar">
              <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => format("bold")}>
                Bold
              </button>
              <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => format("insertUnorderedList")}>
                List
              </button>
              <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => setLinkOpen((open) => !open)}>
                Link
              </button>
            </div>
            {linkOpen ? (
              <div className="mail-link">
                <label className="signin-field">
                  <span>Link</span>
                  <input
                    type="url"
                    value={linkUrl}
                    placeholder="https://"
                    autoComplete="off"
                    onChange={(event) => setLinkUrl(event.target.value)}
                  />
                </label>
                <button type="button" className="btn btn-quiet" onClick={addLink}>
                  Add link
                </button>
              </div>
            ) : null}
            <p className="mail-greeting">
              {greetingName ? `Dear Brother Knight ${greetingName}` : "Dear Brother Knight {each member's name}"}
            </p>
            <div
              ref={editorRef}
              className="mail-body"
              contentEditable={!busy}
              role="textbox"
              aria-multiline="true"
              aria-label="Message"
              data-placeholder="Write the message"
            />
            <div className="mail-signature" aria-label="Signature">
              {signature.map((line, index) => (
                <div key={`${index}-${line}`}>{line}</div>
              ))}
              <img className="mail-logo" src={logoUrl} alt="Knights of Columbus" />
            </div>
            <p className="mail-disclaimer">{DISCLAIMER}</p>
            <div className="signin-actions">
              <button type="button" className="btn" disabled={busy} onClick={onSend}>
                {busy ? "Sending…" : "Send"}
              </button>
            </div>
            {notice ? (
              <p className={error ? "settings-hint" : "settings-notice is-confirm"} role="status">
                {notice}
              </p>
            ) : null}
            {error ? (
              <p className="signin-error" role="alert">
                {error}
              </p>
            ) : null}
          </article>
          <article className="card settings-card">
            <h3>Sent</h3>
            <div className="mail-picks">
              {[
                ["all", "All"],
                ["sent", "Sent"],
                ["failed", "Failed"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className="btn btn-quiet mail-filter"
                  aria-pressed={filter === value}
                  onClick={() => setFilter(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            {visibleSent.length ? (
              <div className="settings-scroll">
                <div className="mail-sent">
                  {visibleSent.map((item) => (
                    <article key={item.id}>
                      <p className="settings-hint">{when(item.sent_at)}</p>
                      <strong>{item.subject}</strong>
                      <p className="settings-hint">
                        <span className={item.success ? "mail-ok" : "mail-failed"}>{item.success ? "Sent" : "Failed"}</span>
                        {` · Sent to ${item.recipient_count}, skipped ${item.skipped_count}`}
                        {!item.success && item.error_code ? ` · code ${item.error_code}` : ""}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="settings-hint">{sent.length ? "No matches." : "No messages yet."}</p>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
