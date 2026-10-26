import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import CroppedPhoto from "../components/CroppedPhoto";
import { PortraitSm } from "../components/Marks";
import {
  fetchEmailRouting,
  saveMemberEmail,
  setMemberCloudflare,
  updateEmailRoute,
} from "../api";

const PREVIEW = 3;

function collapse(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function searchNeedle(value) {
  return collapse(value).toLowerCase().replace(/[\u2013\u2014-]/g, "-");
}

function Photo({ user, className }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [user?.photo_url]);
  if (user?.photo_url && !failed) {
    return <CroppedPhoto className={className} src={user.photo_url} crop={user} onError={() => setFailed(true)} />;
  }
  return <PortraitSm />;
}

function ListPanel({ open, canToggle, onToggle, query, onQuery, placeholder, noMatches, gridClass, children }) {
  return (
    <>
      {canToggle ? (
        <div className="signin-actions recog-actions">
          <button type="button" className="btn btn-quiet" aria-expanded={open} onClick={onToggle}>
            {open ? "View less" : "View all"}
          </button>
        </div>
      ) : null}
      {open ? (
        <label className="signin-field">
          <span>Search</span>
          <input
            type="search"
            value={query}
            placeholder={placeholder}
            autoComplete="off"
            onChange={(event) => onQuery(event.target.value)}
          />
        </label>
      ) : null}
      {noMatches ? (
        <p className="settings-hint" role="status">
          No matches.
        </p>
      ) : (
        <div className={open && canToggle ? "settings-scroll" : undefined}>
          <div className={gridClass}>{children}</div>
        </div>
      )}
    </>
  );
}

function RouteCard({ route, busy, onSaveEmail, onUpdate }) {
  const [email, setEmail] = useState(route.email || "");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setEmail(route.email || "");
  }, [route.title, route.memberid, route.email]);

  async function saveEmail() {
    setNotice("");
    setError("");
    try {
      const saved = await onSaveEmail(route, email);
      setEmail(saved);
      setNotice("Saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the personal email.");
    }
  }

  async function updateRoute() {
    setNotice("");
    setError("");
    try {
      if (route.memberid && email.trim() !== (route.email || "")) {
        await onSaveEmail(route, email);
      }
      const message = await onUpdate(route);
      if (message) setError(message);
      else setNotice("Route updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the route.");
    }
  }

  const holder = route.vacant ? "No member holds this title." : `${route.display_name || "Member"} · ${route.memberid}`;

  return (
    <article className="card settings-card">
      <h3>{route.label}</h3>
      <p className="settings-hint routing-address">{route.address}</p>
      <p className="settings-hint">{holder}</p>
      {route.memberid ? (
        <label className="signin-field">
          <span>Personal email</span>
          <input
            type="email"
            value={email}
            maxLength={90}
            autoComplete="off"
            disabled={busy}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
      ) : null}
      <div className="signin-actions">
        {route.memberid ? (
          <button type="button" className="btn btn-quiet" disabled={busy} onClick={saveEmail}>
            Save email
          </button>
        ) : null}
        <button type="button" className="btn" disabled={busy} onClick={updateRoute}>
          Update route
        </button>
      </div>
      {route.note ? <p className="settings-hint">{route.note}</p> : null}
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
    </article>
  );
}

export default function EmailRouting({ ownSaved, onOwnEmail }) {
  const { user, refresh } = useAuth();
  const [routes, setRoutes] = useState([]);
  const [members, setMembers] = useState([]);
  const [domain, setDomain] = useState("");
  const [panelError, setPanelError] = useState("");
  const [accessError, setAccessError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [routesOpen, setRoutesOpen] = useState(false);
  const [routesQuery, setRoutesQuery] = useState("");
  const [accessOpen, setAccessOpen] = useState(false);
  const [accessQuery, setAccessQuery] = useState("");

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    fetchEmailRouting()
      .then((payload) => {
        if (cancel) return;
        setRoutes(Array.isArray(payload.routes) ? payload.routes : []);
        setMembers(Array.isArray(payload.members) ? payload.members : []);
        setDomain(payload.domain || "");
        setPanelError(payload.error || "");
        setLoading(false);
      })
      .catch((err) => {
        if (cancel) return;
        setPanelError(err instanceof Error ? err.message : "Could not load email routing.");
        setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!ownSaved) return;
    setRoutes((current) =>
      current.map((route) => {
        if (route.memberid !== ownSaved.memberid || (route.email || "") === ownSaved.email) return route;
        return {
          ...route,
          email: ownSaved.email,
          note: ownSaved.email
            ? "Personal email saved. Update route to match it."
            : "No personal email is saved. Update route to turn forwarding off.",
        };
      }),
    );
  }, [ownSaved]);

  function replaceRoute(next) {
    if (!next?.title) return;
    setRoutes((current) => current.map((route) => (route.title === next.title ? { ...route, ...next } : route)));
  }

  async function onSaveEmail(route, email) {
    setBusy(true);
    try {
      const saved = await saveMemberEmail(route.memberid, email);
      const nextEmail = saved.email || "";
      replaceRoute({
        ...route,
        email: nextEmail,
        note: nextEmail
          ? "Personal email saved. Update route to match it."
          : "No personal email is saved. Update route to turn forwarding off.",
      });
      if (saved.memberid === user?.memberid && onOwnEmail) onOwnEmail(nextEmail);
      return nextEmail;
    } finally {
      setBusy(false);
    }
  }

  async function onUpdate(route) {
    setBusy(true);
    try {
      const result = await updateEmailRoute(route.title);
      if (result.route) replaceRoute(result.route);
      if (!result.error) setPanelError("");
      return result.error || "";
    } finally {
      setBusy(false);
    }
  }

  async function onCloudflare(member, isCloudflare) {
    setBusy(true);
    setAccessError("");
    try {
      const updated = await setMemberCloudflare(member.memberid, isCloudflare);
      setMembers((current) =>
        current.map((item) =>
          item.memberid === updated.memberid ? { ...item, is_cloudflare: Boolean(updated.is_cloudflare) } : item,
        ),
      );
      if (updated.memberid === user?.memberid) {
        try {
          await refresh();
        } catch {
          /* The role flag is already saved. */
        }
      }
    } catch (err) {
      setAccessError(err instanceof Error ? err.message : "Could not update Cloudflare access.");
    } finally {
      setBusy(false);
    }
  }

  const routeNeedle = routesOpen ? searchNeedle(routesQuery) : "";
  const shownRoutes = routesOpen
    ? routes.filter((route) =>
        searchNeedle(`${route.label} ${route.title} ${route.address} ${route.display_name} ${route.memberid}`).includes(
          routeNeedle,
        ),
      )
    : routes.slice(0, PREVIEW);
  const accessNeedle = accessOpen ? searchNeedle(accessQuery) : "";
  const shownAccess = accessOpen
    ? members.filter((member) =>
        searchNeedle(`${member.display_name} ${member.memberid} ${member.title}`).includes(accessNeedle),
      )
    : members.slice(0, PREVIEW);
  const cloudflareCount = members.filter((member) => member.is_cloudflare).length;
  const intro = domain
    ? `Officer and director addresses on ${domain} forward to the member who holds that title.`
    : "Officer and director addresses forward to the member who holds that title.";

  return (
    <section className="block" id="email-routing" aria-labelledby="routingHeading">
      <div className="section-head">
        <div className="eyebrow left-only">Cloudflare</div>
        <h2 id="routingHeading">Email routing</h2>
        <p>{intro}</p>
        {loading ? null : (
          <p className="settings-hint">
            {cloudflareCount === 1
              ? "1 member has the Cloudflare role."
              : `${cloudflareCount} members have the Cloudflare role.`}
          </p>
        )}
      </div>
      {panelError ? (
        <p className="signin-error" role="alert">
          {panelError}
        </p>
      ) : null}
      {loading ? <p>Loading routes…</p> : null}
      {loading ? null : (
        <ListPanel
          open={routesOpen}
          canToggle={routes.length > PREVIEW}
          onToggle={() => {
            if (routesOpen) setRoutesQuery("");
            setRoutesOpen((open) => !open);
          }}
          query={routesQuery}
          onQuery={setRoutesQuery}
          placeholder="Role or member"
          noMatches={routesOpen && routeNeedle && shownRoutes.length === 0}
          gridClass="settings-stack"
        >
          {shownRoutes.map((route) => (
            <RouteCard
              key={route.title}
              route={route}
              busy={busy}
              onSaveEmail={onSaveEmail}
              onUpdate={onUpdate}
            />
          ))}
        </ListPanel>
      )}
      {loading ? null : (
        <>
          <div className="section-head">
            <h3>Cloudflare access</h3>
            <p>Only this role can update routes. The last member with it stays.</p>
          </div>
          {accessError ? (
            <p className="signin-error" role="alert">
              {accessError}
            </p>
          ) : null}
          <ListPanel
            open={accessOpen}
            canToggle={members.length > PREVIEW}
            onToggle={() => {
              if (accessOpen) setAccessQuery("");
              setAccessOpen((open) => !open);
            }}
            query={accessQuery}
            onQuery={setAccessQuery}
            placeholder="Name or membership ID"
            noMatches={accessOpen && accessNeedle && shownAccess.length === 0}
            gridClass="officer-grid"
          >
            {shownAccess.map((member) => {
              const last = member.is_cloudflare && cloudflareCount < 2;
              return (
                <article className="officer" key={member.memberid}>
                  <Photo user={member} className="portrait-sm" />
                  <div>
                    <div className="role">{member.memberid}</div>
                    <strong>{member.display_name || "Member"}</strong>
                    <label className="admin-toggle">
                      <input
                        type="checkbox"
                        checked={Boolean(member.is_cloudflare)}
                        disabled={busy || last}
                        onChange={(event) => onCloudflare(member, event.target.checked)}
                      />
                      Cloudflare role
                    </label>
                    {last ? <p className="settings-hint">The council needs at least one Cloudflare role.</p> : null}
                  </div>
                </article>
              );
            })}
          </ListPanel>
        </>
      )}
    </section>
  );
}
