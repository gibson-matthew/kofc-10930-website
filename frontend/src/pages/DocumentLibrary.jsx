import { useEffect, useState } from "react";
import {
  DOCUMENT_ACCEPT,
  deleteDocument,
  documentFileError,
  documentFileUrl,
  fetchDocuments,
  uploadDocument,
} from "../api";
import { MONTHS, collapse } from "../content/records";
import { trackClick, trackSearchUse, watchSearch } from "../tracking";

const DOCUMENT_FALLBACK = {
  treasurer: [
    {
      id: "example-treasurer-september",
      title: "September 2026 statement",
      description: "Receipts and disbursements for September.",
      uploaded_on: "2026-10-02",
      content_type: "application/pdf",
    },
    {
      id: "example-treasurer-august",
      title: "August 2026 statement",
      description: "Receipts and disbursements for August.",
      uploaded_on: "2026-09-04",
      content_type: "application/pdf",
    },
  ],
  financial_secretary: [
    {
      id: "example-fs-membership",
      title: "September 2026 membership report",
      description: "New members, transfers, and suspensions.",
      uploaded_on: "2026-10-03",
      content_type: "application/pdf",
    },
    {
      id: "example-fs-dues",
      title: "Dues notes, September 2026",
      description: "Brothers with dues still open this month.",
      uploaded_on: "2026-09-15",
      content_type: "application/pdf",
    },
  ],
};

function formatUploadedOn(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
  if (!match) return "";
  const month = MONTHS[Number(match[2]) - 1];
  if (!month) return "";
  return `${month} ${Number(match[3])}, ${match[1]}`;
}

function librarySearchText(doc) {
  const shownDate = formatUploadedOn(doc.uploaded_on);
  return collapse(`${doc.title || ""} ${doc.description || ""} ${shownDate} ${doc.uploaded_on || ""}`)
    .toLowerCase()
    .replace(/[\u2013\u2014-]/g, "-");
}

function DocumentForm({ pending, onSave, onCancel, onError }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);

  function onFile(event) {
    const chosen = event.target.files && event.target.files[0];
    if (!chosen) {
      setFile(null);
      return;
    }
    const problem = documentFileError(chosen);
    if (problem) {
      event.target.value = "";
      setFile(null);
      onError(problem);
      return;
    }
    setFile(chosen);
    onError("");
  }

  function submit(event) {
    event.preventDefault();
    if (pending) return;
    const cleanedTitle = collapse(title);
    const cleanedDescription = collapse(description);
    if (!cleanedTitle) {
      onError("Enter a title.");
      return;
    }
    if (cleanedTitle.length > 120) {
      onError("Title must be 120 characters or fewer.");
      return;
    }
    if (cleanedDescription.length > 280) {
      onError("Description must be 280 characters or fewer.");
      return;
    }
    const problem = documentFileError(file);
    if (problem) {
      onError(problem);
      return;
    }
    onSave({ title: cleanedTitle, description: cleanedDescription }, file);
  }

  return (
    <form className="doc-form" onSubmit={submit}>
      <label className="signin-field">
        <span>Title</span>
        <input
          type="text"
          maxLength={120}
          value={title}
          disabled={pending}
          onChange={(event) => setTitle(event.target.value)}
        />
      </label>
      <label className="signin-field">
        <span>Description</span>
        <input
          type="text"
          maxLength={280}
          value={description}
          disabled={pending}
          onChange={(event) => setDescription(event.target.value)}
        />
        <p className="settings-hint">Optional.</p>
      </label>
      <label className="signin-field">
        <span>File</span>
        <input type="file" accept={DOCUMENT_ACCEPT} disabled={pending} onChange={onFile} />
      </label>
      <div className="signin-actions recog-actions">
        <button type="submit" className="btn" disabled={pending}>
          Save document
        </button>
        <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function DocumentLibrary({ library, canManage }) {
  const [documents, setDocuments] = useState([]);
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [adding, setAdding] = useState(false);
  const [confirmId, setConfirmId] = useState(null);
  const [query, setQuery] = useState("");
  const manage = Boolean(canManage) && !fallback;

  useEffect(() => {
    let cancel = false;
    setLoaded(false);
    fetchDocuments(library)
      .then((rows) => {
        if (cancel) return;
        setDocuments(Array.isArray(rows) ? rows : []);
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setDocuments(DOCUMENT_FALLBACK[library] || []);
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, [library]);

  useEffect(() => {
    if (!manage) {
      setAdding(false);
      setConfirmId(null);
    }
  }, [manage]);

  useEffect(() => {
    const needle = librarySearchText({ title: query, description: "", uploaded_on: "" });
    if (!needle) {
      watchSearch(`library.${library}`, "", 0);
      return;
    }
    const count = documents.filter((doc) => librarySearchText(doc).includes(needle)).length;
    watchSearch(`library.${library}`, query, count);
  }, [query, documents, library]);

  async function reload() {
    const rows = await fetchDocuments(library);
    setDocuments(Array.isArray(rows) ? rows : []);
    setFallback(false);
  }

  async function onSave(fields, file) {
    setPending(true);
    setError("");
    try {
      await uploadDocument(library, fields, file);
      setAdding(false);
      try {
        await reload();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Saved, but the list could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the document.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove(id) {
    setPending(true);
    setError("");
    try {
      await deleteDocument(id);
      setConfirmId(null);
      setDocuments((current) => current.filter((item) => item.id !== id));
      try {
        await reload();
      } catch {
        /* The removed document is already hidden. */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the document.");
    } finally {
      setPending(false);
    }
  }

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
      {manage && !adding ? (
        <div className="signin-actions recog-actions">
          <button
            type="button"
            className="btn"
            disabled={pending}
            onClick={() => {
              setError("");
              setConfirmId(null);
              setAdding(true);
            }}
          >
            Add document
          </button>
        </div>
      ) : null}
      {manage && adding ? (
        <DocumentForm
          pending={pending}
          onError={setError}
          onCancel={() => setAdding(false)}
          onSave={onSave}
        />
      ) : null}
      {loaded && documents.length === 0 ? <p className="settings-hint">None recorded yet.</p> : null}
      {documents.length > 0 ? (
        <label className="signin-field doc-search">
          <span>Search</span>
          <input
            type="search"
            value={query}
            placeholder="Title, date, or description"
            autoComplete="off"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      ) : null}
      {documents.length > 0 ? (
        <DocumentList
          documents={documents}
          library={library}
          query={query}
          fallback={fallback}
          manage={manage}
          pending={pending}
          confirmId={confirmId}
          onConfirm={setConfirmId}
          onRemove={onRemove}
          onStartRemove={(id) => {
            setAdding(false);
            setConfirmId(id);
          }}
        />
      ) : null}
    </>
  );
}

function DocumentList({
  documents,
  library,
  query,
  fallback,
  manage,
  pending,
  confirmId,
  onConfirm,
  onRemove,
  onStartRemove,
}) {
  const needle = librarySearchText({ title: query, description: "", uploaded_on: "" });
  const shown = needle
    ? documents.filter((doc) => librarySearchText(doc).includes(needle))
    : documents;
  return (
    <div className="doc-scroll">
      {needle && shown.length === 0 ? (
        <p className="settings-hint" role="status">
          No matches.
        </p>
      ) : (
        <ul className="doc-list">
          {shown.map((doc) => {
            const confirming = confirmId === doc.id;
            const downloadable = !fallback && Number.isInteger(doc.id);
            const pdf = doc.content_type === "application/pdf";
            return (
              <li key={doc.id}>
                <h3>{doc.title}</h3>
                {doc.uploaded_on ? <p>{formatUploadedOn(doc.uploaded_on)}</p> : null}
                {doc.description ? <p>{doc.description}</p> : null}
                {downloadable || manage ? (
                  <div className="signin-actions recog-actions">
                    {downloadable ? (
                      pdf ? (
                        <a
                          className="btn"
                          href={documentFileUrl(doc.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={() => {
                            trackClick("library_preview", { library, document_id: doc.id });
                            if (needle) trackSearchUse(`library.${library}`, query, { document_id: doc.id });
                          }}
                        >
                          Open
                        </a>
                      ) : (
                        <a
                          className="btn"
                          href={documentFileUrl(doc.id)}
                          download={doc.original_name || ""}
                          onClick={() => {
                            trackClick("library_download", { library, document_id: doc.id });
                            if (needle) trackSearchUse(`library.${library}`, query, { document_id: doc.id });
                          }}
                        >
                          Download
                        </a>
                      )
                    ) : null}
                    {manage ? (
                      confirming ? (
                        <>
                          <button type="button" className="btn" disabled={pending} onClick={() => onRemove(doc.id)}>
                            Remove
                          </button>
                          <button
                            type="button"
                            className="btn btn-quiet"
                            disabled={pending}
                            onClick={() => onConfirm(null)}
                          >
                            Keep
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-quiet"
                          disabled={pending}
                          onClick={() => onStartRemove(doc.id)}
                        >
                          Remove
                        </button>
                      )
                    ) : null}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
