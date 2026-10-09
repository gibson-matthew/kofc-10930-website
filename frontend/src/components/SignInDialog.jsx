import { useEffect, useRef, useState } from "react";
import { login } from "../api";
import { useContent } from "../content/ContentContext";
import { navigate } from "../router";

export function SignInDialog({ open, onClose }) {
  const dialogRef = useRef(null);
  const { text } = useContent();
  const [membershipId, setMembershipId] = useState("");
  const [password, setPassword] = useState("");
  const closingRef = useRef(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open) {
      if (!dialog.open) dialog.showModal();
      dialog.querySelector("input")?.focus();
      return;
    }
    if (dialog.open) {
      closingRef.current = true;
      dialog.close();
      closingRef.current = false;
    }
  }, [open]);

  function reset() {
    setMembershipId("");
    setPassword("");
  }

  function close() {
    reset();
    onClose();
  }

  async function onSubmit(event) {
    event.preventDefault();
    try {
      const result = await login(membershipId, password);
      if (result?.token) sessionStorage.setItem("koc10930.token", result.token);
    } catch {
      /* Any submitted values are accepted, including when the API is down. */
    }
    reset();
    onClose();
    navigate("/member");
  }

  return (
    <dialog
      className="signin-dialog"
      id="signInDialog"
      aria-labelledby="signInTitle"
      ref={dialogRef}
      onClose={() => {
        if (closingRef.current) return;
        reset();
        onClose();
      }}
    >
      <h2 id="signInTitle">{text("signin.title")}</h2>
      <form id="signInForm" onSubmit={onSubmit} noValidate>
        <label className="signin-field">
          <span>{text("signin.membership")}</span>
          <input
            type="text"
            autoComplete="off"
            spellCheck={false}
            value={membershipId}
            onChange={(event) => setMembershipId(event.target.value)}
          />
        </label>
        <label className="signin-field">
          <span>{text("signin.password")}</span>
          <input
            type="password"
            autoComplete="off"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <div className="signin-actions">
          <button type="button" className="btn btn-quiet" id="signInCancel" onClick={close}>
            {text("signin.cancel")}
          </button>
          <button type="submit" className="btn">
            {text("signin.submit")}
          </button>
        </div>
      </form>
    </dialog>
  );
}
