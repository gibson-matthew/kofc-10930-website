import { useEffect, useRef, useState } from "react";
import { mediaUrl } from "../api";
import { clampCrop } from "../crop";
import { PortraitSm } from "./Marks";

export const PHOTO_ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

export default function PhotoEditor({
  src,
  initial,
  pending = false,
  onSave,
  onCancel,
  onSwap,
  onRemove,
  removeLabel = "Remove photo",
  embedded = false,
  onChange,
}) {
  const [crop, setCrop] = useState(() =>
    clampCrop(initial?.x ?? initial?.crop_x, initial?.y ?? initial?.crop_y, initial?.scale ?? initial?.crop_scale ?? 1),
  );
  const stageRef = useRef(null);
  const windowRef = useRef(null);
  const dragRef = useRef(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (onChangeRef.current) onChangeRef.current(crop);
  }, [crop]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage || !src) return undefined;
    function onWheel(event) {
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.08 : 0.08;
      setCrop((current) => clampCrop(current.x, current.y, current.scale + delta));
    }
    stage.addEventListener("wheel", onWheel, { passive: false });
    return () => stage.removeEventListener("wheel", onWheel);
  }, [src]);

  function onPointerDown(event) {
    if (!src || event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { x: event.clientX, y: event.clientY, crop };
  }

  function onPointerMove(event) {
    const drag = dragRef.current;
    const frame = windowRef.current;
    if (!drag || !frame || !frame.clientWidth || !frame.clientHeight) return;
    const dx = (event.clientX - drag.x) / frame.clientWidth;
    const dy = (event.clientY - drag.y) / frame.clientHeight;
    setCrop(clampCrop(drag.crop.x + dx, drag.crop.y + dy, drag.crop.scale));
  }

  function onPointerUp() {
    dragRef.current = null;
  }

  return (
    <div className="photo-editor">
      <div
        className={src ? "photo-editor-stage" : "photo-editor-stage is-empty"}
        ref={stageRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div className="photo-editor-window" ref={windowRef}>
          {src ? (
            <img
              src={mediaUrl(src)}
              alt=""
              draggable={false}
              style={{ transform: `translate(${crop.x * 100}%, ${crop.y * 100}%) scale(${crop.scale})` }}
            />
          ) : (
            <span className="photo-editor-empty">
              <PortraitSm />
            </span>
          )}
        </div>
        <div className="photo-editor-ring" aria-hidden="true" />
      </div>
      <label className="signin-field">
        <span>Zoom</span>
        <input
          type="range"
          min="1"
          max="3"
          step="0.01"
          value={crop.scale}
          disabled={pending || !src}
          onChange={(event) => setCrop((current) => clampCrop(current.x, current.y, event.target.value))}
        />
      </label>
      <div className="signin-actions">
        <label className="btn btn-quiet">
          {src ? "Swap image" : "Choose image"}
          <input type="file" accept={PHOTO_ACCEPT} hidden disabled={pending} onChange={onSwap} />
        </label>
        {onRemove ? (
          <button type="button" className="btn btn-quiet" disabled={pending} onClick={onRemove}>
            {removeLabel}
          </button>
        ) : null}
        {embedded ? null : (
          <button type="button" className="btn" disabled={pending || !src} onClick={() => onSave(crop)}>
            Save photo
          </button>
        )}
        {embedded ? null : (
          <button type="button" className="btn btn-quiet" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
