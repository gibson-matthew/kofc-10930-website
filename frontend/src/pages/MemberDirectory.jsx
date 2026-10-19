import { useEffect, useState } from "react";
import { fetchDirectory, setMemberHonorary } from "../api";
import CroppedPhoto from "../components/CroppedPhoto";
import { PortraitSm } from "../components/Marks";
import { DIRECTORY_EXAMPLES } from "../content/directory";
import { collapse } from "../content/records";
import { OFFICER_TITLES } from "../titles";

function titleLabel(title) {
  if (!title) return "";
  const found = OFFICER_TITLES.find(([, abbrev]) => abbrev === title);
  return found ? found[0] : String(title);
}

function searchText(item) {
  return collapse(`${item.display_name || ""} ${item.title || ""} ${titleLabel(item.title)}`)
    .toLowerCase()
    .replace(/[\u2013\u2014-]/g, "-");
}

function forViewer(rows, admin) {
  return rows.map((row) => (admin ? { ...row } : { ...row, phone: "", email: "" }));
}

function byName(a, b) {
  const name = String(a.display_name || "").localeCompare(String(b.display_name || ""), undefined, {
    sensitivity: "base",
  });
  if (name) return name;
  return String(a.memberid || "").localeCompare(String(b.memberid || ""));
}

function MemberPhoto({ member }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [member?.photo_url]);
  if (member?.photo_url && !failed) {
    return (
      <CroppedPhoto className="portrait-sm" src={member.photo_url} crop={member} onError={() => setFailed(true)} />
    );
  }
  return <PortraitSm />;
}

export default function MemberDirectory({ canManage }) {
  const [items, setItems] = useState([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [pendingId, setPendingId] = useState("");
  const [query, setQuery] = useState("");
  const manage = Boolean(canManage) && !fallback;
  const showContact = Boolean(canManage);

  useEffect(() => {
    let cancel = false;
    setLoaded(false);
    fetchDirectory()
      .then((rows) => {
        if (cancel) return;
        const list = Array.isArray(rows) ? rows : [];
        setItems(forViewer(list, canManage).sort(byName));
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setItems(forViewer(DIRECTORY_EXAMPLES, canManage).sort(byName));
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, [canManage]);

  async function onHonorary(member, next) {
    setPendingId(member.memberid);
    setError("");
    try {
      const updated = await setMemberHonorary(member.memberid, next);
      setItems((current) =>
        current.map((item) =>
          item.memberid === member.memberid
            ? { ...item, honorary_life: Boolean(updated?.honorary_life) }
            : item,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update Honorary Life Member.");
    } finally {
      setPendingId("");
    }
  }

  const needle = searchText({ display_name: query, title: "" });
  const shown = needle ? items.filter((item) => searchText(item).includes(needle)) : items;

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
      {loaded && items.length === 0 ? <p className="settings-hint">None recorded yet.</p> : null}
      {items.length > 0 ? (
        <label className="signin-field doc-search">
          <span>Search</span>
          <input
            type="search"
            value={query}
            placeholder="Name or title"
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
                const office = titleLabel(item.title);
                const pending = pendingId === item.memberid;
                return (
                  <li key={item.memberid}>
                    <div className="member-row">
                      <MemberPhoto member={item} />
                      <div>
                        <h3>{item.display_name || "Member"}</h3>
                        {office ? <p>{office}</p> : null}
                        {item.honorary_life && !manage ? <p className="member-honor">Honorary Life Member</p> : null}
                        {showContact && item.phone ? <p className="settings-hint">{item.phone}</p> : null}
                        {showContact && item.email ? <p className="settings-hint">{item.email}</p> : null}
                        {manage ? (
                          <label className="admin-toggle">
                            <input
                              type="checkbox"
                              checked={Boolean(item.honorary_life)}
                              disabled={Boolean(pendingId)}
                              onChange={(event) => onHonorary(item, event.target.checked)}
                            />
                            Honorary Life Member
                          </label>
                        ) : null}
                        {pending ? <p className="settings-hint">Saving…</p> : null}
                      </div>
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
