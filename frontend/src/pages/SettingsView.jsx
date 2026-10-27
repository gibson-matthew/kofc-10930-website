import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import CroppedPhoto from "../components/CroppedPhoto";
import { PortraitSm } from "../components/Marks";
import PhotoEditor, { PHOTO_ACCEPT } from "../components/PhotoEditor";
import { daysInMonth } from "../birthdays";
import { MONTHS } from "../content/records";
import {
  assignMediaSlot,
  assignPastGrandKnight,
  createMember,
  deleteMedia,
  deleteMyPhoto,
  fetchMedia,
  fetchMembers,
  fetchMyEmail,
  mediaUrl,
  imageFileError,
  replaceMedia,
  setMemberAdmin,
  saveMyEmail,
  setMemberBirthday,
  setMemberHonorary,
  setMemberWebmaster,
  updateMyCrop,
  uploadMedia,
  uploadMyPhoto,
} from "../api";
import { OFFICER_TITLES, memberLabel } from "../titles";
import { navigate } from "../router";
import ActivityLog from "./ActivityLog";
import EmailCompose from "./EmailCompose";
import EmailRouting from "./EmailRouting";

const MEDIA_SECTIONS = [
  {
    id: "logo",
    label: "Logo",
    slots: [["logo", "Logo"]],
  },
  {
    id: "carousel",
    label: "Carousel",
    slots: [
      ["carousel.1", "Carousel photo 1"],
      ["carousel.2", "Carousel photo 2"],
      ["carousel.3", "Carousel photo 3"],
      ["carousel.4", "Carousel photo 4"],
    ],
  },
  {
    id: "about",
    label: "About",
    slots: [
      ["recog.0", "Family of the Month"],
      ["recog.1", "Knight of the Month"],
      ["recog.2", "Family of the Year"],
      ["recog.3", "Knight of the Year"],
    ],
  },
];

const EMPTY_MEMBER = {
  memberid: "",
  password: "",
  display_name: "",
  title: "",
  birth_month: "",
  birth_day: "",
  pgk_period: "",
  pgk_note: "",
};

const PGK_PERIOD = /^(\d{4})(?:[-\u2013](\d{2}))?$/;

const DIRECTORY_PREVIEW = 3;
const MEDIA_PREVIEW = 2;

function collapse(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function searchNeedle(value) {
  return collapse(value).toLowerCase().replace(/[\u2013\u2014-]/g, "-");
}

function memberMatches(member, needle) {
  if (!needle) return true;
  const haystack = searchNeedle(`${member.display_name || ""} ${member.memberid || ""} ${titleText(member.title)}`);
  return haystack.includes(needle);
}

function accessLabel(member) {
  if (member.is_webmaster) return "Webmaster";
  if (member.is_admin) return "Admin";
  return "Member";
}

function titleText(title) {
  if (!title) return "No title";
  const found = OFFICER_TITLES.find(([, abbrev]) => abbrev === title);
  return found ? `${found[1]} — ${found[0]}` : title;
}

function birthdayProblem(month, day) {
  const monthBlank = month === "" || month == null;
  const dayBlank = day === "" || day == null;
  if (monthBlank && dayBlank) return "";
  const monthN = Number(month);
  const dayN = Number(day);
  if (
    monthBlank ||
    dayBlank ||
    !Number.isInteger(monthN) ||
    monthN < 1 ||
    monthN > 12 ||
    !Number.isInteger(dayN) ||
    dayN < 1 ||
    dayN > daysInMonth(monthN)
  ) {
    return "Choose a valid birthday.";
  }
  return "";
}

function pgkPeriodProblem(period) {
  const value = collapse(period);
  if (!value) return "Enter the year this Past Grand Knight served.";
  const match = PGK_PERIOD.exec(value);
  if (!match) return "Enter a year, such as 2024 or 2024–25.";
  const year = Number(match[1]);
  if (year < 1900 || year > 2100) return "Enter a year between 1900 and 2100.";
  return "";
}

function memberProblem(form) {
  const memberid = String(form.memberid || "").trim();
  if (!/^\d{1,32}$/.test(memberid)) return "Membership ID must contain only digits.";
  const password = String(form.password || "");
  const bytes = new TextEncoder().encode(password).length;
  if (password.length < 8 || bytes > 72) return "Password must be 8 to 72 characters.";
  const name = collapse(form.display_name);
  if (!name) return "Enter the member's name.";
  if (name.length > 80) return "Name is too long.";
  if (form.title && !OFFICER_TITLES.some(([, abbrev]) => abbrev === form.title)) {
    return "Choose a title from the list.";
  }
  if (form.title === "PGK") {
    const period = pgkPeriodProblem(form.pgk_period);
    if (period) return period;
    if (collapse(form.pgk_note).length > 280) return "Description is too long.";
  }
  const birthday = birthdayProblem(form.birth_month, form.birth_day);
  if (birthday) return birthday;
  return "";
}

function BirthdayFields({ month, day, disabled, onMonth, onDay, compact = false }) {
  const max = month ? daysInMonth(Number(month)) : 0;
  const fieldClass = compact ? "member-birth-field" : "signin-field";
  return (
    <div className={compact ? "member-birthday-fields" : "birthday-inputs"}>
      <label className={fieldClass}>
        <span>{compact ? "Month" : "Birth month"}</span>
        <select value={month || ""} disabled={disabled} onChange={(event) => onMonth(event.target.value)}>
          <option value="">Month</option>
          {MONTHS.map((label, index) => (
            <option key={label} value={String(index + 1)}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className={fieldClass}>
        <span>{compact ? "Day" : "Birth day"}</span>
        <select value={day || ""} disabled={disabled || !month} onChange={(event) => onDay(event.target.value)}>
          <option value="">Day</option>
          {Array.from({ length: max }, (_, index) => (
            <option key={index + 1} value={String(index + 1)}>
              {index + 1}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function BirthdayEditor({ member, onSave }) {
  const [month, setMonth] = useState(member.birth_month ? String(member.birth_month) : "");
  const [day, setDay] = useState(member.birth_day ? String(member.birth_day) : "");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setMonth(member.birth_month ? String(member.birth_month) : "");
    setDay(member.birth_day ? String(member.birth_day) : "");
  }, [member.memberid, member.birth_month, member.birth_day]);

  function changeMonth(value) {
    setMonth(value);
    setDay((current) => {
      if (!value) return "";
      if (current && Number(current) > daysInMonth(Number(value))) return "";
      return current;
    });
  }

  async function save() {
    const problem = birthdayProblem(month, day);
    if (problem) {
      setError(problem);
      setNotice("");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await onSave(member.memberid, {
        birth_month: month ? Number(month) : null,
        birth_day: day ? Number(day) : null,
      });
      setNotice("Birthday saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the birthday.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="member-birthday">
      <BirthdayFields month={month} day={day} disabled={busy} onMonth={changeMonth} onDay={setDay} compact />
      <button type="button" className="btn btn-quiet" onClick={save} disabled={busy}>
        Save birthday
      </button>
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
    </div>
  );
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

function PersonalEmail({ initial, onSaved }) {
  const [email, setEmail] = useState(initial || "");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setEmail(initial || "");
  }, [initial]);

  async function save() {
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const saved = await saveMyEmail(email);
      const next = saved.email || "";
      setEmail(next);
      setNotice("Saved.");
      if (onSaved) onSaved(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the personal email.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="card settings-card" id="personal-email">
      <h3>Personal email</h3>
      <p>Mail for your role address is forwarded to this inbox.</p>
      <label className="signin-field">
        <span>Personal email</span>
        <input
          type="email"
          value={email}
          maxLength={90}
          autoComplete="email"
          disabled={busy}
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>
      <div className="signin-actions">
        <button type="button" className="btn btn-quiet" disabled={busy} onClick={save}>
          Save email
        </button>
      </div>
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

export default function SettingsView() {
  const { user, refresh } = useAuth();
  const webmaster = Boolean(user?.is_webmaster);
  const cloudflare = Boolean(user?.is_cloudflare);
  const admin = Boolean(user?.is_admin || webmaster);
  const [members, setMembers] = useState([]);
  const [images, setImages] = useState([]);
  const [membersOpen, setMembersOpen] = useState(false);
  const [membersQuery, setMembersQuery] = useState("");
  const [adminsOpen, setAdminsOpen] = useState(false);
  const [adminsQuery, setAdminsQuery] = useState("");
  const [mediaOpen, setMediaOpen] = useState(false);
  const [mediaQuery, setMediaQuery] = useState("");
  const [mediaSection, setMediaSection] = useState("");
  const [pgkForm, setPgkForm] = useState({ memberid: "", period: "", note: "" });
  const [pgkNotice, setPgkNotice] = useState("");
  const [pgkError, setPgkError] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState({});
  const [pending, setPending] = useState(false);
  const [loadingAdmin, setLoadingAdmin] = useState(admin);
  const [editor, setEditor] = useState(null);
  const [memberForm, setMemberForm] = useState(EMPTY_MEMBER);
  const [memberNotice, setMemberNotice] = useState("");
  const [memberError, setMemberError] = useState("");
  const [ownEmail, setOwnEmail] = useState(null);
  const [ownSaved, setOwnSaved] = useState(null);
  const editorRef = useRef(null);
  editorRef.current = editor;

  useEffect(() => {
    return () => {
      const current = editorRef.current;
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
    };
  }, []);

  useEffect(() => {
    let cancel = false;
    fetchMyEmail()
      .then((row) => {
        if (cancel) return;
        setOwnEmail({ email: row.email || "", editable: Boolean(row.editable) });
      })
      .catch(() => {
        if (!cancel) setOwnEmail({ email: "", editable: false });
      });
    return () => {
      cancel = true;
    };
  }, [user?.memberid]);

  useEffect(() => {
    if (!admin) return undefined;
    let cancel = false;
    setLoadingAdmin(true);
    Promise.all([fetchMembers(), fetchMedia()])
      .then(([people, library]) => {
        if (cancel) return;
        setMembers(people);
        setImages(library);
        setLoadingAdmin(false);
      })
      .catch((err) => {
        if (cancel) return;
        setError(err instanceof Error ? err.message : "Could not load settings.");
        setLoadingAdmin(false);
      });
    return () => {
      cancel = true;
    };
  }, [admin]);

  function writeFlash(scope, message, problem) {
    setFlash((current) => ({ ...current, [scope]: { notice: message || "", error: problem || "" } }));
  }

  function Flash({ scope }) {
    const item = flash[scope];
    if (!item?.error && !item?.notice) return null;
    if (item.error) {
      return (
        <p className="signin-error" role="alert">
          {item.error}
        </p>
      );
    }
    return (
      <p className="settings-notice is-confirm" role="status">
        {item.notice}
      </p>
    );
  }

  async function run(scope, action, success) {
    setPending(true);
    writeFlash(scope, "", "");
    try {
      await action();
      if (success) writeFlash(scope, success, "");
    } catch (err) {
      writeFlash(scope, "", err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  function closeEditor() {
    setEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return null;
    });
  }

  function openEditor() {
    setError("");
    writeFlash("profile", "", "");
    setEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      if (user?.photo_url) {
        return {
          src: user.photo_url,
          file: null,
          ownedUrl: false,
          crop: { x: user.crop_x || 0, y: user.crop_y || 0, scale: user.crop_scale || 1 },
        };
      }
      return { src: "", file: null, ownedUrl: false, crop: { x: 0, y: 0, scale: 1 } };
    });
  }

  function onSwap(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) return;
    const problem = imageFileError(file);
    if (problem) {
      writeFlash("profile", "", problem);
      return;
    }
    const url = URL.createObjectURL(file);
    writeFlash("profile", "", "");
    setEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return { src: url, file, ownedUrl: true, crop: { x: 0, y: 0, scale: 1 } };
    });
  }

  function rememberMember(updated) {
    if (!updated) return;
    setMembers((current) => current.map((item) => (item.memberid === updated.memberid ? updated : item)));
  }

  function onSavePhoto(crop) {
    const file = editor?.file || null;
    if (!file && !editor?.src) return;
    run("profile", async () => {
      const updated = file ? await uploadMyPhoto(file, crop) : await updateMyCrop(crop);
      await refresh();
      rememberMember(updated);
      closeEditor();
    }, "Profile photo saved.");
  }

  function showEmptyEditor() {
    setEditor((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return { src: "", file: null, ownedUrl: false, crop: { x: 0, y: 0, scale: 1 } };
    });
  }

  function onRemovePhoto() {
    closeEditor();
    run("profile", async () => {
      const updated = await deleteMyPhoto();
      await refresh();
      rememberMember(updated);
    }, "Profile photo removed.");
  }

  function onRemoveInEditor() {
    if (!user?.photo_url) {
      showEmptyEditor();
      return;
    }
    run("profile", async () => {
      const updated = await deleteMyPhoto();
      await refresh();
      rememberMember(updated);
      showEmptyEditor();
    }, "Profile photo removed.");
  }

  async function reloadMedia() {
    setImages(await fetchMedia());
  }

  function chooseMediaSection(id) {
    setMediaSection(id);
    setMediaOpen(false);
    setMediaQuery("");
  }

  function onAddToSlot(slot, event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    const problem = imageFileError(file);
    if (problem) {
      writeFlash("media", "", problem);
      return;
    }
    run("media", async () => {
      const image = await uploadMedia(file);
      try {
        await assignMediaSlot(image.id, slot);
      } catch (err) {
        try {
          await deleteMedia(image.id);
        } catch {
          /* The unused upload stays out of the section list. */
        }
        throw err;
      }
      await reloadMedia();
    }, "Image uploaded.");
  }

  function onReplace(image, event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    const problem = imageFileError(file);
    if (problem) {
      writeFlash("media", "", problem);
      return;
    }
    run("media", async () => {
      await replaceMedia(image.id, file);
      await reloadMedia();
    }, "Image replaced.");
  }

  function onRemove(image) {
    run("media", async () => {
      await deleteMedia(image.id);
      await reloadMedia();
    }, "Image removed.");
  }

  async function onCreateMember(event) {
    event.preventDefault();
    const problem = memberProblem(memberForm);
    if (problem) {
      setMemberError(problem);
      setMemberNotice("");
      return;
    }
    const memberid = memberForm.memberid.trim();
    const displayName = collapse(memberForm.display_name);
    const payload = {
      memberid,
      password: memberForm.password,
      display_name: displayName,
      title: memberForm.title || null,
      birth_month: memberForm.birth_month ? Number(memberForm.birth_month) : null,
      birth_day: memberForm.birth_day ? Number(memberForm.birth_day) : null,
      pgk_period: memberForm.title === "PGK" ? collapse(memberForm.pgk_period) : "",
      pgk_note: memberForm.title === "PGK" ? collapse(memberForm.pgk_note) : "",
    };
    setPending(true);
    setError("");
    setMemberError("");
    setMemberNotice("");
    try {
      const created = await createMember(payload);
      setMemberForm(EMPTY_MEMBER);
      setMemberNotice("Member created. They can sign in with that membership ID.");
      setMembers((current) => {
        const next = current
          .filter((item) => item.memberid !== created.memberid)
          .map((item) => (created.title === "PGK" && item.title === "PGK" ? { ...item, title: null } : item));
        next.push(created);
        next.sort(
          (a, b) =>
            String(a.display_name || "").localeCompare(String(b.display_name || "")) ||
            String(a.memberid).localeCompare(String(b.memberid)),
        );
        return next;
      });
      try {
        setMembers(await fetchMembers());
        await refresh();
      } catch {
        /* The new member is already in the directory. */
      }
    } catch (err) {
      setMemberError(err instanceof Error ? err.message : "Could not create the member.");
    } finally {
      setPending(false);
    }
  }

  async function onBirthday(memberid, payload) {
    const updated = await setMemberBirthday(memberid, payload);
    setMembers((current) => current.map((item) => (item.memberid === updated.memberid ? updated : item)));
  }

  function onAdmin(member, next) {
    run("admin", async () => {
      const updated = await setMemberAdmin(member.memberid, next);
      setMembers((current) => current.map((item) => (item.memberid === updated.memberid ? updated : item)));
      if (updated.memberid === user?.memberid) await refresh();
    }, next ? "Admin access granted." : "Admin access removed.");
  }

  function onWebmaster(member, next) {
    run("admin", async () => {
      const updated = await setMemberWebmaster(member.memberid, next);
      setMembers((current) => current.map((item) => (item.memberid === updated.memberid ? updated : item)));
      if (updated.memberid === user?.memberid) await refresh();
    }, next ? "Webmaster access granted." : "Webmaster access removed.");
  }

  function onHonorary(member, next) {
    run("members", async () => {
      const updated = await setMemberHonorary(member.memberid, next);
      setMembers((current) =>
        current.map((item) =>
          item.memberid === updated.memberid ? { ...item, honorary_life: Boolean(updated.honorary_life) } : item,
        ),
      );
    }, next ? "Honorary Life Member set." : "Honorary Life Member cleared.");
  }

  async function onAssignPgk(event) {
    event.preventDefault();
    const periodProblem = pgkPeriodProblem(pgkForm.period);
    if (!pgkForm.memberid) {
      setPgkError("Choose a member from the list.");
      setPgkNotice("");
      return;
    }
    if (periodProblem) {
      setPgkError(periodProblem);
      setPgkNotice("");
      return;
    }
    if (collapse(pgkForm.note).length > 280) {
      setPgkError("Description is too long.");
      setPgkNotice("");
      return;
    }
    const memberid = pgkForm.memberid;
    setPending(true);
    setPgkError("");
    setPgkNotice("");
    try {
      const updated = await assignPastGrandKnight(memberid, {
        period: collapse(pgkForm.period),
        note: collapse(pgkForm.note),
      });
      setMembers((current) =>
        current.map((item) => {
          if (item.memberid === updated.memberid) return { ...item, ...updated };
          if (item.title === "PGK") return { ...item, title: null };
          return item;
        }),
      );
      setPgkForm({ memberid: "", period: "", note: "" });
      setPgkNotice("Past Grand Knight saved.");
      if (updated.memberid === user?.memberid) await refresh();
    } catch (err) {
      setPgkError(err instanceof Error ? err.message : "Could not save Past Grand Knight.");
    } finally {
      setPending(false);
    }
  }

  const adminCount = members.filter((member) => member.is_admin).length;
  const webmasterCount = members.filter((member) => member.is_webmaster).length;
  const memberNeedle = membersOpen ? searchNeedle(membersQuery) : "";
  const shownMembers = membersOpen
    ? members.filter((member) => memberMatches(member, memberNeedle))
    : members.slice(0, DIRECTORY_PREVIEW);
  const adminNeedle = adminsOpen ? searchNeedle(adminsQuery) : "";
  const shownAdmins = adminsOpen
    ? members.filter((member) => memberMatches(member, adminNeedle))
    : members.slice(0, DIRECTORY_PREVIEW);
  const chosenMedia = MEDIA_SECTIONS.find((section) => section.id === mediaSection) || null;
  const mediaSlots = chosenMedia
    ? chosenMedia.slots.map(([value, label]) => ({
        value,
        label,
        image: images.find((image) => image.slot === value) || null,
      }))
    : [];
  const mediaNeedle = mediaOpen ? searchNeedle(mediaQuery) : "";
  const filteredMedia = mediaNeedle
    ? mediaSlots.filter((slot) =>
        searchNeedle(`${slot.label} ${slot.image?.original_name || ""}`).includes(mediaNeedle),
      )
    : mediaSlots;
  const shownMedia = mediaOpen ? filteredMedia : filteredMedia.slice(0, MEDIA_PREVIEW);

  function toggleMembers() {
    if (membersOpen) setMembersQuery("");
    setMembersOpen((open) => !open);
  }

  function toggleAdmins() {
    if (adminsOpen) setAdminsQuery("");
    setAdminsOpen((open) => !open);
  }

  function toggleMedia() {
    if (mediaOpen) setMediaQuery("");
    setMediaOpen((open) => !open);
  }

  return (
    <div className="container settings-view">
      <section aria-labelledby="settingsHeading">
        <div className="section-head">
          <div className="eyebrow left-only">Account</div>
          <h2 id="settingsHeading">Settings</h2>
          <p>{memberLabel(user)}</p>
          {admin || cloudflare ? (
            <nav className="settings-jump" aria-label="Settings sections">
              <a href="#profile">Profile photo</a>
              {admin ? (
                <>
                  <a href="#new-member">New member</a>
                  <a href="#members">Members</a>
                  <a href="#admin-access">Admin access</a>
                  {cloudflare ? <a href="#email-routing">Email routing</a> : null}
                  {cloudflare ? <a href="#council-email">Email</a> : null}
                  <a href="#media">Media</a>
                </>
              ) : null}
              {cloudflare && !admin ? <a href="#email-routing">Email routing</a> : null}
              {cloudflare && !admin ? <a href="#council-email">Email</a> : null}
              {webmaster ? <a href="#logs">Logs & activity</a> : null}
            </nav>
          ) : null}
        </div>
        {error ? (
          <p className="signin-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="settings-stack">
          <article className="card settings-card" id="profile">
            <h3>Profile photo</h3>
            <p>One photo. It is public and appears wherever you are shown.</p>
            <Flash scope="profile" />
            {editor ? (
              <PhotoEditor
                key={editor.src || "empty"}
                src={editor.src}
                initial={editor.crop}
                pending={pending}
                onSave={onSavePhoto}
                onCancel={closeEditor}
                onSwap={onSwap}
                onRemove={editor.src || user?.photo_url ? onRemoveInEditor : undefined}
              />
            ) : (
              <div className="settings-photo-row">
                <Photo user={user} className="settings-photo" />
                <div className="signin-actions">
                  <button type="button" className="btn" onClick={openEditor} disabled={pending}>
                    Change photo
                  </button>
                  {user?.photo_url ? (
                    <button type="button" className="btn btn-quiet" onClick={onRemovePhoto} disabled={pending}>
                      Remove photo
                    </button>
                  ) : null}
                </div>
              </div>
            )}
          </article>
          {ownEmail?.editable ? (
            <PersonalEmail
              initial={ownEmail.email}
              onSaved={(email) => {
                setOwnEmail((current) => (current ? { ...current, email } : current));
                setOwnSaved({ memberid: user?.memberid, email, nonce: Date.now() });
              }}
            />
          ) : null}
        </div>
        <div className="signin-actions settings-back">
          <button type="button" className="btn btn-quiet" onClick={() => navigate("/member")}>
            Back to members area
          </button>
        </div>
      </section>

      {admin ? (
        <section className="block" id="members" aria-labelledby="membersHeading">
          <div className="section-head">
            <div className="eyebrow left-only">Directory</div>
            <h2 id="membersHeading">Members</h2>
            <p>Create a member, then they can sign in. Titles come from the officer list.</p>
          </div>
          <article className="card settings-card members-create" id="new-member">
            <h3>New member</h3>
            {memberNotice ? (
              <p className="settings-notice is-confirm" role="status">
                {memberNotice}
              </p>
            ) : null}
            {memberError ? (
              <p className="signin-error" role="alert">
                {memberError}
              </p>
            ) : null}
            <form autoComplete="off" onSubmit={onCreateMember}>
              <label className="signin-field">
                <span>Membership ID</span>
                <input
                  type="text"
                  name="new-memberid"
                  inputMode="numeric"
                  autoComplete="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  maxLength={32}
                  value={memberForm.memberid}
                  disabled={pending}
                  onChange={(event) => setMemberForm((current) => ({ ...current, memberid: event.target.value }))}
                />
                <p className="settings-hint">Digits only. They will use this ID to sign in.</p>
              </label>
              <label className="signin-field">
                <span>Password</span>
                <input
                  type="password"
                  name="new-password"
                  autoComplete="new-password"
                  maxLength={128}
                  value={memberForm.password}
                  disabled={pending}
                  onChange={(event) => setMemberForm((current) => ({ ...current, password: event.target.value }))}
                />
                <p className="settings-hint">At least 8 characters.</p>
              </label>
              <label className="signin-field">
                <span>Name</span>
                <input
                  type="text"
                  name="new-name"
                  autoComplete="off"
                  maxLength={80}
                  value={memberForm.display_name}
                  disabled={pending}
                  onChange={(event) => setMemberForm((current) => ({ ...current, display_name: event.target.value }))}
                />
              </label>
              <label className="signin-field">
                <span>Title</span>
                <select
                  value={memberForm.title}
                  disabled={pending}
                  onChange={(event) => setMemberForm((current) => ({ ...current, title: event.target.value }))}
                >
                  <option value="">No title</option>
                  {OFFICER_TITLES.map(([label, abbrev]) => (
                    <option key={abbrev} value={abbrev}>
                      {abbrev} — {label}
                    </option>
                  ))}
                </select>
                <p className="settings-hint">Optional. A title can belong to one member. Later changes are made with Edit on the members page.</p>
              </label>
              {memberForm.title === "PGK" ? (
                <>
                  <label className="signin-field">
                    <span>Year served</span>
                    <input
                      type="text"
                      maxLength={12}
                      value={memberForm.pgk_period}
                      disabled={pending}
                      onChange={(event) =>
                        setMemberForm((current) => ({ ...current, pgk_period: event.target.value }))
                      }
                    />
                    <p className="settings-hint">Required. 2024 or 2024–25.</p>
                  </label>
                  <label className="signin-field">
                    <span>Description</span>
                    <input
                      type="text"
                      maxLength={280}
                      value={memberForm.pgk_note}
                      disabled={pending}
                      onChange={(event) => setMemberForm((current) => ({ ...current, pgk_note: event.target.value }))}
                    />
                    <p className="settings-hint">Optional. Saved with the Past Grand Knights entry.</p>
                  </label>
                </>
              ) : null}
              <BirthdayFields
                month={memberForm.birth_month}
                day={memberForm.birth_day}
                disabled={pending}
                onMonth={(value) =>
                  setMemberForm((current) => ({
                    ...current,
                    birth_month: value,
                    birth_day:
                      !value || (current.birth_day && Number(current.birth_day) > daysInMonth(Number(value)))
                        ? ""
                        : current.birth_day,
                  }))
                }
                onDay={(value) => setMemberForm((current) => ({ ...current, birth_day: value }))}
              />
              <p className="settings-hint">Optional. Month and day only.</p>
              <div className="signin-actions">
                <button type="submit" className="btn" disabled={pending}>
                  Create member
                </button>
              </div>
            </form>
          </article>
          <article className="card settings-card members-create">
            <h3>Past Grand Knight</h3>
            <p className="settings-hint">
              Year served is required. Saving writes the Past Grand Knights entry and sets that member’s title to PGK.
            </p>
            {pgkNotice ? (
              <p className="settings-notice is-confirm" role="status">
                {pgkNotice}
              </p>
            ) : null}
            {pgkError ? (
              <p className="signin-error" role="alert">
                {pgkError}
              </p>
            ) : null}
            <form autoComplete="off" onSubmit={onAssignPgk}>
              <label className="signin-field">
                <span>Member</span>
                <select
                  value={pgkForm.memberid}
                  disabled={pending || loadingAdmin}
                  onChange={(event) => setPgkForm((current) => ({ ...current, memberid: event.target.value }))}
                >
                  <option value="">Choose a member</option>
                  {[...members]
                    .sort(
                      (a, b) =>
                        String(a.display_name || "").localeCompare(String(b.display_name || "")) ||
                        String(a.memberid).localeCompare(String(b.memberid)),
                    )
                    .map((member) => (
                      <option key={member.memberid} value={member.memberid}>
                        {member.display_name || "Member"} ({member.memberid})
                      </option>
                    ))}
                </select>
              </label>
              <label className="signin-field">
                <span>Year served</span>
                <input
                  type="text"
                  maxLength={12}
                  value={pgkForm.period}
                  disabled={pending}
                  onChange={(event) => setPgkForm((current) => ({ ...current, period: event.target.value }))}
                />
                <p className="settings-hint">2024 or 2024–25.</p>
              </label>
              <label className="signin-field">
                <span>Description</span>
                <input
                  type="text"
                  maxLength={280}
                  value={pgkForm.note}
                  disabled={pending}
                  onChange={(event) => setPgkForm((current) => ({ ...current, note: event.target.value }))}
                />
                <p className="settings-hint">Optional.</p>
              </label>
              <div className="signin-actions">
                <button type="submit" className="btn" disabled={pending || loadingAdmin}>
                  Save
                </button>
              </div>
            </form>
          </article>
          {loadingAdmin ? <p>Loading members…</p> : null}
          <Flash scope="members" />
          <ListPanel
            open={membersOpen}
            canToggle={members.length > DIRECTORY_PREVIEW}
            onToggle={toggleMembers}
            query={membersQuery}
            onQuery={setMembersQuery}
            placeholder="Name or membership ID"
            noMatches={membersOpen && memberNeedle && shownMembers.length === 0}
            gridClass="officer-grid"
          >
            {shownMembers.map((member) => (
              <article className="officer" key={member.memberid}>
                <Photo user={member} className="portrait-sm" />
                <div>
                  <div className="role">{member.memberid}</div>
                  <strong>{member.display_name || "Member"}</strong>
                  <p className="settings-hint">
                    {titleText(member.title)}
                    {" · "}
                    {accessLabel(member)}
                  </p>
                  <label className="admin-toggle">
                    <input
                      type="checkbox"
                      checked={Boolean(member.honorary_life)}
                      disabled={pending}
                      onChange={(event) => onHonorary(member, event.target.checked)}
                    />
                    Honorary Life Member
                  </label>
                  <BirthdayEditor member={member} onSave={onBirthday} />
                </div>
              </article>
            ))}
          </ListPanel>
        </section>
      ) : null}

      {admin ? (
        <section className="block" id="admin-access" aria-labelledby="adminHeading">
          <div className="section-head">
            <div className="eyebrow left-only">Webmaster</div>
            <h2 id="adminHeading">Admin access</h2>
            <p>Full edit access uses the Edit control on the members page.</p>
            {loadingAdmin ? null : (
              <p className="settings-hint">
                {adminCount === 1 ? "1 member has full edit access." : `${adminCount} members have full edit access.`}
              </p>
            )}
            {webmaster && !loadingAdmin ? (
              <p className="settings-hint">
                {webmasterCount === 1 ? "1 member is a webmaster." : `${webmasterCount} members are webmasters.`}
              </p>
            ) : null}
          </div>
          <Flash scope="admin" />
          {loadingAdmin ? <p>Loading members…</p> : null}
          <ListPanel
            open={adminsOpen}
            canToggle={members.length > DIRECTORY_PREVIEW}
            onToggle={toggleAdmins}
            query={adminsQuery}
            onQuery={setAdminsQuery}
            placeholder="Name or membership ID"
            noMatches={adminsOpen && adminNeedle && shownAdmins.length === 0}
            gridClass="officer-grid"
          >
            {shownAdmins.map((member) => {
              const lastAdmin = member.is_admin && adminCount < 2;
              const lastWebmaster = member.is_webmaster && webmasterCount < 2;
              return (
                <article className="officer" key={member.memberid}>
                  <Photo user={member} className="portrait-sm" />
                  <div>
                    <div className="role">{member.memberid}</div>
                    <strong>{memberLabel(member)}</strong>
                    <label className="admin-toggle">
                      <input
                        type="checkbox"
                        checked={Boolean(member.is_admin)}
                        disabled={pending || lastAdmin}
                        onChange={(event) => onAdmin(member, event.target.checked)}
                      />
                      Full edit access
                    </label>
                    {lastAdmin ? <p className="settings-hint">The council needs at least one admin.</p> : null}
                    {webmaster ? (
                      <label className="admin-toggle">
                        <input
                          type="checkbox"
                          checked={Boolean(member.is_webmaster)}
                          disabled={pending || lastWebmaster}
                          onChange={(event) => onWebmaster(member, event.target.checked)}
                        />
                        Webmaster
                      </label>
                    ) : null}
                    {webmaster && lastWebmaster ? (
                      <p className="settings-hint">The council needs at least one webmaster.</p>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </ListPanel>
        </section>
      ) : null}

      {cloudflare ? (
        <EmailRouting
          ownSaved={ownSaved}
          onOwnEmail={(email) => setOwnEmail((current) => (current ? { ...current, email } : current))}
        />
      ) : null}

      {cloudflare ? <EmailCompose /> : null}

      {admin ? (
        <section className="block" id="media" aria-labelledby="mediaHeading">
          <div className="section-head">
            <div className="eyebrow left-only">Library</div>
            <h2 id="mediaHeading">Media</h2>
            <p>Choose the part of the site, then add, replace, or remove its photos. JPG, PNG, or WebP. An empty slot uses the example image.</p>
          </div>
          <Flash scope="media" />
          <div className="media-sections" role="group" aria-label="Photo sections">
            {MEDIA_SECTIONS.map((section) => (
              <button
                type="button"
                key={section.id}
                className={mediaSection === section.id ? "btn" : "btn btn-quiet"}
                aria-pressed={mediaSection === section.id}
                onClick={() => chooseMediaSection(section.id)}
              >
                {section.label}
              </button>
            ))}
          </div>
          {chosenMedia ? (
          <ListPanel
            open={mediaOpen}
            canToggle={mediaSlots.length > MEDIA_PREVIEW}
            onToggle={toggleMedia}
            query={mediaQuery}
            onQuery={setMediaQuery}
            placeholder="File name or photo"
            noMatches={mediaOpen && mediaNeedle && shownMedia.length === 0}
            gridClass="media-grid"
          >
            {shownMedia.map((slot) => (
              <article className="card media-card" key={slot.value}>
                {slot.image ? <img src={mediaUrl(slot.image.url)} alt="" /> : null}
                <strong>{slot.label}</strong>
                {slot.image ? <p className="settings-hint">{slot.image.original_name}</p> : (
                  <p className="settings-hint">No photo yet.</p>
                )}
                <div className="signin-actions">
                  {slot.image ? (
                    <>
                      <label className="btn btn-quiet">
                        Replace
                        <input
                          type="file"
                          accept={PHOTO_ACCEPT}
                          hidden
                          disabled={pending}
                          onChange={(event) => onReplace(slot.image, event)}
                        />
                      </label>
                      <button
                        type="button"
                        className="btn btn-quiet"
                        disabled={pending}
                        onClick={() => onRemove(slot.image)}
                      >
                        Remove
                      </button>
                    </>
                  ) : (
                    <label className="btn">
                      Add
                      <input
                        type="file"
                        accept={PHOTO_ACCEPT}
                        hidden
                        disabled={pending}
                        onChange={(event) => onAddToSlot(slot.value, event)}
                      />
                    </label>
                  )}
                </div>
              </article>
            ))}
          </ListPanel>
          ) : (
            <p className="settings-hint">Choose a section to see its photos.</p>
          )}
        </section>
      ) : null}

      {webmaster ? (
        <section className="block" id="logs" aria-labelledby="logsHeading">
          <div className="section-head">
            <div className="eyebrow left-only">Webmaster</div>
            <h2 id="logsHeading">Logs & activity</h2>
            <p>Stored sign-in, security, content, and optional site events, plus each Accept or Decline. Read-only.</p>
          </div>
          <ActivityLog members={members} />
        </section>
      ) : null}
    </div>
  );
}
