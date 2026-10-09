import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Block, Eyebrow } from "../components/Block";
import { Avatar, Emblem, Portrait, PortraitSm } from "../components/Marks";
import { ContentProvider, useContent } from "../content/ContentContext";
import { DIRECTOR_COUNT, EVENT_COUNT, OFFICER_COUNT } from "../content/seed";
import { navigate } from "../router";

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

function People({ prefix, count }) {
  return range(count).map((index) => (
    <article className="officer" key={`${prefix}-${index}`}>
      <PortraitSm />
      <div>
        <Block id={`${prefix}.${index}.role`} as="div" className="role" />
        <Block id={`${prefix}.${index}.name`} as="strong" />
      </div>
    </article>
  ));
}

function MemberView() {
  const { editing, savedFlash } = useContent();
  const [navOpen, setNavOpen] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [openPanels, setOpenPanels] = useState({});
  const profileRef = useRef(null);
  const hiddenRef = useRef(false);

  useLayoutEffect(() => {
    document.body.className = "page-member";
    document.body.dataset.page = "member";
    document.title = TITLE;
  }, []);

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

  function logout() {
    setMenuOpen(false);
    sessionStorage.removeItem("koc10930.token");
    navigate("/");
  }

  function settings() {
    setMenuOpen(false);
    window.alert("Settings. Replace this with the member settings page.");
  }

  return (
    <>
      <a className="skip" href="#main">
        Skip to members content
      </a>
      <header className={navHidden ? "site nav-hidden" : "site"}>
        <a className="brand" href="#top" onClick={keepEditingClick}>
          <Emblem className="mark" />
          <span>
            <Block id="brand.name" className="name" />
            <Block id="brand.sub" className="sub" />
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
          <EditBar />
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
              <Avatar />
              <Block id="profile.name" className="profile-name" />
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
          <Block id="nav.about" href="#about" locked onClick={closeNav} />
          <Block id="nav.officers" href="#officers" locked onClick={closeNav} />
          <Block id="nav.directors" href="#directors" locked onClick={closeNav} />
          <Block id="nav.events" href="#events" locked onClick={closeNav} />
          <Block id="nav.blood" href="#blood" locked onClick={closeNav} />
          <Block id="nav.links" href="#links" locked onClick={closeNav} />
        </nav>
      </header>

      <section className="member-hero" id="top">
        <div className="container">
          <Eyebrow id="hero.eyebrow" />
          <Block id="hero.title" as="h1" />
          <Block id="hero.place" as="div" className="place" />
        </div>
      </section>

      <main id="main">
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
                <article className="recog" key={`recog-${index}`}>
                  <Portrait />
                  <div>
                    <Block id={`recog.${index}.title`} as="h3" />
                    <p>
                      <Block id={`recog.${index}.body`} /> <Block id={`recog.${index}.more`} className="more" href="#about" />
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="block" id="officers" aria-labelledby="officersHeading">
            <div className="section-head">
              <Eyebrow id="officers.eyebrow" />
              <Block id="officers.title" as="h2" htmlId="officersHeading" />
              <Block id="officers.intro" as="p" htmlId="headlineIntro" />
            </div>
            <div className="officer-grid" id="officerGrid">
              <People prefix="officer" count={OFFICER_COUNT} />
            </div>
          </section>

          <section className="block" id="directors" aria-labelledby="directorsHeading">
            <div className="section-head">
              <Eyebrow id="directors.eyebrow" />
              <Block id="directors.title" as="h2" htmlId="directorsHeading" />
              <Block id="directors.intro" as="p" htmlId="directorIntro" />
            </div>
            <div className="officer-grid" id="directorGrid">
              <People prefix="director" count={DIRECTOR_COUNT} />
            </div>
          </section>

          <section className="block" id="events" aria-labelledby="eventsHeading">
            <div className="section-head">
              <Eyebrow id="events.eyebrow" />
              <Block id="events.title" as="h2" htmlId="eventsHeading" />
            </div>
            <div className="card-grid" id="eventList">
              {range(EVENT_COUNT).map((index) => (
                <article className="event" key={`event-${index}`}>
                  <Block id={`event.${index}.when`} as="div" className="when" />
                  <Block id={`event.${index}.title`} as="strong" />
                  <Block id={`event.${index}.more`} className="more" href="#events" />
                </article>
              ))}
            </div>
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
      </main>

      <footer>
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <Emblem />
              <span>
                <Block id="footer.name" className="name" />
                <Block id="footer.sub" className="sub" />
              </span>
            </div>
            <nav className="footer-nav" aria-label="Footer">
              <Block id="footer.nav.about" href="#about" />
              <Block id="footer.nav.officers" href="#officers" />
              <Block id="footer.nav.directors" href="#directors" />
              <Block id="footer.nav.events" href="#events" />
              <Block id="footer.nav.blood" href="#blood" />
              <Block id="footer.nav.links" href="#links" />
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
      <div id="saveStatus" className="save-status" role="status" aria-live="polite" hidden={!savedFlash}>
        Saved
      </div>
    </>
  );
}

export default function MemberPage() {
  return (
    <ContentProvider slug="member">
      <MemberView />
    </ContentProvider>
  );
}
