import { useEffect, useState } from "react";
import { fetchAnnouncement } from "../api";
import { exampleAnnouncement } from "../content/announcements";
import { LOGO_SRC, SITE_TITLE } from "../content/seed";
import { MONTHS } from "../content/records";
import { navigate } from "../router";
import { sanitizeHtml } from "../sanitizeHtml";

function formatPostedOn(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
  if (!match) return "";
  const month = MONTHS[Number(match[2]) - 1];
  if (!month) return "";
  return `${month} ${Number(match[3])}, ${match[1]}`;
}

export default function AnnouncementReader({ id }) {
  const example = exampleAnnouncement(id);
  const [item, setItem] = useState(null);
  const [problem, setProblem] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const title = item?.title ? `${item.title} | Council 10930` : SITE_TITLE;
    document.title = title;
  }, [item]);

  useEffect(() => {
    if (example) {
      setItem(example);
      setProblem("");
      setLoaded(true);
      return undefined;
    }
    let cancel = false;
    setLoaded(false);
    setProblem("");
    setItem(null);
    fetchAnnouncement(id)
      .then((row) => {
        if (cancel) return;
        setItem(row);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setItem(null);
        setProblem("This announcement is unavailable right now.");
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, [example, id]);

  const body = item ? sanitizeHtml(item.body || "") : "";

  return (
    <div className="announcement-page">
      <header className="announcement-bar">
        <a
          className="brand"
          href="/member"
          onClick={(event) => {
            event.preventDefault();
            navigate("/member");
          }}
        >
          <img className="hero-medallion-navbar" src={LOGO_SRC} alt="" />
          <span>
            <span className="name">Council 10930</span>
            <span className="sub">Knights of Columbus</span>
          </span>
        </a>
      </header>
      <main id="main" className="container">
        {!loaded ? <p className="settings-hint">Loading…</p> : null}
        {problem ? (
          <p className="signin-error" role="alert">
            {problem}
          </p>
        ) : null}
        {item ? (
          <>
            <p className="eyebrow left-only">Announcement</p>
            <h1>{item.title}</h1>
            {item.posted_on ? <p className="announcement-date">{formatPostedOn(item.posted_on)}</p> : null}
            {item.summary ? <p className="announcement-summary">{item.summary}</p> : null}
            <div className="announcement-body" dangerouslySetInnerHTML={{ __html: body }} />
          </>
        ) : null}
      </main>
    </div>
  );
}
