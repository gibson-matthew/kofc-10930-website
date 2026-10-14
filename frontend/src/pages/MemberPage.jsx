import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { fetchMediaSlots, fetchRoster, imageFileError, replaceMedia, saveRoleAssignments, uploadMedia, assignMediaSlot } from "../api";
import { useAuth } from "../auth/AuthContext";
import { Block, Eyebrow } from "../components/Block";
import CroppedPhoto from "../components/CroppedPhoto";
import { Avatar, Portrait, PortraitSm } from "../components/Marks";
import { ContentProvider, useContent } from "../content/ContentContext";
import { LOGO_SRC } from "../content/seed";
import EventsSection from "./EventsSection";
import HonorsSection from "./HonorsSection";
import SettingsView from "./SettingsView";
import { navigate, usePath } from "../router";
import { DIRECTOR_ROLES, memberLabel, OFFICER_ROLES } from "../titles";

const TITLE = "Members Area — Council 10930 — Knights of Columbus";

const LINK_CARDS = [
  {
    title: "links.0.title",
    body: "links.0.body",
    action: "links.0.action",
    href: "https://square.link/u/Gw17DDDx",
    external: true,
  },
  { title: "links.1.title", action: "links.1.action", detail: "links.1.detail", panel: "panel-birthdays" },
  { title: "links.2.title", action: "links.2.action", detail: "links.2.detail", panel: "panel-announcements" },
  { title: "links.3.title", action: "links.3.action", detail: "links.3.detail", panel: "panel-prayer" },
  { title: "links.4.title", action: "links.4.action", detail: "links.4.detail", panel: "panel-roster" },
  { title: "links.5.title", action: "links.5.action", detail: "links.5.detail", panel: "panel-elders" },
  { title: "links.6.title", action: "links.6.action", detail: "links.6.detail", panel: "panel-comments" },
  { title: "links.7.title", action: "links.7.action", detail: "links.7.detail", panel: "panel-sfs" },
  { title: "links.8.title", action: "links.8.action", detail: "links.8.detail", panel: "panel-events" },
  { title: "links.9.title", action: "links.9.action", panel: "panel-hours", hours: true },
  {
    title: "links.10.title",
    body: "links.10.body",
    action: "links.10.action",
    detail: "links.10.detail",
    panel: "panel-goal",
  },
  { title: "links.11.title", action: "links.11.action", detail: "links.11.detail", panel: "panel-nominate" },
  { title: "links.12.title", action: "links.12.action", detail: "links.12.detail", panel: "panel-fs" },
  { title: "links.13.title", action: "links.13.action", detail: "links.13.detail", panel: "panel-treasurer" },
  { title: "links.14.title", action: "links.14.action", detail: "links.14.detail", panel: "panel-budget" },
  { title: "links.15.title", action: "links.15.action", href: "mailto:webmaster@council10930.example" },
];

function range(count) {
  return Array.from({ length: count }, (_, index) => index);
}

const PHOTO_ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

function MemberAvatar({ user }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [user?.photo_url]);
  if (user?.photo_url && !failed) {
    return <CroppedPhoto className="avatar" src={user.photo_url} crop={user} onError={() => setFailed(true)} />;
  }
  return <Avatar />;
}

function PersonPhoto({ member }) {
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

function buildDraft(roster, roles) {
  const draft = {};
  for (const [, abbrev] of roles) {
    const holder = roster.find((member) => member.title === abbrev);
    draft[abbrev] = holder ? holder.memberid : "";
  }
  return draft;
}

function optionLabel(member, roster) {
  const shared = roster.filter((item) => item.display_name === member.display_name).length > 1;
  return shared ? `${member.display_name} (${member.memberid})` : member.display_name;
}

function RoleGrid({ roles, roster, ready, editing, onDraft }) {
  const [draft, setDraft] = useState(null);

  useEffect(() => {
    if (!editing || !ready) {
      setDraft(null);
      return;
    }
    setDraft((current) => current || buildDraft(roster, roles));
  }, [editing, ready, roster, roles]);

  useEffect(() => {
    if (!editing) onDraft(null);
    else if (draft) onDraft(draft);
    return () => onDraft(null);
  }, [editing, draft, onDraft]);

  function onPick(abbrev, memberid) {
    setDraft((current) => {
      if (!current) return current;
      const next = { ...current, [abbrev]: memberid };
      if (memberid) {
        for (const key of Object.keys(next)) {
          if (key !== abbrev && next[key] === memberid) next[key] = "";
        }
      }
      return next;
    });
  }

  return roles.map(([label, abbrev]) => {
    const holder = roster.find((member) => member.title === abbrev) || null;
    const picked = editing && draft ? draft[abbrev] : "";
    const shown = editing && draft ? roster.find((member) => member.memberid === picked) || null : holder;
    return (
      <article className="officer" key={abbrev}>
        <PersonPhoto member={shown} />
        <div>
          <div className="role">{label}</div>
          {editing && draft ? (
            <label className="signin-field officer-pick">
              <span>Member</span>
              <select value={draft[abbrev] || ""} onChange={(event) => onPick(abbrev, event.target.value)}>
                <option value="">Unassigned</option>
                {roster.map((member) => (
                  <option key={member.memberid} value={member.memberid}>
                    {optionLabel(member, roster)}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <strong>{shown ? shown.display_name : "\u00a0"}</strong>
          )}
        </div>
      </article>
    );
  });
}

function RecogCard({ index, editing, recognition, onReload }) {
  const { text } = useContent();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const slot = (recognition || []).find((item) => item.slot === `recog.${index}`) || null;
  const src = slot?.url || "";
  const showDetail = editing || open;

  async function onFile(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    const problem = imageFileError(file);
    if (problem) {
      setPhotoError(problem);
      return;
    }
    setBusy(true);
    setPhotoError("");
    try {
      if (slot?.id) {
        await replaceMedia(slot.id, file);
      } else {
        const image = await uploadMedia(file);
        await assignMediaSlot(image.id, `recog.${index}`);
      }
      await onReload();
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : "Could not save the photo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="recog">
      {src ? <img className="portrait" src={src} alt="" /> : <Portrait />}
      <div>
        <Block id={`recog.${index}.title`} as="h3" />
        <p>
          <Block id={`recog.${index}.body`} />
          {showDetail ? (
            <>
              {" "}
              <Block id={`recog.${index}.detail`} />
            </>
          ) : null}{" "}
          {editing ? (
            <span className="more">{text(`recog.${index}.more`) || "Read More..."}</span>
          ) : (
            <button
              type="button"
              className="more"
              aria-expanded={open ? "true" : "false"}
              onClick={() => setOpen((value) => !value)}
            >
              {open ? "Show less" : text(`recog.${index}.more`) || "Read More..."}
            </button>
          )}
        </p>
        {editing ? (
          <div className="signin-actions recog-actions">
            <label className="btn btn-quiet">
              {src ? "Replace photo" : "Add photo"}
              <input type="file" accept={PHOTO_ACCEPT} hidden disabled={busy} onChange={onFile} />
            </label>
          </div>
        ) : null}
        {photoError ? (
          <p className="signin-error" role="alert">
            {photoError}
          </p>
        ) : null}
      </div>
    </article>
  );
}

function keepEditingClick(event) {
  if (event.target.closest(".inline-edit, .inline-input, .edit-mark")) event.preventDefault();
}

function EditBar() {
  const { editing, startEdit, cancelEdit, saveEdits } = useContent();
  return (
    <>
      <button
        type="button"
        className="edit-toggle"
        id="editToggle"
        aria-pressed={editing ? "true" : "false"}
        aria-label={editing ? "CANCEL CHANGES" : "EDIT PAGE"}
        onClick={editing ? cancelEdit : startEdit}
      >
        {editing ? "CANCEL CHANGES" : "EDIT PAGE"}
      </button>
      <button type="button" className="btn save-edits" id="saveEdits" hidden={!editing} onClick={saveEdits}>
        SAVE CHANGES
      </button>
    </>
  );
}

function MemberView() {
  const { editing, savedFlash, saveError, cancelEdit, registerSaveHook } = useContent();
  const { logout: signOut, user, refresh } = useAuth();
  const path = usePath();
  const onSettings = path === "/member/settings";
  const [navOpen, setNavOpen] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openPanels, setOpenPanels] = useState({});
  const profileRef = useRef(null);
  const hiddenRef = useRef(false);
  const roleDrafts = useRef({ officer: null, director: null });
  const [logoSrc, setLogoSrc] = useState(LOGO_SRC);
  const [recognition, setRecognition] = useState([]);
  const [roster, setRoster] = useState([]);
  const [rosterReady, setRosterReady] = useState(false);

  const onOfficerDraft = useCallback((draft) => {
    roleDrafts.current.officer = draft;
  }, []);
  const onDirectorDraft = useCallback((draft) => {
    roleDrafts.current.director = draft;
  }, []);

  function keepExampleLogo() {
    setLogoSrc((current) => (current === LOGO_SRC ? current : LOGO_SRC));
  }

  async function reloadSlots() {
    const data = await fetchMediaSlots();
    if (data?.logo) setLogoSrc(data.logo);
    if (Array.isArray(data?.recognition)) setRecognition(data.recognition);
  }

  useLayoutEffect(() => {
    document.body.className = "page-member";
    document.body.dataset.page = "member";
    document.title = onSettings ? "Settings — Council 10930" : TITLE;
  }, [onSettings]);

  useEffect(() => {
    if (onSettings && editing) cancelEdit();
  }, [onSettings, editing, cancelEdit]);

  useEffect(() => {
    let cancel = false;
    fetchMediaSlots()
      .then((data) => {
        if (cancel || !data) return;
        if (data.logo) setLogoSrc(data.logo);
        if (Array.isArray(data.recognition)) setRecognition(data.recognition);
      })
      .catch(() => {
        /* The example logo stays in the header. */
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (onSettings) return undefined;
    let cancel = false;
    fetchRoster()
      .then((rows) => {
        if (cancel) return;
        setRoster(Array.isArray(rows) ? rows : []);
        setRosterReady(true);
      })
      .catch(() => {
        /* Keep the last roster so a failed reload cannot clear titles. */
      });
    return () => {
      cancel = true;
    };
  }, [onSettings]);

  useEffect(() => {
    if (onSettings || editing || !rosterReady) return undefined;
    let cancel = false;
    fetchRoster()
      .then((rows) => {
        if (cancel || !Array.isArray(rows)) return;
        setRoster(rows);
      })
      .catch(() => {
        /* Keep the last roster so a failed reload cannot clear titles. */
      });
    return () => {
      cancel = true;
    };
  }, [onSettings, editing, rosterReady]);

  useEffect(() => {
    return registerSaveHook(async () => {
      const officer = roleDrafts.current.officer;
      const director = roleDrafts.current.director;
      if (!officer || !director) return;
      const seen = new Set();
      for (const memberid of [...Object.values(officer), ...Object.values(director)]) {
        if (!memberid) continue;
        if (seen.has(memberid)) throw new Error("A member can hold only one title.");
        seen.add(memberid);
      }
      const rows = await saveRoleAssignments({
        officer: Object.entries(officer).map(([title, memberid]) => ({
          title,
          memberid: memberid || null,
        })),
        director: Object.entries(director).map(([title, memberid]) => ({
          title,
          memberid: memberid || null,
        })),
      });
      if (Array.isArray(rows)) setRoster(rows);
      try {
        await refresh();
      } catch {
        /* The assignment is saved. The name updates on the next visit. */
      }
    });
  }, [registerSaveHook, refresh]);

  useEffect(() => {
    if (onSettings) return undefined;
    const id = window.location.hash.replace(/^#/, "");
    if (!id) return undefined;
    const node = document.getElementById(id);
    if (node) node.scrollIntoView();
    return undefined;
  }, [onSettings]);

  useEffect(() => {
    let lastY = window.scrollY;
    let travel = 0;
    let ignoreUntil = 0;
    function onScroll() {
      const y = window.scrollY;
      const delta = y - lastY;
      lastY = y;
      if (!window.matchMedia("(max-width: 820px)").matches) {
        if (hiddenRef.current) {
          hiddenRef.current = false;
          setNavHidden(false);
        }
        travel = 0;
        return;
      }
      if (Date.now() < ignoreUntil) return;
      if (Math.abs(delta) < 4) return;
      if ((delta > 0 && travel < 0) || (delta < 0 && travel > 0)) travel = 0;
      travel += delta;
      if (y < 32) {
        if (hiddenRef.current) {
          hiddenRef.current = false;
          setNavHidden(false);
        }
        travel = 0;
        return;
      }
      if (travel > 36 && y > 72 && !hiddenRef.current) {
        hiddenRef.current = true;
        setNavHidden(true);
        setNavOpen(false);
        ignoreUntil = Date.now() + 350;
        travel = 0;
      } else if (travel < -48 && hiddenRef.current) {
        hiddenRef.current = false;
        setNavHidden(false);
        ignoreUntil = Date.now() + 350;
        travel = 0;
      }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    function onDoc(event) {
      if (!profileRef.current?.contains(event.target)) setMenuOpen(false);
    }
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);

  function closeNav() {
    setNavOpen(false);
  }

  function togglePanel(panel) {
    if (editing) return;
    setOpenPanels((current) => ({ ...current, [panel]: !current[panel] }));
  }

  async function logout() {
    setMenuOpen(false);
    await signOut();
    navigate("/");
  }

  function settings() {
    setMenuOpen(false);
    navigate("/member/settings");
  }

  function sectionProps(hash) {
    if (!onSettings) return { href: `#${hash}`, onClick: closeNav };
    return {
      href: `/member#${hash}`,
      onClick: (event) => {
        closeNav();
        event.preventDefault();
        navigate(`/member#${hash}`);
      },
    };
  }

  return (
    <>
      <a className="skip" href="#main">
        Skip to members content
      </a>
      <header className={navHidden ? "site nav-hidden" : "site"}>
        <a
          className="brand"
          href={onSettings ? "/member" : "#top"}
          onClick={(event) => {
            keepEditingClick(event);
            if (!onSettings) return;
            event.preventDefault();
            navigate("/member");
          }}
        >
          <img className="hero-medallion-navbar" src={logoSrc} alt="" onError={keepExampleLogo} />
          <span>
            <Block id="brand.name" className="name" locked />
            <Block id="brand.sub" className="sub" locked />
          </span>
        </a>
        <div className="head-right">
          <button
            className="nav-toggle"
            id="navToggle"
            type="button"
            aria-label={navOpen ? "Close section menu" : "Open section menu"}
            aria-expanded={navOpen ? "true" : "false"}
            aria-controls="siteNav"
            onClick={() => setNavOpen((open) => !open)}
          >
            <span />
            <span />
            <span />
          </button>
          {user?.is_admin && !onSettings ? <EditBar /> : null}
          <div className="profile" ref={profileRef}>
            <button
              type="button"
              className="profile-btn"
              id="profileBtn"
              aria-expanded={menuOpen ? "true" : "false"}
              aria-controls="profileMenu"
              aria-haspopup="true"
              onClick={(event) => {
                if (event.target.closest(".inline-edit, .inline-input, .edit-mark")) return;
                setMenuOpen((open) => !open);
              }}
            >
              <MemberAvatar user={user} />
              <span className="profile-name">{memberLabel(user)}</span>
            </button>
            <div className="profile-menu" id="profileMenu" role="menu" hidden={!menuOpen}>
              <button type="button" role="menuitem" id="settingsBtn" onClick={settings}>
                Settings
              </button>
              <button type="button" role="menuitem" id="logoutBtn" onClick={logout}>
                Log out
              </button>
            </div>
          </div>
        </div>
        <nav className={navOpen ? "site-nav open" : "site-nav"} id="siteNav" aria-label="Page sections">
          <Block id="nav.about" locked {...sectionProps("about")} />
          <Block id="nav.officers" locked {...sectionProps("officers")} />
          <Block id="nav.directors" locked {...sectionProps("directors")} />
          <Block id="nav.events" locked {...sectionProps("events")} />
          <Block id="nav.blood" locked {...sectionProps("blood")} />
          <Block id="nav.links" locked {...sectionProps("links")} />
        </nav>
      </header>

      {onSettings ? null : (
      <section className="member-hero" id="top">
        <div className="container">
          <Eyebrow id="hero.eyebrow" locked />
          <Block id="hero.title" as="h1" locked />
          <Block id="hero.place" as="div" className="place" locked />
        </div>
      </section>
      )}

      <main id="main">
        {onSettings ? <SettingsView /> : null}
        {onSettings ? null : (
        <>
        <div className="container">
          <section id="about" aria-labelledby="aboutHeading">
            <div className="section-head">
              <Eyebrow id="about.eyebrow" />
              <Block id="about.title" as="h2" htmlId="aboutHeading" />
            </div>
            <div className="schedule">
              {range(4).map((index) => (
                <article className={index === 3 ? "sched wide" : "sched"} key={`sched-${index}`}>
                  <Block id={`sched.${index}.title`} as="h3" />
                  <Block id={`sched.${index}.body`} as="p" lines={index === 3} />
                </article>
              ))}
            </div>
            <div className="recog-grid">
              {range(4).map((index) => (
                <RecogCard
                  key={`recog-${index}`}
                  index={index}
                  editing={editing}
                  recognition={recognition}
                  onReload={reloadSlots}
                />
              ))}
            </div>
          </section>

          <HonorsSection />

          <section className="block" id="officers" aria-labelledby="officersHeading">
            <div className="section-head">
              <Eyebrow id="officers.eyebrow" />
              <Block id="officers.title" as="h2" htmlId="officersHeading" locked />
              <Block id="officers.intro" as="p" htmlId="headlineIntro" />
            </div>
            <div className="officer-grid" id="officerGrid">
              <RoleGrid
                roles={OFFICER_ROLES}
                roster={roster}
                ready={rosterReady}
                editing={editing}
                onDraft={onOfficerDraft}
              />
            </div>
          </section>

          <section className="block" id="directors" aria-labelledby="directorsHeading">
            <div className="section-head">
              <Eyebrow id="directors.eyebrow" />
              <Block id="directors.title" as="h2" htmlId="directorsHeading" locked />
              <Block id="directors.intro" as="p" htmlId="directorIntro" />
            </div>
            <div className="officer-grid" id="directorGrid">
              <RoleGrid
                roles={DIRECTOR_ROLES}
                roster={roster}
                ready={rosterReady}
                editing={editing}
                onDraft={onDirectorDraft}
              />
            </div>
          </section>

          <section className="block" id="events" aria-labelledby="eventsHeading">
            <div className="section-head">
              <Eyebrow id="events.eyebrow" />
              <Block id="events.title" as="h2" htmlId="eventsHeading" locked />
            </div>
            <EventsSection />
          </section>
        </div>

        <section className="on-navy" id="blood">
          <div className="container split">
            <div>
              <Eyebrow id="blood.eyebrow" />
              <Block
                id="blood.title"
                as="h2"
                className="serif"
                style={{ fontSize: "2.1rem", fontWeight: 600, margin: "0.3rem 0 0.4rem" }}
              />
              <Block id="blood.place" as="p" className="muted" />
              <Block id="blood.when" as="p" className="muted" />
              <p className="muted">
                <Block id="blood.before" />{" "}
                <Block
                  id="blood.link"
                  href="https://www.redcrossblood.org"
                  target="_blank"
                  rel="noopener noreferrer"
                />
                <Block id="blood.after" />
              </p>
            </div>
            <div className="stats" aria-label="Donation statistics">
              {range(3).map((index) => (
                <div className="stat" key={`stat-${index}`}>
                  <Block id={`stat.${index}.value`} as="b" />
                  <Block id={`stat.${index}.label`} />
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="container tools" id="links">
          <section id="quickLinks" aria-labelledby="qlHeading">
            <div className="section-head" style={{ marginTop: "1rem" }}>
              <Eyebrow id="links.eyebrow" />
              <Block id="links.title" as="h2" htmlId="qlHeading" />
              <Block id="links.intro" as="p" />
            </div>
            <div className="link-grid">
              {LINK_CARDS.map((card) => {
                const shown = Boolean(editing || (card.panel && openPanels[card.panel]));
                return (
                  <article className="link-card" key={card.title}>
                    <div className="link-copy">
                      <Block id={card.title} as="h3" />
                      {card.body ? <Block id={card.body} as="p" /> : null}
                    </div>
                    {card.href ? (
                      <Block
                        id={card.action}
                        className="btn"
                        href={card.href}
                        target={card.external ? "_blank" : undefined}
                        rel={card.external ? "noopener noreferrer" : undefined}
                      />
                    ) : (
                      <Block
                        id={card.action}
                        className="btn"
                        control
                        ariaExpanded={shown ? "true" : "false"}
                        ariaControls={card.panel}
                        onClick={() => togglePanel(card.panel)}
                      />
                    )}
                    {card.panel ? (
                      <div className="detail" id={card.panel} hidden={!shown}>
                        {card.hours ? (
                          <p>
                            <Block id="links.9.before" />{" "}
                            <Block
                              id="links.9.link"
                              href="https://www.UKnightMobile.org"
                              target="_blank"
                              rel="noopener noreferrer"
                            />
                            <Block id="links.9.after" />
                          </p>
                        ) : (
                          <Block id={card.detail} as="p" />
                        )}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </section>
        </div>
        </>
        )}
      </main>

      <footer>
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <img className="hero-medallion-navbar" src={logoSrc} alt="" onError={keepExampleLogo} />
              <span>
                <Block id="footer.name" className="name" />
                <Block id="footer.sub" className="sub" />
              </span>
            </div>
            <nav className="footer-nav" aria-label="Footer">
              <Block id="footer.nav.about" {...sectionProps("about")} />
              <Block id="footer.nav.officers" {...sectionProps("officers")} />
              <Block id="footer.nav.directors" {...sectionProps("directors")} />
              <Block id="footer.nav.events" {...sectionProps("events")} />
              <Block id="footer.nav.blood" {...sectionProps("blood")} />
              <Block id="footer.nav.links" {...sectionProps("links")} />
              <Block
                id="footer.nav.public"
                href="/"
                htmlId="publicLink"
                onClick={(event) => {
                  event.preventDefault();
                  navigate("/");
                }}
              />
            </nav>
          </div>
          <div className="footer-bottom">
            <Block id="footer.copy" />
            <Block id="footer.principles" />
          </div>
        </div>
      </footer>
      <div
        id="saveStatus"
        className="save-status"
        role="status"
        aria-live="polite"
        hidden={!savedFlash && !saveError}
      >
        {saveError || "Saved"}
      </div>
    </>
  );
}

export default function MemberPage() {
  const { user } = useAuth();
  return (
    <ContentProvider slug="member" canEdit={Boolean(user?.is_admin)}>
      <MemberView />
    </ContentProvider>
  );
}
