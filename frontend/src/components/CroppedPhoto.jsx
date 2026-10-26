import { mediaUrl } from "../api";

export default function CroppedPhoto({ src, crop, className, alt = "", onError }) {
  const x = Number(crop?.crop_x ?? crop?.x ?? 0) || 0;
  const y = Number(crop?.crop_y ?? crop?.y ?? 0) || 0;
  const scale = Number(crop?.crop_scale ?? crop?.scale ?? 1) || 1;
  return (
    <span className={["crop-frame", className].filter(Boolean).join(" ")}>
      <img
        src={mediaUrl(src)}
        alt={alt}
        draggable={false}
        onError={onError}
        style={{ transform: `translate(${x * 100}%, ${y * 100}%) scale(${scale})` }}
      />
    </span>
  );
}
