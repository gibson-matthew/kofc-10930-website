import { useEffect, useRef, useState } from "react";
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

function StatusMark({ status, failed }) {
  const kind = failed ? "error" : status === "forwarding" ? "verified" : status === "pending" ? "waiting" : "unset";
  const label = kind === "verified" ? "✓" : kind === "error" ? "!" : "";
  return (
    <span className={`routing-mark is-${kind}`} aria-hidden="true">
      {label}
    </span>
  );
}

function RouteCard({ route, busy, applyError, onSaveEmail, onUpdate, onEditing }) {
  const [email, setEmail] = useState(route.email || "");
  const [override, setOverride] = useState(false);
  const [error, setError] = useState("");
  const status = route.status || "unset";
  const destination = route.email || "";
  const holder = route.vacant ? "No member holds this title." : `${route.display_name || "Member"} · ${route.memberid}`;
  const shownError = error || applyError || "";

  useEffect(() => {
    setEmail(route.email || "");
  }, [route.title, route.memberid, route.email]);

  useEffect(() => {
    onEditing(route.title, override);
    return () => onEditing(route.title, false);
  }, [onEditing, override, route.title]);

  async function saveDestination() {
    setError("");
    try {
      const next = email.trim();
      await onSaveEmail(route, next);
      const message = await onUpdate({ ...route, email: next }, { sendVerification: true });
      if (message) setError(message);
      else setOverride(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the destination.");
    }
  }

  async function runUpdate(sendVerification) {
    setError("");
    try {
      const message = await onUpdate(route, { sendVerification });
      if (message) setError(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the route.");
    }
  }

  const statusCopy =
    status === "forwarding"
      ? "Forwarding to this personal email."
      : status === "pending"
        ? "Waiting for this inbox to confirm the Cloudflare verification email."
        : "Not set.";
  const canSend = Boolean(destination) && !route.vacant && status === "unset" && !route.verified;
  const canApply = Boolean(destination) && !route.vacant && route.verified && status !== "forwarding" && !busy;
  const canDisable = Boolean(route.route_enabled) && (route.vacant || !destination);

  return (
    <article className="card settings-card">
      <h3>{route.label}</h3>
      <p className="settings-hint routing-address">{route.address}</p>
      <p className="settings-hint">{holder}</p>
      <p className="settings-hint">{destination ? `Destination: ${destination}` : "Destination: Not set"}</p>
      {route.forward_to && route.forward_to.toLowerCase() !== destination.toLowerCase() ? (
        <p className="settings-hint">Cloudflare forwards to {route.forward_to}.</p>
      ) : null}
      <p className="routing-status" role="status">
        <StatusMark status={status} failed={Boolean(shownError)} />
        <span>{statusCopy}</span>
      </p>
      {override ? (
        <label className="signin-field">
          <span>Destination</span>
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
        {route.memberid && !override ? (
          <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => setOverride(true)}>
            {destination ? "Change destination" : "Set destination"}
          </button>
        ) : null}
        {override ? (
          <button type="button" className="btn btn-quiet" disabled={busy} onClick={saveDestination}>
            Save destination
          </button>
        ) : null}
        {canSend ? (
          <button type="button" className="btn" disabled={busy} onClick={() => runUpdate(true)}>
            Update route
          </button>
        ) : null}
        {canApply ? (
          <button type="button" className="btn" disabled={busy} onClick={() => runUpdate(false)}>
            Apply route
          </button>
        ) : null}
        {canDisable ? (
          <button type="button" className="btn" disabled={busy} onClick={() => runUpdate(false)}>
            Turn forwarding off
          </button>
        ) : null}
      </div>
      {shownError ? (
        <p className="signin-error" role="alert">
          {shownError}
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
  const [rowError, setRowError] = useState({});
  const applyFailed = useRef(new Set());
  const applying = useRef(new Set());
  const editing = useRef(new Set());
  const onEditing = useRef((title, isOpen) => {
    if (isOpen) editing.current.add(title);
    else editing.current.delete(title);
  });

  function remember(payload) {
    const next = Array.isArray(payload.routes) ? payload.routes : [];
    setRoutes(next);
    setMembers(Array.isArray(payload.members) ? payload.members : []);
    setDomain(payload.domain || "");
    setPanelError(payload.error || "");
    return next;
  }

  async function applyVerified(list) {
    const ready = list.filter(
      (route) =>
        route.verified &&
        route.status !== "forwarding" &&
        route.email &&
        !route.vacant &&
        !applyFailed.current.has(route.title) &&
        !applying.current.has(route.title) &&
        !editing.current.has(route.title),
    );
    if (!ready.length) return;
    setBusy(true);
    try {
      for (const route of ready) {
        applying.current.add(route.title);
        try {
          const result = await updateEmailRoute(route.title, { sendVerification: false });
          if (result.route) replaceRoute(result.route);
          const confirmed = !result.error && result.route && result.route.status === "forwarding";
          if (!confirmed) {
            applyFailed.current.add(route.title);
            setRowError((current) => ({
              ...current,
              [route.title]: result.error || "Cloudflare has not turned this route on.",
            }));
          } else {
            applyFailed.current.delete(route.title);
            setRowError((current) => ({ ...current, [route.title]: "" }));
            setPanelError("");
          }
        } catch (err) {
          applyFailed.current.add(route.title);
          setRowError((current) => ({
            ...current,
            [route.title]: err instanceof Error ? err.message : "Could not update the route.",
          }));
        } finally {
          applying.current.delete(route.title);
        }
      }
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    fetchEmailRouting()
      .then(async (payload) => {
        if (cancel) return;
        const next = remember(payload);
        setLoading(false);
        if (!payload.error) await applyVerified(next);
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

  const pending = routes.some((route) => route.status === "pending");

  useEffect(() => {
    if (!pending) return undefined;
    let cancel = false;
    const id = window.setInterval(() => {
      fetchEmailRouting()
        .then(async (payload) => {
          if (cancel) return;
          const next = remember(payload);
          if (!payload.error) await applyVerified(next);
        })
        .catch((err) => {
          if (cancel) return;
          setPanelError(err instanceof Error ? err.message : "Could not load email routing.");
        });
    }, 15000);
    return () => {
      cancel = true;
      window.clearInterval(id);
    };
  }, [pending]);

  useEffect(() => {
    if (!ownSaved) return undefined;
    let cancel = false;
    setRoutes((current) =>
      current.map((route) => {
        if (route.memberid !== ownSaved.memberid || (route.email || "") === (ownSaved.email || "")) return route;
        return {
          ...route,
          email: ownSaved.email || "",
          forward_to: "",
          route_enabled: false,
          verified: false,
          status: "unset",
          note: "Not set.",
        };
      }),
    );
    fetchEmailRouting()
      .then((payload) => {
        if (!cancel) remember(payload);
      })
      .catch((err) => {
        if (cancel) return;
        setPanelError(err instanceof Error ? err.message : "Could not load email routing.");
      });
    return () => {
      cancel = true;
    };
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
        forward_to: "",
        route_enabled: false,
        verified: false,
        status: "unset",
        note: "Not set.",
      });
      if (saved.memberid === user?.memberid && onOwnEmail) onOwnEmail(nextEmail);
      return nextEmail;
    } finally {
      setBusy(false);
    }
  }

  async function onUpdate(route, { sendVerification = false } = {}) {
    if (applying.current.has(route.title)) return "This route is already being updated.";
    applying.current.add(route.title);
    setBusy(true);
    try {
      const result = await updateEmailRoute(route.title, { sendVerification });
      if (result.route) replaceRoute(result.route);
      let message = result.error || "";
      const applyMissed =
        !message &&
        !sendVerification &&
        route.verified &&
        route.email &&
        !route.vacant &&
        result.route &&
        result.route.status !== "forwarding";
      if (applyMissed) message = "Cloudflare has not turned this route on.";
      if (message) {
        applyFailed.current.add(route.title);
        setRowError((current) => ({ ...current, [route.title]: message }));
      } else {
        applyFailed.current.delete(route.title);
        setRowError((current) => ({ ...current, [route.title]: "" }));
        setPanelError("");
      }
      return message;
    } finally {
      applying.current.delete(route.title);
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
        searchNeedle(
          `${route.label} ${route.title} ${route.address} ${route.display_name} ${route.memberid} ${route.email} ${route.forward_to}`,
        ).includes(
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
    ? `Role addresses on ${domain} forward to the personal email saved for the member in that role.`
    : "Role addresses forward to the personal email saved for the member in that role.";

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
              applyError={rowError[route.title] || ""}
              onSaveEmail={onSaveEmail}
              onUpdate={onUpdate}
              onEditing={onEditing.current}
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
