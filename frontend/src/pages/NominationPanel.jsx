import { useEffect, useState } from "react";
import { fetchNominationResults, fetchNominations, fetchRoster, saveNomination, withdrawNomination } from "../api";
import { NOMINATION_CATEGORIES, NOMINATION_RESULT_EXAMPLES } from "../content/nominations";
import { MONTHS, collapse } from "../content/records";

function stripTags(value) {
  return String(value || "")
    .replace(/\u0000/g, "")
    .replace(/<[^>]*>/g, "");
}

function cleanName(value) {
  return collapse(stripTags(value));
}

function cleanReason(value) {
  return collapse(stripTags(value));
}

function formatPeriod(period) {
  const month = /^(\d{4})-(\d{2})$/.exec(String(period || ""));
  if (month) {
    const name = MONTHS[Number(month[2]) - 1];
    return name ? `${name} ${month[1]}` : String(period);
  }
  if (/^\d{4}$/.test(String(period || ""))) return String(period);
  return "";
}

function categoryMeta(category) {
  return NOMINATION_CATEGORIES.find((item) => item[0] === category) || NOMINATION_CATEGORIES[0];
}

function voteLabel(count) {
  const total = Number(count) || 0;
  return total === 1 ? "1 nomination" : `${total} nominations`;
}

function optionLabel(member, roster) {
  const shared = roster.filter((item) => item.display_name === member.display_name).length > 1;
  return shared ? `${member.display_name} (${member.memberid})` : member.display_name;
}

function nominatorLabel(person, people) {
  const shared = people.filter((item) => item.display_name === person.display_name).length > 1;
  return shared ? `${person.display_name} (${person.member_id})` : person.display_name;
}

function numericId(id) {
  return /^\d+$/.test(String(id || ""));
}

function ResultsList({ results }) {
  const groups = Array.isArray(results?.categories) ? results.categories : [];
  return (
    <div className="doc-scroll">
      {groups.map((group) => {
        const nominees = Array.isArray(group.nominees) ? group.nominees : [];
        const period = String(group.category || "").endsWith("_year") ? results?.year_period : results?.month_period;
        return (
          <ul className="doc-list" key={group.category}>
            <li>
              <h3>{group.label}</h3>
              {formatPeriod(period) ? <p>{formatPeriod(period)}</p> : null}
            </li>
            {nominees.length === 0 ? (
              <li>
                <p>None recorded yet.</p>
              </li>
            ) : (
              nominees.map((nominee) => {
                const people = Array.isArray(nominee.nominators) ? nominee.nominators : [];
                const key = nominee.nominee_member_id || nominee.nominee_name;
                return (
                  <li key={key}>
                    <h3>{nominee.nominee_name}</h3>
                    <p>{voteLabel(nominee.votes)}</p>
                    {people.map((person) => (
                      <p key={person.member_id}>
                        {nominatorLabel(person, people)}
                        {person.reason ? `: ${person.reason}` : ""}
                      </p>
                    ))}
                  </li>
                );
              })
            )}
          </ul>
        );
      })}
    </div>
  );
}

export default function NominationPanel({ isAdmin }) {
  const [nominations, setNominations] = useState([]);
  const [monthPeriod, setMonthPeriod] = useState("");
  const [yearPeriod, setYearPeriod] = useState("");
  const [fallback, setFallback] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [category, setCategory] = useState("");
  const [memberId, setMemberId] = useState("");
  const [name, setName] = useState("");
  const [reason, setReason] = useState("");
  const [confirmId, setConfirmId] = useState(null);
  const [roster, setRoster] = useState([]);
  const [rosterReady, setRosterReady] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState(null);
  const [resultsError, setResultsError] = useState("");
  const [resultsLoaded, setResultsLoaded] = useState(false);
  const [resultsNonce, setResultsNonce] = useState(0);
  const admin = Boolean(isAdmin);
  const saved = nominations.find((item) => item.category === category) || null;
  const savedKey = saved ? `${saved.id}|${saved.nominee_member_id}|${saved.nominee_name}|${saved.reason}` : "";
  const meta = categoryMeta(category);
  const knight = meta[0] === "knight_month" || meta[0] === "knight_year";
  const period = meta[2] === "year" ? yearPeriod : monthPeriod;
  const periodLabel = formatPeriod(period);
  const members = [...roster].sort((a, b) => {
    const byName = String(a.display_name || "").localeCompare(String(b.display_name || ""), undefined, {
      sensitivity: "base",
    });
    if (byName) return byName;
    return String(a.memberid || "").localeCompare(String(b.memberid || ""));
  });

  useEffect(() => {
    let cancel = false;
    setLoaded(false);
    fetchNominations()
      .then((payload) => {
        if (cancel) return;
        setNominations(Array.isArray(payload?.nominations) ? payload.nominations : []);
        setMonthPeriod(payload?.month_period || "");
        setYearPeriod(payload?.year_period || "");
        setFallback(false);
        setLoaded(true);
      })
      .catch(() => {
        if (cancel) return;
        setNominations([]);
        setMonthPeriod(NOMINATION_RESULT_EXAMPLES.month_period);
        setYearPeriod(NOMINATION_RESULT_EXAMPLES.year_period);
        setFallback(true);
        setLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    let cancel = false;
    fetchRoster()
      .then((rows) => {
        if (cancel) return;
        setRoster(Array.isArray(rows) ? rows : []);
        setRosterReady(true);
      })
      .catch(() => {
        if (cancel) return;
        setRoster([]);
        setRosterReady(true);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!loaded) return;
    setMemberId(saved?.nominee_member_id || "");
    setName(saved?.nominee_name || "");
    setReason(saved?.reason || "");
    setConfirmId(null);
  }, [loaded, category, savedKey]);

  useEffect(() => {
    if (!admin) setShowResults(false);
  }, [admin]);

  useEffect(() => {
    if (!admin || !showResults || fallback) return undefined;
    let cancel = false;
    setResultsLoaded(false);
    setResultsError("");
    fetchNominationResults()
      .then((payload) => {
        if (cancel) return;
        setResults(payload);
        setResultsLoaded(true);
      })
      .catch((err) => {
        if (cancel) return;
        setResults(null);
        setResultsError(err instanceof Error ? err.message : "Could not load nomination results.");
        setResultsLoaded(true);
      });
    return () => {
      cancel = true;
    };
  }, [admin, showResults, fallback, resultsNonce]);

  async function reload() {
    const payload = await fetchNominations();
    setNominations(Array.isArray(payload?.nominations) ? payload.nominations : []);
    setMonthPeriod(payload?.month_period || "");
    setYearPeriod(payload?.year_period || "");
    setFallback(false);
    if (admin && showResults) setResultsNonce((value) => value + 1);
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (pending || fallback) return;
    setNotice("");
    const cleanedReason = cleanReason(reason);
    if (cleanedReason.length > 280) {
      setError("Reason must be 280 characters or fewer.");
      return;
    }
    const fields = { category, reason: cleanedReason, nominee_member_id: "", nominee_name: "" };
    if (knight) {
      if (!memberId) {
        setError("Choose a member from the list.");
        return;
      }
      fields.nominee_member_id = memberId;
    } else {
      const cleanedName = cleanName(name);
      if (!cleanedName) {
        setError("Enter the nominee's name.");
        return;
      }
      if (cleanedName.length > 120) {
        setError("Name must be 120 characters or fewer.");
        return;
      }
      fields.nominee_name = cleanedName;
    }
    setPending(true);
    setError("");
    try {
      await saveNomination(fields);
      try {
        await reload();
        setNotice("Saved");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Saved, but the nominations could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the nomination.");
    } finally {
      setPending(false);
    }
  }

  async function onWithdraw(id) {
    if (!numericId(id) || fallback) return;
    setPending(true);
    setError("");
    setNotice("");
    try {
      await withdrawNomination(id);
      setConfirmId(null);
      setNotice("Saved");
      try {
        await reload();
      } catch (err) {
        setNominations((current) => current.filter((item) => item.id !== id));
        setNotice("");
        setError(err instanceof Error ? err.message : "Withdrawn, but the nominations could not be reloaded.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not withdraw the nomination.");
    } finally {
      setPending(false);
    }
  }

  const knownMember = members.some((member) => member.memberid === memberId);
  const locked = pending || fallback || !loaded;

  return (
    <>
      {fallback ? (
        <p className="settings-hint">Nominations are unavailable right now.</p>
      ) : null}
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
      {!loaded ? <p className="settings-hint">Loading…</p> : null}
      <div className="nomination-pick" role="group" aria-label="Nomination category">
        {NOMINATION_CATEGORIES.map(([value, label]) => (
          <button
            type="button"
            key={value}
            className={category === value ? "btn" : "btn btn-quiet"}
            aria-pressed={category === value}
            disabled={pending}
            onClick={() => {
              setError("");
              setConfirmId(null);
              setCategory(value);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {category ? (
      <form className="doc-form" onSubmit={onSubmit}>
        <p className="settings-hint">{meta[1]}{periodLabel ? ` · Nominations for ${periodLabel}.` : ""}</p>
        {knight ? (
          <label className="signin-field">
            <span>Member</span>
            <select
              value={memberId}
              disabled={locked || !rosterReady}
              onChange={(event) => setMemberId(event.target.value)}
            >
              <option value="">Choose a member</option>
              {memberId && !knownMember ? <option value={memberId}>{name || "Selected member"}</option> : null}
              {members.map((member) => (
                <option key={member.memberid} value={member.memberid}>
                  {optionLabel(member, members)}
                </option>
              ))}
            </select>
            {rosterReady && members.length === 0 ? (
              <p className="settings-hint">Members are unavailable right now.</p>
            ) : null}
          </label>
        ) : (
          <label className="signin-field">
            <span>Family name</span>
            <input
              type="text"
              maxLength={120}
              value={name}
              disabled={locked}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
        )}
        <label className="signin-field">
          <span>Reason</span>
          <textarea
            rows={4}
            maxLength={280}
            value={reason}
            disabled={locked}
            onChange={(event) => setReason(event.target.value)}
          />
          <p className="settings-hint">Optional.</p>
        </label>
        <div className="signin-actions recog-actions">
          {saved && confirmId === saved.id ? (
            <>
              <button type="button" className="btn" disabled={pending || fallback} onClick={() => onWithdraw(saved.id)}>
                Withdraw
              </button>
              <button type="button" className="btn btn-quiet" disabled={pending} onClick={() => setConfirmId(null)}>
                Keep
              </button>
            </>
          ) : (
            <>
              <button type="submit" className="btn" disabled={locked}>
                {saved ? "Update nomination" : "Submit nomination"}
              </button>
              {saved ? (
                <button
                  type="button"
                  className="btn btn-quiet"
                  disabled={pending || fallback}
                  onClick={() => {
                    setError("");
                    setConfirmId(saved.id);
                  }}
                >
                  Withdraw
                </button>
              ) : null}
            </>
          )}
        </div>
      </form>
      ) : (
        <p className="settings-hint">Choose a category to nominate.</p>
      )}
      {admin ? (
        <div className="nomination-results">
          <div className="signin-actions recog-actions">
            <button type="button" className="btn btn-quiet" onClick={() => setShowResults((current) => !current)}>
              {showResults ? "Hide results" : "View results"}
            </button>
          </div>
          {showResults ? (
            fallback ? (
              <>
                <p className="settings-hint">Showing the example list while the council records are unavailable.</p>
                <ResultsList results={NOMINATION_RESULT_EXAMPLES} />
              </>
            ) : resultsError ? (
              <p className="signin-error" role="alert">
                {resultsError}
              </p>
            ) : !resultsLoaded ? (
              <p className="settings-hint">Loading…</p>
            ) : (
              <ResultsList results={results} />
            )
          ) : null}
        </div>
      ) : null}
    </>
  );
}
