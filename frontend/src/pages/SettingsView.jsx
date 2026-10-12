import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import CroppedPhoto from "../components/CroppedPhoto";
import { PortraitSm } from "../components/Marks";
import { clampCrop } from "../crop";
import {
  assignMediaSlot,
  deleteMedia,
  deleteMyPhoto,
  fetchMedia,
  fetchMembers,
  imageFileError,
  replaceMedia,
  setMemberAdmin,
  setMemberTitle,
  updateMyCrop,
  uploadMedia,
  uploadMyPhoto,
} from "../api";
import { memberLabel, OFFICER_TITLES } from "../titles";
import { navigate } from "../router";

const SLOTS = [
  ["logo", "Logo"],
  ["carousel.1", "Carousel photo 1"],
  ["carousel.2", "Carousel photo 2"],
  ["carousel.3", "Carousel photo 3"],
  ["carousel.4", "Carousel photo 4"],
  ["recog.0", "Family of the Month"],
  ["recog.1", "Knight of the Month"],
  ["recog.2", "Family of the Year"],
  ["recog.3", "Knight of the Year"],
];

const ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

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

function ViewingAngle({ src, initial, pending, onSave, onCancel }) {
  const [crop, setCrop] = useState(() => clampCrop(initial?.x, initial?.y, initial?.scale ?? 1));
  const frameRef = useRef(null);
  const dragRef = useRef(null);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return undefined;
    function onWheel(event) {
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.08 : 0.08;
      setCrop((current) => clampCrop(current.x, current.y, current.scale + delta));
    }
    frame.addEventListener("wheel", onWheel, { passive: false });
    return () => frame.removeEventListener("wheel", onWheel);
  }, []);

  function onPointerDown(event) {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { x: event.clientX, y: event.clientY, crop };
  }

  function onPointerMove(event) {
    const drag = dragRef.current;
    const frame = frameRef.current;
    if (!drag || !frame || !frame.clientWidth || !frame.clientHeight) return;
    const dx = (event.clientX - drag.x) / frame.clientWidth;
    const dy = (event.clientY - drag.y) / frame.clientHeight;
    setCrop(clampCrop(drag.crop.x + dx, drag.crop.y + dy, drag.crop.scale));
  }

  function onPointerUp() {
    dragRef.current = null;
  }

  return (
    <div className="viewing-angle">
      <div className="eyebrow left-only">Viewing Angle</div>
      <div
        className="settings-photo crop-frame viewing-stage"
        ref={frameRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <img
          src={src}
          alt=""
          draggable={false}
          style={{ transform: `translate(${crop.x * 100}%, ${crop.y * 100}%) scale(${crop.scale})` }}
        />
      </div>
      <label className="signin-field">
        <span>Zoom</span>
        <input
          type="range"
          min="1"
          max="3"
          step="0.01"
          value={crop.scale}
          disabled={pending}
          onChange={(event) => setCrop((current) => clampCrop(current.x, current.y, event.target.value))}
        />
      </label>
      <div className="signin-actions">
        <button type="button" className="btn" disabled={pending} onClick={() => onSave(crop)}>
          Save photo
        </button>
        <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function SettingsView() {
  const { user, refresh } = useAuth();
  const admin = Boolean(user?.is_admin);
  const [members, setMembers] = useState([]);
  const [images, setImages] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [loadingAdmin, setLoadingAdmin] = useState(admin);
  const [angle, setAngle] = useState(null);
  const angleRef = useRef(null);
  angleRef.current = angle;

  useEffect(() => {
    return () => {
      const current = angleRef.current;
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
    };
  }, []);

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

  async function run(action, success) {
    setPending(true);
    setError("");
    setNotice("");
    try {
      await action();
      if (success) setNotice(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  function closeAngle() {
    setAngle((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return null;
    });
  }

  function onPhoto(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    const problem = imageFileError(file);
    if (problem) {
      setNotice("");
      setError(problem);
      return;
    }
    const url = URL.createObjectURL(file);
    setError("");
    setNotice("");
    setAngle((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return { src: url, file, ownedUrl: true, crop: { x: 0, y: 0, scale: 1 } };
    });
  }

  function onAdjust() {
    if (!user?.photo_url) return;
    setError("");
    setNotice("");
    setAngle((current) => {
      if (current?.ownedUrl) URL.revokeObjectURL(current.src);
      return {
        src: user.photo_url,
        file: null,
        ownedUrl: false,
        crop: { x: user.crop_x || 0, y: user.crop_y || 0, scale: user.crop_scale || 1 },
      };
    });
  }

  function rememberMember(updated) {
    if (!updated) return;
    setMembers((current) => current.map((item) => (item.memberid === updated.memberid ? updated : item)));
  }

  function onSaveAngle(crop) {
    const file = angle?.file || null;
    run(async () => {
      const updated = file ? await uploadMyPhoto(file, crop) : await updateMyCrop(crop);
      await refresh();
      rememberMember(updated);
      closeAngle();
    }, "Profile photo saved.");
  }

  function onRemovePhoto() {
    closeAngle();
    run(async () => {
      const updated = await deleteMyPhoto();
      await refresh();
      rememberMember(updated);
    }, "Profile photo removed.");
  }

  async function reloadMedia() {
    setImages(await fetchMedia());
  }

  function onUpload(event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    const problem = imageFileError(file);
    if (problem) {
      setNotice("");
      setError(problem);
      return;
    }
    run(async () => {
      await uploadMedia(file);
      await reloadMedia();
    }, "Image uploaded.");
  }

  function onReplace(image, event) {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    const problem = imageFileError(file);
    if (problem) {
      setNotice("");
      setError(problem);
      return;
    }
    run(async () => {
      await replaceMedia(image.id, file);
      await reloadMedia();
    }, "Image replaced.");
  }

  function onRemove(image) {
    run(async () => {
      await deleteMedia(image.id);
      await reloadMedia();
    }, "Image removed.");
  }

  function onSlot(image, slot) {
    const previous = images;
    setImages((current) =>
      current.map((item) => {
        if (item.id === image.id) return { ...item, slot: slot || null };
        if (slot && item.slot === slot) return { ...item, slot: null };
        return item;
      }),
    );
    run(async () => {
      try {
        await assignMediaSlot(image.id, slot);
      } catch (err) {
        try {
          await reloadMedia();
        } catch {
          setImages(previous);
        }
        throw err;
      }
      await reloadMedia();
    }, "Image placement saved.");
  }

  function onMemberTitle(member, next) {
    run(async () => {
      await setMemberTitle(member.memberid, next);
      setMembers(await fetchMembers());
      if (member.memberid === user?.memberid) await refresh();
    }, "Title saved.");
  }

  function onAdmin(member, next) {
    run(async () => {
      const updated = await setMemberAdmin(member.memberid, next);
      setMembers((current) => current.map((item) => (item.memberid === updated.memberid ? updated : item)));
      if (updated.memberid === user?.memberid) await refresh();
    }, next ? "Admin access granted." : "Admin access removed.");
  }

  const adminCount = members.filter((member) => member.is_admin).length;

  return (
    <div className="container settings-view">
      <section aria-labelledby="settingsHeading">
        <div className="section-head">
          <div className="eyebrow left-only">Account</div>
          <h2 id="settingsHeading">Settings</h2>
          <p>{memberLabel(user)}</p>
          {admin ? (
            <p className="settings-jump">
              <a href="#admin-access">Admin access</a>
              <a href="#media">Media</a>
            </p>
          ) : null}
        </div>
        {error ? (
          <p className="signin-error" role="alert">
            {error}
          </p>
        ) : null}
        {notice ? (
          <p className="settings-notice" role="status">
            {notice}
          </p>
        ) : null}

        <div className="settings-stack">
          <article className="card settings-card">
            <h3>Profile photo</h3>
            <p>One photo. It is public and appears wherever you are shown.</p>
            {angle ? (
              <ViewingAngle
                key={angle.src}
                src={angle.src}
                initial={angle.crop}
                pending={pending}
                onSave={onSaveAngle}
                onCancel={closeAngle}
              />
            ) : (
              <div className="settings-photo-row">
                <Photo user={user} className="settings-photo" />
                <div className="signin-actions">
                  <label className="btn">
                    {user?.photo_url ? "Replace photo" : "Upload photo"}
                    <input type="file" accept={ACCEPT} hidden onChange={onPhoto} disabled={pending} />
                  </label>
                  {user?.photo_url ? (
                    <button type="button" className="btn btn-quiet" onClick={onAdjust} disabled={pending}>
                      Viewing angle
                    </button>
                  ) : null}
                  {user?.photo_url ? (
                    <button type="button" className="btn btn-quiet" onClick={onRemovePhoto} disabled={pending}>
                      Remove photo
                    </button>
                  ) : null}
                </div>
              </div>
            )}
          </article>
        </div>
        <div className="signin-actions settings-back">
          <button type="button" className="btn btn-quiet" onClick={() => navigate("/member")}>
            Back to members area
          </button>
        </div>
      </section>

      {admin ? (
        <section className="block" id="admin-access" aria-labelledby="adminHeading">
          <div className="section-head">
            <div className="eyebrow left-only">Webmaster</div>
            <h2 id="adminHeading">Admin access</h2>
            <p>Full edit access uses the same Edit page, Save changes, and Cancel changes controls.</p>
          </div>
          {loadingAdmin ? <p>Loading members…</p> : null}
          <div className="officer-grid">
            {members.map((member) => {
              const lastAdmin = member.is_admin && adminCount < 2;
              return (
                <article className="officer" key={member.memberid}>
                  <Photo user={member} className="portrait-sm" />
                  <div>
                    <div className="role">{member.memberid}</div>
                    <strong>{memberLabel(member)}</strong>
                    <label className="signin-field officer-pick">
                      <span>Officer title</span>
                      <select
                        value={member.title || ""}
                        disabled={pending}
                        onChange={(event) => onMemberTitle(member, event.target.value)}
                      >
                        <option value="">No title</option>
                        {OFFICER_TITLES.map(([label, abbrev]) => (
                          <option key={abbrev} value={abbrev}>
                            {abbrev} — {label}
                          </option>
                        ))}
                      </select>
                    </label>
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
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ) : null}

      {admin ? (
        <section className="block" id="media" aria-labelledby="mediaHeading">
          <div className="section-head">
            <div className="eyebrow left-only">Library</div>
            <h2 id="mediaHeading">Media</h2>
            <p>Upload a JPG, PNG, or WebP, then choose it for the logo, a carousel photo, or an About photo. Replace or remove any image. An empty slot uses the example image.</p>
          </div>
          <div className="signin-actions">
            <label className="btn">
              Upload image
              <input type="file" accept={ACCEPT} hidden onChange={onUpload} disabled={pending} />
            </label>
          </div>
          <div className="media-grid">
            {images.map((image) => (
              <article className="card media-card" key={image.id}>
                <img src={image.url} alt="" />
                <strong>{image.original_name}</strong>
                <label className="signin-field">
                  <span>Use for</span>
                  <select
                    value={image.slot || ""}
                    disabled={pending}
                    onChange={(event) => onSlot(image, event.target.value)}
                  >
                    <option value="">Not used</option>
                    {SLOTS.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="signin-actions">
                  <label className="btn btn-quiet">
                    Replace
                    <input
                      type="file"
                      accept={ACCEPT}
                      hidden
                      disabled={pending}
                      onChange={(event) => onReplace(image, event)}
                    />
                  </label>
                  <button type="button" className="btn btn-quiet" disabled={pending} onClick={() => onRemove(image)}>
                    Remove
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
