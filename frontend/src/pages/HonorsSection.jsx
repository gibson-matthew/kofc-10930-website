import { useEffect, useRef, useState } from "react";
import { createHonor, deleteHonor, fetchHonors, imageFileError, updateHonor } from "../api";
import CroppedPhoto from "../components/CroppedPhoto";
import { Portrait } from "../components/Marks";
import PhotoEditor from "../components/PhotoEditor";
import { useContent } from "../content/ContentContext";
import { clampCrop } from "../crop";
import { HONOR_FALLBACK, HONOR_GROUPS, MONTHS, collapse } from "../content/records";

const VISIBLE_HONORS = 2;
const MONTH_CATEGORIES = new Set(["knight_month", "family_month"]);
const YEAR_CATEGORIES = new Set(["knight_year", "family_year"]);

function honorProblem(category, fields) {
  const name = collapse(fields.name);
  if (!name) return "Name is required.";
  if (name.length > 80) return "Name is too long.";
  const note = collapse(fields.note);
  if (note.length > 280) return "Note is too long.";
  if (MONTH_CATEGORIES.has(category)) {
    const month = Number(fields.month);
    if (!month || month < 1 || month > 12) return "Choose a month.";
    if (!/^\d{4}$/.test(String(fields.year || "").trim())) return "Enter a year between 1900 and 2100.";
    const year = Number(fields.year);
    if (year < 1900 || year > 2100) return "Enter a year between 1900 and 2100.";
  } else if (YEAR_CATEGORIES.has(category)) {
    if (!/^\d{4}$/.test(String(fields.year || "").trim())) return "Enter a year between 1900 and 2100.";
    const year = Number(fields.year);
    if (year < 1900 || year > 2100) return "Enter a year between 1900 and 2100.";
  } else {
    const period = collapse(fields.period);
    if (!/^(\d{4})(?:[–-]\d{2})?$/.test(period)) return "Enter a year, such as 2024 or 2024–25.";
    const year = Number(period.slice(0, 4));
    if (year < 1900 || year > 2100) return "Enter a year between 1900 and 2100.";
  }
  return "";
}

function fieldsFromHonor(honor) {
  const fields = { name: honor?.name || "", note: honor?.note || "", year: "", month: "", period: "" };
  const period = honor?.period || "";
  if (MONTH_CATEGORIES.has(honor?.category)) {
    const match = /^([A-Za-z]+)\s+(\d{4})$/.exec(period);
    if (match) {
      const index = MONTHS.findIndex((name) => name.toLowerCase() === match[1].toLowerCase());
      if (index >= 0) fields.month = String(index + 1);
      fields.year = match[2];
    }
  } else if (YEAR_CATEGORIES.has(honor?.category)) {
    if (/^\d{4}$/.test(period)) fields.year = period;
  } else {
    fields.period = period;
  }
  return fields;
}

function honorCrop(honor) {
  return clampCrop(honor?.crop_x, honor?.crop_y, honor?.crop_scale ?? 1);
}

function honorSearchText(value) {
  return collapse(value).toLowerCase().replace(/[\u2013\u2014-]/g, "-");
}

function HonorPhoto({ src, crop }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [src]);
  if (src && !failed) {
    return <CroppedPhoto className="portrait" src={src} crop={crop} onError={() => setFailed(true)} />;
  }
  return <Portrait />;
}

function HonorForm({ category, initial, pending, onSave, onCancel, onError }) {
  const [fields, setFields] = useState(() => fieldsFromHonor(initial ? { ...initial, category } : { category }));
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [clearPhoto, setClearPhoto] = useState(false);
  const [crop, setCrop] = useState(() => honorCrop(initial));
  const previewRef = useRef("");

  useEffect(() => {
    return () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  function setField(key, value) {
    setFields((current) => ({ ...current, [key]: value }));
  }

  function onFile(event) {
    const chosen = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!chosen) return;
    const problem = imageFileError(chosen);
    if (problem) {
      onError(problem);
      return;
    }
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const url = URL.createObjectURL(chosen);
    previewRef.current = url;
    setFile(chosen);
    setPreview(url);
    setClearPhoto(false);
    setCrop({ x: 0, y: 0, scale: 1 });
    onError("");
  }

  function clearChosenFile() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = "";
    setFile(null);
    setPreview("");
  }

  const shownPhoto = preview || (!clearPhoto && initial?.photo_url) || "";

  function onRemovePhoto() {
    clearChosenFile();
    if (initial?.photo_url) setClearPhoto(true);
    setCrop({ x: 0, y: 0, scale: 1 });
  }

  function submit(event) {
    event.preventDefault();
    if (pending) return;
    const problem = honorProblem(category, fields);
    if (problem) {
      onError(problem);
      return;
    }
    onSave(
      {
        category,
        name: collapse(fields.name),
        note: collapse(fields.note),
        year: fields.year,
        month: fields.month,
        period: collapse(fields.period),
        clear_photo: clearPhoto && !file,
        crop,
      },
      file,
    );
  }

  return (
    <div className="honor-form">
      <form onSubmit={submit}>
        <PhotoEditor
          key={shownPhoto || "empty"}
          src={shownPhoto}
          initial={crop}
          pending={pending}
          embedded
          onSwap={onFile}
          onChange={setCrop}
          onRemove={shownPhoto ? onRemovePhoto : undefined}
        />
        <label className="signin-field">
          <span>Name</span>
          <input
            type="text"
            maxLength={80}
            value={fields.name}
            disabled={pending}
            onChange={(event) => setField("name", event.target.value)}
          />
        </label>
        {MONTH_CATEGORIES.has(category) ? (
          <>
            <label className="signin-field">
              <span>Month</span>
              <select value={fields.month} disabled={pending} onChange={(event) => setField("month", event.target.value)}>
                <option value="">Choose a month</option>
                {MONTHS.map((label, index) => (
                  <option key={label} value={String(index + 1)}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="signin-field">
              <span>Year</span>
              <input
                type="text"
                inputMode="numeric"
                maxLength={4}
                value={fields.year}
                disabled={pending}
                onChange={(event) => setField("year", event.target.value)}
              />
            </label>
          </>
        ) : null}
        {YEAR_CATEGORIES.has(category) ? (
          <label className="signin-field">
            <span>Year</span>
            <input
              type="text"
              inputMode="numeric"
              maxLength={4}
              value={fields.year}
              disabled={pending}
              onChange={(event) => setField("year", event.target.value)}
            />
          </label>
        ) : null}
        {category === "past_gk" ? (
          <label className="signin-field">
            <span>Year</span>
            <input
              type="text"
              maxLength={12}
              value={fields.period}
              disabled={pending}
              onChange={(event) => setField("period", event.target.value)}
            />
            <p className="settings-hint">2024 or 2024–25</p>
          </label>
        ) : null}
        <label className="signin-field">
          <span>Note</span>
          <input
            type="text"
            maxLength={280}
            value={fields.note}
            disabled={pending}
            onChange={(event) => setField("note", event.target.value)}
          />
        </label>
        <div className="signin-actions recog-actions">
          <button type="submit" className="btn" disabled={pending}>
            Save entry
          </button>
          <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

export default function HonorsSection() {
  const { editing } = useContent();
  const [honors, setHonors] = useState([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [editor, setEditor] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [queries, setQueries] = useState({});
  const canManage = Boolean(editing) && !fallback;

  useEffect(() => {
    let cancel = false;
    fetchHonors()
      .then((rows) => {
        if (cancel) return;
        setHonors(Array.isArray(rows) ? rows : []);
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setHonors(HONOR_FALLBACK);
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!editing) {
      setEditor(null);
      setConfirmId(null);
    }
  }, [editing]);

  async function reload() {
    const rows = await fetchHonors();
    setHonors(Array.isArray(rows) ? rows : []);
    setFallback(false);
  }

  async function onSave(fields, file, id) {
    setPending(true);
    setError("");
    try {
      if (id) await updateHonor(id, fields, file);
      else await createHonor(fields, file);
      setEditor(null);
      try {
        await reload();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Saved, but the list could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the past honor.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove(id) {
    setPending(true);
    setError("");
    try {
      await deleteHonor(id);
      setConfirmId(null);
      setHonors((current) => current.filter((item) => item.id !== id));
      try {
        await reload();
      } catch {
        /* The removed entry is already hidden. */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the past honor.");
    } finally {
      setPending(false);
    }
  }

  function toggleGroup(category) {
    const next = !expanded[category];
    setExpanded((current) => ({ ...current, [category]: next }));
    if (!next) setQueries((current) => ({ ...current, [category]: "" }));
  }

  function renderEntry(honor, category) {
    if (editor?.mode === "edit" && editor.id === honor.id) {
      return (
        <HonorForm
          key={honor.id}
          category={category}
          initial={honor}
          pending={pending}
          onError={setError}
          onCancel={() => setEditor(null)}
          onSave={(fields, file) => onSave(fields, file, honor.id)}
        />
      );
    }
    const confirming = confirmId === honor.id;
    return (
      <div className="honor-entry" key={honor.id}>
        <HonorPhoto src={honor.photo_url} crop={honor} />
        <div>
          <div className="when">{honor.period}</div>
          <h3>{honor.name}</h3>
          {honor.note ? <p>{honor.note}</p> : null}
          {canManage ? (
            confirming ? (
              <div className="signin-actions recog-actions">
                <button type="button" className="btn" disabled={pending} onClick={() => onRemove(honor.id)}>
                  Remove
                </button>
                <button type="button" className="btn btn-quiet" disabled={pending} onClick={() => setConfirmId(null)}>
                  Keep
                </button>
              </div>
            ) : (
              <div className="signin-actions recog-actions">
                <button
                  type="button"
                  className="btn btn-quiet"
                  disabled={pending}
                  onClick={() => {
                    setError("");
                    setConfirmId(null);
                    setEditor({ mode: "edit", category, id: honor.id });
                  }}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn-quiet"
                  disabled={pending}
                  onClick={() => {
                    setEditor(null);
                    setConfirmId(honor.id);
                  }}
                >
                  Remove
                </button>
              </div>
            )
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <section className="block" id="honors" aria-labelledby="honorsHeading">
      <div className="section-head">
        <div className="eyebrow left-only">Archive</div>
        <h2 id="honorsHeading">Past Honors</h2>
      </div>
      {fallback ? (
        <p className="settings-hint">Showing the example list while the council records are unavailable.</p>
      ) : null}
      {error ? (
        <p className="signin-error" role="alert">
          {error}
        </p>
      ) : null}
      {!loaded ? <p className="settings-hint">Loading…</p> : null}
      <div className="schedule honor-board">
      {HONOR_GROUPS.map(([category, label], index) => {
        const items = honors.filter((item) => item.category === category);
        const canExpand = items.length > VISIBLE_HONORS;
        const open = canExpand && Boolean(expanded[category]);
        const needle = honorSearchText(queries[category] || "");
        let shown = open ? items : items.slice(0, VISIBLE_HONORS);
        if (open && needle) {
          shown = items.filter((honor) =>
            honorSearchText(`${honor.name || ""} ${honor.period || ""} ${honor.note || ""}`).includes(needle),
          );
        }
        if (editor?.mode === "edit" && editor.category === category && !shown.some((item) => item.id === editor.id)) {
          const editingItem = items.find((item) => item.id === editor.id);
          if (editingItem) shown = [...shown, editingItem];
        }
        const adding = editor?.mode === "add" && editor.category === category;
        const wide = index === HONOR_GROUPS.length - 1 && HONOR_GROUPS.length % 2 === 1;
        const noMatches = open && needle.length > 0 && shown.length === 0;
        return (
          <article className={wide ? "sched wide honor-group" : "sched honor-group"} key={category}>
            <h3>{label}</h3>
            {canManage && !adding ? (
              <div className="signin-actions recog-actions">
                <button
                  type="button"
                  className="btn"
                  disabled={pending}
                  onClick={() => {
                    setError("");
                    setConfirmId(null);
                    setEditor({ mode: "add", category });
                  }}
                >
                  Add entry
                </button>
              </div>
            ) : null}
            {adding ? (
              <HonorForm
                category={category}
                pending={pending}
                onError={setError}
                onCancel={() => setEditor(null)}
                onSave={(fields, file) => onSave(fields, file)}
              />
            ) : null}
            {loaded && items.length === 0 && !adding ? <p className="settings-hint">None recorded yet.</p> : null}
            {loaded && open ? (
              <button type="button" className="more is-top" aria-expanded="true" onClick={() => toggleGroup(category)}>
                View less
              </button>
            ) : null}
            {open ? (
              <label className="signin-field honor-search">
                <span>Search</span>
                <input
                  type="search"
                  value={queries[category] || ""}
                  placeholder="Name, year, or note"
                  autoComplete="off"
                  onChange={(event) =>
                    setQueries((current) => ({ ...current, [category]: event.target.value }))
                  }
                />
              </label>
            ) : null}
            {open ? (
              <div className="honor-scroll">
                {noMatches ? (
                  <p className="settings-hint" role="status">
                    No matches.
                  </p>
                ) : (
                  <div className="honor-list">{shown.map((honor) => renderEntry(honor, category))}</div>
                )}
              </div>
            ) : (
              <div className="honor-list">{shown.map((honor) => renderEntry(honor, category))}</div>
            )}
            {loaded && canExpand ? (
              <button
                type="button"
                className="more"
                aria-expanded={open ? "true" : "false"}
                onClick={() => toggleGroup(category)}
              >
                {open ? "View less" : "View more"}
              </button>
            ) : null}
          </article>
        );
      })}
      </div>
    </section>
  );
}
