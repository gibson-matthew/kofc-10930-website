import { useEffect, useRef, useState } from "react";
import { createHonor, deleteHonor, fetchHonors, imageFileError, updateHonor } from "../api";
import { Portrait } from "../components/Marks";
import { useContent } from "../content/ContentContext";
import { HONOR_FALLBACK, HONOR_GROUPS, MONTHS, collapse } from "../content/records";

const ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";
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

function HonorPhoto({ src }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(false);
  }, [src]);
  if (src && !failed) {
    return <img className="portrait" src={src} alt="" onError={() => setFailed(true)} />;
  }
  return <Portrait />;
}

function HonorForm({ category, initial, pending, onSave, onCancel, onError }) {
  const [fields, setFields] = useState(() => fieldsFromHonor(initial ? { ...initial, category } : { category }));
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [clearPhoto, setClearPhoto] = useState(false);
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
    onError("");
  }

  function clearChosenFile() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = "";
    setFile(null);
    setPreview("");
  }

  const shownPhoto = preview || (!clearPhoto && initial?.photo_url) || "";

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
      },
      file,
    );
  }

  return (
    <article className="card honor-form">
      <form onSubmit={submit}>
        <div className="settings-photo-row">
          <HonorPhoto src={shownPhoto} />
          <div className="signin-actions recog-actions">
            <label className="btn btn-quiet">
              {shownPhoto ? "Replace photo" : "Add photo"}
              <input type="file" accept={ACCEPT} hidden disabled={pending} onChange={onFile} />
            </label>
            {file ? (
              <button type="button" className="btn btn-quiet" disabled={pending} onClick={clearChosenFile}>
                Undo image
              </button>
            ) : null}
            {!file && initial?.photo_url && !clearPhoto ? (
              <button type="button" className="btn btn-quiet" disabled={pending} onClick={() => setClearPhoto(true)}>
                Remove photo
              </button>
            ) : null}
            {!file && clearPhoto && initial?.photo_url ? (
              <button type="button" className="btn btn-quiet" disabled={pending} onClick={() => setClearPhoto(false)}>
                Keep photo
              </button>
            ) : null}
          </div>
        </div>
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
    </article>
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
      {HONOR_GROUPS.map(([category, label]) => {
        const items = honors.filter((item) => item.category === category);
        const adding = editor?.mode === "add" && editor.category === category;
        return (
          <div className="honor-group" key={category}>
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
            <div className="recog-grid">
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
              {items.map((honor) => {
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
                  <article className="recog" key={honor.id}>
                    <HonorPhoto src={honor.photo_url} />
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
                            <button
                              type="button"
                              className="btn btn-quiet"
                              disabled={pending}
                              onClick={() => setConfirmId(null)}
                            >
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
                  </article>
                );
              })}
            </div>
          </div>
        );
      })}
    </section>
  );
}
