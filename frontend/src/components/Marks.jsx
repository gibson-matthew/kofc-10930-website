export function Emblem({ className }) {
  return (
    <svg className={className} viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="2" />
      <path fill="currentColor" d="M43 50 V33 L36 18 H64 L57 33 V50 Z" />
      <path fill="currentColor" d="M43 50 V33 L36 18 H64 L57 33 V50 Z" transform="rotate(90 50 50)" />
      <path fill="currentColor" d="M43 50 V33 L36 18 H64 L57 33 V50 Z" transform="rotate(180 50 50)" />
      <path fill="currentColor" d="M43 50 V33 L36 18 H64 L57 33 V50 Z" transform="rotate(270 50 50)" />
    </svg>
  );
}

export function Avatar() {
  return (
    <svg className="avatar" viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r="32" fill="#122842" />
      <circle cx="32" cy="26" r="9" fill="#E8C96A" />
      <path d="M16 50.5c1.2-8.2 7.4-13 16-13s14.8 4.8 16 13" fill="#C9A227" />
    </svg>
  );
}

export function Portrait() {
  return (
    <svg className="portrait" viewBox="0 0 92 92" aria-hidden="true">
      <circle cx="46" cy="46" r="46" fill="#122842" />
      <circle cx="46" cy="36" r="14" fill="#E8C96A" />
      <path d="M20 76c2-14 12-22 26-22s24 8 26 22" fill="#C9A227" />
    </svg>
  );
}

export function PortraitSm() {
  return (
    <svg className="portrait-sm" viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r="32" fill="#122842" />
      <circle cx="32" cy="26" r="9" fill="#E8C96A" />
      <path d="M16 50.5c1.2-8.2 7.4-13 16-13s14.8 4.8 16 13" fill="#C9A227" />
    </svg>
  );
}

export function SvgSprite() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <symbol id="cross-pattee" viewBox="0 0 100 100">
          <g fill="currentColor">
            <path d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z" />
            <path d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z" transform="rotate(90 50 50)" />
            <path d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z" transform="rotate(180 50 50)" />
            <path d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z" transform="rotate(270 50 50)" />
          </g>
        </symbol>
        <symbol id="medallion" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="47" fill="none" stroke="currentColor" strokeWidth="1.1" opacity="0.95" />
          <circle cx="50" cy="50" r="41.5" fill="none" stroke="currentColor" strokeWidth="0.55" opacity="0.5" />
          <use href="#cross-pattee" width="100" height="100" x="0" y="0" transform="scale(0.58) translate(36,36)" />
        </symbol>
        <symbol id="icon-rosary" viewBox="0 0 40 40">
          <circle cx="20" cy="13" r="9" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M20 22 L20 34 M14 34 H26" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          <circle cx="20" cy="27" r="1.5" fill="currentColor" />
        </symbol>
        <symbol id="icon-family" viewBox="0 0 40 40">
          <path d="M8 32 V20 L20 10 L32 20 V32 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M17 32 V23 H23 V32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </symbol>
        <symbol id="icon-charity" viewBox="0 0 40 40">
          <path d="M20 30 C10 23 6 17 10 12 C13 8.4 18 9 20 13 C22 9 27 8.4 30 12 C34 17 30 23 20 30 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        </symbol>
        <symbol id="icon-youth" viewBox="0 0 40 40">
          <path d="M20 10 L34 16 L20 22 L6 16 Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M13 19 V26 C13 28.5 16 30.5 20 30.5 C24 30.5 27 28.5 27 26 V19" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </symbol>
      </defs>
    </svg>
  );
}
