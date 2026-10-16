import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { fetchMediaSlots, fetchRoster, imageFileError, replaceMedia, saveRoleAssignments, updateMediaCrop, uploadMedia, assignMediaSlot } from "../api";
import { useAuth } from "../auth/AuthContext";
import { Block, Eyebrow } from "../components/Block";
import CroppedPhoto from "../components/CroppedPhoto";
import { Avatar, Portrait, PortraitSm } from "../components/Marks";
import PhotoEditor, { PHOTO_ACCEPT } from "../components/PhotoEditor";
import { ContentProvider, useContent } from "../content/ContentContext";
import { birthdayGroups } from "../birthdays";
import { LOGO_SRC, SITE_TITLE } from "../content/seed";
import { DEFAULT_YEAR, FIXED_CHROME, YEAR_KEY, fraternalPhrases, normalizeFraternalYear } from "../content/year";
import DocumentLibrary from "./DocumentLibrary";
import EventsSection from "./EventsSection";
import HonorsSection from "./HonorsSection";
import SettingsView from "./SettingsView";
import { navigate, usePath } from "../router";
import { DIRECTOR_ROLES, memberLabel, OFFICER_ROLES } from "../titles";

const TITLE = SITE_TITLE;

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
  { title: "links.6.title", action: "links.6.action", detail: "links.6.detail", panel: "panel-comments" },
  { title: "links.9.title", action: "links.9.action", panel: "panel-hours", hours: true },
  { title: "links.11.title", action: "links.11.action", detail: "links.11.detail", panel: "panel-nominate" },
  { title: "links.12.title", action: "links.12.action", panel: "panel-fs", library: "financial_secretary" },
  { title: "links.13.title", action: "links.13.action", panel: "panel-treasurer", library: "treasurer" },
  { title: "links.14.title", action: "links.14.action", detail: "links.14.detail", panel: "panel-budget" },
  { title: "links.15.title", action: "links.15.action", href: "mailto:webmaster@council10930.example" },
];

function range(count) {
  return Array.from({ length: count }, (_, index) => index);
}

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
  const { text, draftText, setDraft } = useContent();
  const [open, setOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [snapshot, setSnapshot] = useState(null);
  const [busy, setBusy] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const [photoFailed, setPhotoFailed] = useState(false);
  const [photoEditor, setPhotoEditor] = useState(null);
  const photoRef = useRef(null);
  const titleId = `recog.${index}.title`;
  const bodyId = `recog.${index}.body`;
  const detailId = `recog.${index}.detail`;
  const slot = (recognition || []).find((item) => item.slot === `recog.${index}`) || null;
  const src = slot?.url || "";
  const title = editing ? draftText(titleId) : text(titleId);
  const body = editing ? draftText(bodyId) : text(bodyId);
  const detail = editing ? draftText(detailId) : text(detailId);
  photoRef.current = photoEditor;

  useEffect(() => {
    setPhotoFailed(false);
  }, [src]);

  useEffect(() => {
    return () => {
      const current = photoRef.current;
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
    };
  }, []);

  function closePhotoEditor() {
    setPhotoEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return null;
    });
  }

  useEffect(() => {
    if (!editing) {
      setFormOpen(false);
      closePhotoEditor();
    }
  }, [editing]);

  function beginEdit() {
    setSnapshot({
      title: draftText(titleId),
      body: draftText(bodyId),
      detail: draftText(detailId),
    });
    setFormOpen(true);
  }

  function revertCopy() {
    if (snapshot) {
      setDraft(titleId, snapshot.title);
      setDraft(bodyId, snapshot.body);
      setDraft(detailId, snapshot.detail);
    }
    setFormOpen(false);
  }

  function openExisting() {
    setPhotoError("");
    setPhotoEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return {
        src,
        file: null,
        ownedUrl: false,
        crop: { x: slot?.crop_x || 0, y: slot?.crop_y || 0, scale: slot?.crop_scale || 1 },
      };
    });
  }

  function onPick(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) return;
    const problem = imageFileError(file);
    if (problem) {
      setPhotoError(problem);
      return;
    }
    const url = URL.createObjectURL(file);
    setPhotoError("");
    setPhotoEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return { src: url, file, ownedUrl: true, crop: { x: 0, y: 0, scale: 1 } };
    });
  }

  async function onSavePhoto(crop) {
    const chosen = photoEditor;
    if (!chosen?.src) return;
    setBusy(true);
    setPhotoError("");
    try {
      if (chosen.file) {
        if (slot?.id) {
          await replaceMedia(slot.id, chosen.file, crop);
        } else {
          const image = await uploadMedia(chosen.file, crop);
          await assignMediaSlot(image.id, `recog.${index}`);
        }
      } else if (slot?.id) {
        await updateMediaCrop(slot.id, crop);
      } else {
        setPhotoError("Choose an image file.");
        return;
      }
      await onReload();
      closePhotoEditor();
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : "Could not save the photo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="recog">
      {src && !photoFailed ? (
        <CroppedPhoto className="portrait" src={src} crop={slot} onError={() => setPhotoFailed(true)} />
      ) : (
        <Portrait />
      )}
      <div>
        {editing && formOpen ? (
          <>
            <DraftFields
              fields={[
                { id: titleId, label: "Title" },
                { id: bodyId, label: "Summary", long: true },
                { id: detailId, label: "Details", long: true },
              ]}
            />
            <div className="signin-actions recog-actions">
              <button type="button" className="btn btn-quiet" onClick={() => setFormOpen(false)}>
                Done
              </button>
              <button type="button" className="btn btn-quiet" onClick={revertCopy}>
                Cancel
              </button>
            </div>
          </>
        ) : (
          <>
            <h3>{title}</h3>
            <p>
              {body}{" "}
              {open ? <>{detail} </> : null}
              <button
                type="button"
                className="more"
                aria-expanded={open ? "true" : "false"}
                onClick={() => setOpen((value) => !value)}
              >
                {open ? "Show less" : "Read More..."}
              </button>
            </p>
            {editing ? (
              <div className="signin-actions recog-actions">
                <button type="button" className="btn btn-quiet" onClick={beginEdit}>
                  Edit
                </button>
              </div>
            ) : null}
          </>
        )}
        {editing && photoEditor ? (
          <PhotoEditor
            key={photoEditor.src || "empty"}
            src={photoEditor.src}
            initial={photoEditor.crop}
            pending={busy}
            onSave={onSavePhoto}
            onCancel={closePhotoEditor}
            onSwap={onPick}
          />
        ) : null}
        {editing && !photoEditor ? (
          <div className="signin-actions recog-actions">
            {src ? (
              <button type="button" className="btn btn-quiet" disabled={busy} onClick={openExisting}>
                Change photo
              </button>
            ) : (
              <label className="btn btn-quiet">
                Add photo
                <input type="file" accept={PHOTO_ACCEPT} hidden disabled={busy} onChange={onPick} />
              </label>
            )}
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
  const { editing, startEdit, cancelEdit, saveEdits, draftText, setFraternalYear } = useContent();
  const yearValue = draftText(YEAR_KEY);
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
      {editing ? (
        <label className="year-field">
          <span>Fraternal year</span>
          <input
            value={yearValue}
            maxLength={9}
            inputMode="text"
            autoComplete="off"
            spellCheck={false}
            aria-label="Fraternal year"
            placeholder="2026–27"
            onChange={(event) => setFraternalYear(event.target.value)}
          />
        </label>
      ) : null}
      <button type="button" className="btn save-edits" id="saveEdits" hidden={!editing} onClick={saveEdits}>
        SAVE CHANGES
      </button>
    </>
  );
}

function YearText({ id, as: Tag = "p", className, htmlId }) {
  const { editing, draftText, text } = useContent();
  const raw = editing ? draftText(YEAR_KEY) : text(YEAR_KEY);
  const year = normalizeFraternalYear(raw) || normalizeFraternalYear(text(YEAR_KEY)) || DEFAULT_YEAR;
  return (
    <Tag id={htmlId} className={className}>
      {fraternalPhrases(year)[id]}
    </Tag>
  );
}

function FixedText({ id, as: Tag = "p", className, htmlId, style }) {
  return (
    <Tag id={htmlId} className={className} style={style}>
      {FIXED_CHROME[id]}
    </Tag>
  );
}

function DraftFields({ fields }) {
  const { draftText, setDraft, editing } = useContent();
  const idKey = fields.map((field) => field.id).join("|");
  const [values, setValues] = useState(() =>
    Object.fromEntries(fields.map((field) => [field.id, draftText(field.id)])),
  );

  useEffect(() => {
    setValues(Object.fromEntries(fields.map((field) => [field.id, draftText(field.id)])));
  }, [editing, idKey]);

  function update(id, value, long) {
    const next = long ? String(value).replace(/\r?\n/g, " ") : value;
    setValues((current) => ({ ...current, [id]: next }));
    setDraft(id, next);
  }

  return (
    <div className="honor-form">
      {fields.map((field) => (
        <label className="signin-field" key={field.id}>
          <span>{field.label}</span>
          {field.lines || field.long ? (
            <textarea
              value={values[field.id] ?? ""}
              onChange={(event) => update(field.id, event.target.value, field.long && !field.lines)}
            />
          ) : (
            <input
              type="text"
              value={values[field.id] ?? ""}
              onChange={(event) => update(field.id, event.target.value, false)}
            />
          )}
        </label>
      ))}
    </div>
  );
}

function ScheduleCard({ index }) {
  const { editing, text, draftText, setDraft } = useContent();
  const [open, setOpen] = useState(false);
  const [snapshot, setSnapshot] = useState(null);
  const titleId = `sched.${index}.title`;
  const bodyId = `sched.${index}.body`;
  const lines = index === 3;

  useEffect(() => {
    if (!editing) setOpen(false);
  }, [editing]);

  const title = editing ? draftText(titleId) : text(titleId);
  const body = editing ? draftText(bodyId) : text(bodyId);

  function beginEdit() {
    setSnapshot({ title: draftText(titleId), body: draftText(bodyId) });
    setOpen(true);
  }

  function revert() {
    if (snapshot) {
      setDraft(titleId, snapshot.title);
      setDraft(bodyId, snapshot.body);
    }
    setOpen(false);
  }

  return (
    <article className={index === 3 ? "sched wide" : "sched"}>
      {editing && open ? (
        <>
          <DraftFields
            fields={[
              { id: titleId, label: "Title" },
              { id: bodyId, label: "Details", lines },
            ]}
          />
          <div className="signin-actions recog-actions">
            <button type="button" className="btn btn-quiet" onClick={() => setOpen(false)}>
              Done
            </button>
            <button type="button" className="btn btn-quiet" onClick={revert}>
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <h3>{title}</h3>
          <p>
            {String(body)
              .split("\n")
              .map((line, lineIndex) => (
                <span key={`${bodyId}-${lineIndex}`}>
                  {lineIndex > 0 ? <br /> : null}
                  {line}
                </span>
              ))}
          </p>
          {editing ? (
            <div className="signin-actions recog-actions">
              <button type="button" className="btn btn-quiet" onClick={beginEdit}>
                Edit
              </button>
            </div>
          ) : null}
        </>
      )}
    </article>
  );
}

function linkFields(card) {
  if (card.panel === "panel-birthdays" || card.library) return [];
  const fields = [];
  if (card.body) fields.push({ id: card.body, label: "Summary", long: true });
  if (card.hours) {
    fields.push(
      { id: "links.9.before", label: "Link lead-in" },
      { id: "links.9.link", label: "Link label" },
      { id: "links.9.after", label: "Link ending" },
    );
  } else if (card.detail) {
    fields.push({ id: card.detail, label: "Details", long: true });
  }
  return fields;
}

function LinkAction({ card, shown, onToggle }) {
  const { text } = useContent();
  const label = card.panel === "panel-birthdays" ? (shown ? "View less" : "View more") : text(card.action);
  if (card.href) {
    return (
      <a
        className="btn"
        href={card.href}
        target={card.external ? "_blank" : undefined}
        rel={card.external ? "noopener noreferrer" : undefined}
      >
        {label}
      </a>
    );
  }
  return (
    <button
      type="button"
      className="btn"
      aria-expanded={card.panel ? (shown ? "true" : "false") : undefined}
      aria-controls={card.panel || undefined}
      onClick={onToggle}
    >
      {label}
    </button>
  );
}

function BirthdayList({ roster, ready, onHide }) {
  const groups = birthdayGroups(roster);
  const total = groups.reduce((count, group) => count + group.people.length, 0);
  function hideControl(key) {
    return (
      <button type="button" className="more birthday-hide" onClick={onHide} key={key}>
        View less
      </button>
    );
  }
  if (!ready) return <p>Loading…</p>;
  return (
    <>
      {total > 8 ? hideControl("top") : null}
      {groups.map((group) => (
        <div key={group.month}>
          <p className="birthday-month">{group.label}</p>
          {group.people.length === 0 ? (
            <p>No birthdays.</p>
          ) : (
            <ul className="birthday-list">
              {group.people.map((person) => (
                <li key={person.memberid}>
                  <span className="when">{person.day}</span>
                  <span>{person.name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      {hideControl("bottom")}
    </>
  );
}

function MemberView() {
  const { editing, savedFlash, saveError, cancelEdit, registerSaveHook, applyFraternalYear } = useContent();
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
    document.title = TITLE;
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
      applyFraternalYear();
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
  }, [registerSaveHook, refresh, applyFraternalYear]);

  useEffect(() => {
    if (onSettings) return undefined;
    const id = window.location.hash.replace(/^#/, "");
    if (!id) return undefined;
    if (id === "birthdays" || id === "panel-birthdays") {
      setOpenPanels((current) => ({ ...current, "panel-birthdays": true }));
    }
    const node = document.getElementById(id === "panel-birthdays" ? "birthdays" : id);
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
    setOpenPanels((current) => ({ ...current, [panel]: !current[panel] }));
  }

  function openBirthdays(event) {
    closeNav();
    if (onSettings) {
      event.preventDefault();
      navigate("/member#birthdays");
      return;
    }
    event.preventDefault();
    setOpenPanels((current) => ({ ...current, "panel-birthdays": true }));
    window.requestAnimationFrame(() => {
      document.getElementById("birthdays")?.scrollIntoView();
    });
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
          {user?.is_admin && !onSettings ? (
            <div className="admin-cluster">
              <EditBar />
            </div>
          ) : null}
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
              <button
                type="button"
                role="menuitem"
                id="publicLinkMenu"
                onClick={() => {
                  setMenuOpen(false);
                  navigate("/");
                }}
              >
                Public page
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
          <a href={onSettings ? "/member#honors" : "#honors"} onClick={sectionProps("honors").onClick}>
            Honors
          </a>
          <a href={onSettings ? "/member#birthdays" : "#birthdays"} onClick={openBirthdays}>
            Birthdays
          </a>
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
              <FixedText id="about.eyebrow" as="div" className="eyebrow" />
              <FixedText id="about.title" as="h2" htmlId="aboutHeading" />
            </div>
            <div className="schedule">
              {range(4).map((index) => (
                <ScheduleCard index={index} key={`sched-${index}`} />
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

          <section className="block" id="officers" aria-labelledby="officersHeading">
            <div className="section-head">
              <YearText id="officers.eyebrow" as="div" className="eyebrow" />
              <Block id="officers.title" as="h2" htmlId="officersHeading" locked />
              <YearText id="officers.intro" as="p" htmlId="headlineIntro" />
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
              <YearText id="directors.eyebrow" as="div" className="eyebrow" />
              <Block id="directors.title" as="h2" htmlId="directorsHeading" locked />
              <YearText id="directors.intro" as="p" htmlId="directorIntro" />
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
              <FixedText id="events.eyebrow" as="div" className="eyebrow" />
              <Block id="events.title" as="h2" htmlId="eventsHeading" locked />
            </div>
            <EventsSection />
          </section>
        </div>

        <section className="on-navy" id="blood">
          <div className="container split">
            <div>
              <FixedText id="blood.eyebrow" as="div" className="eyebrow" />
              <FixedText
                id="blood.title"
                as="h2"
                className="serif"
                style={{ fontSize: "2.1rem", fontWeight: 600, margin: "0.3rem 0 0.4rem" }}
              />
              {editing ? (
                <div className="card blood-edit">
                  <DraftFields
                    fields={[
                      { id: "blood.place", label: "Location" },
                      { id: "blood.when", label: "Date and time" },
                      { id: "blood.before", label: "Link lead-in" },
                      { id: "blood.link", label: "Link label" },
                      { id: "blood.after", label: "Link ending" },
                    ]}
                  />
                </div>
              ) : (
                <>
                  <Block id="blood.place" as="p" className="muted" locked />
                  <Block id="blood.when" as="p" className="muted" locked />
                  <p className="muted">
                    <Block id="blood.before" locked />{" "}
                    <Block
                      id="blood.link"
                      href="https://www.redcrossblood.org"
                      target="_blank"
                      rel="noopener noreferrer"
                      locked
                    />
                    <Block id="blood.after" locked />
                  </p>
                </>
              )}
            </div>
            <div className="stats" aria-label="Donation statistics">
              {editing ? (
                <div className="card blood-edit">
                  <DraftFields
                    fields={range(3).flatMap((index) => [
                      { id: `stat.${index}.value`, label: `Stat ${index + 1} number` },
                      { id: `stat.${index}.label`, label: `Stat ${index + 1} label` },
                    ])}
                  />
                </div>
              ) : (
                range(3).map((index) => (
                  <div className="stat" key={`stat-${index}`}>
                    <Block id={`stat.${index}.value`} as="b" locked />
                    <Block id={`stat.${index}.label`} locked />
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <div className="container">
          <HonorsSection />
        </div>

        <div className="container tools" id="links">
          <section id="quickLinks" aria-labelledby="qlHeading">
            <div className="section-head" style={{ marginTop: "1rem" }}>
              <FixedText id="links.eyebrow" as="div" className="eyebrow" />
              <FixedText id="links.title" as="h2" htmlId="qlHeading" />
              <FixedText id="links.intro" as="p" />
            </div>
            <div className="link-grid">
              {LINK_CARDS.map((card) => {
                const shown = Boolean(card.panel && openPanels[card.panel]);
                const birthdays = card.panel === "panel-birthdays";
                const fields = linkFields(card);
                const showForm = editing && fields.length > 0 && (shown || !card.panel);
                return (
                  <article className="link-card" id={birthdays ? "birthdays" : undefined} key={card.title}>
                    <div className="link-copy">
                      <Block id={card.title} as="h3" locked />
                      {card.body && !showForm ? <Block id={card.body} as="p" locked /> : null}
                    </div>
                    <LinkAction
                      card={card}
                      shown={shown}
                      onToggle={card.panel ? () => togglePanel(card.panel) : undefined}
                    />
                    {showForm && !card.panel ? <DraftFields fields={fields} /> : null}
                    {card.panel ? (
                      <div className="detail" id={card.panel} hidden={!shown}>
                        {card.library ? (
                          shown ? (
                            <DocumentLibrary
                              library={card.library}
                              canManage={Boolean(editing && user?.is_admin)}
                            />
                          ) : null
                        ) : birthdays ? (
                          <BirthdayList
                            roster={roster}
                            ready={rosterReady}
                            onHide={() => setOpenPanels((current) => ({ ...current, [card.panel]: false }))}
                          />
                        ) : showForm ? (
                          <DraftFields fields={fields} />
                        ) : card.hours ? (
                          <p>
                            <Block id="links.9.before" locked />{" "}
                            <Block
                              id="links.9.link"
                              href="https://www.UKnightMobile.org"
                              target="_blank"
                              rel="noopener noreferrer"
                              locked
                            />
                            <Block id="links.9.after" locked />
                          </p>
                        ) : (
                          <Block id={card.detail} as="p" locked />
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
                <Block id="footer.name" className="name" locked />
                <Block id="footer.sub" className="sub" locked />
              </span>
            </div>
            <nav className="footer-nav" aria-label="Footer">
              <Block id="footer.nav.about" locked {...sectionProps("about")} />
              <Block id="footer.nav.officers" locked {...sectionProps("officers")} />
              <Block id="footer.nav.directors" locked {...sectionProps("directors")} />
              <Block id="footer.nav.events" locked {...sectionProps("events")} />
              <Block id="footer.nav.blood" locked {...sectionProps("blood")} />
              <a href={onSettings ? "/member#honors" : "#honors"} onClick={sectionProps("honors").onClick}>
                Honors
              </a>
              <a href={onSettings ? "/member#birthdays" : "#birthdays"} onClick={openBirthdays}>
                Birthdays
              </a>
              <Block id="footer.nav.links" locked {...sectionProps("links")} />
              <Block
                id="footer.nav.public"
                locked
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
            <Block id="footer.copy" locked />
            <Block id="footer.principles" locked />
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
