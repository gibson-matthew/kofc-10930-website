export default function SvgSprite() {
  return (
    <svg className="svg-sprite" width="0" height="0" aria-hidden="true">
      <defs>
        <symbol id="cross-pattee" viewBox="0 0 100 100">
          <g fill="currentColor">
            <path d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z" />
            <path
              d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z"
              transform="rotate(90 50 50)"
            />
            <path
              d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z"
              transform="rotate(180 50 50)"
            />
            <path
              d="M42,50 L42,30 L35,14 L65,14 L58,30 L58,50 Z"
              transform="rotate(270 50 50)"
            />
          </g>
        </symbol>
        <symbol id="medallion" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="47"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.1"
            opacity="0.95"
          />
          <circle
            cx="50"
            cy="50"
            r="41.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.55"
            opacity="0.5"
          />
          <use
            href="#cross-pattee"
            width="100"
            height="100"
            x="0"
            y="0"
            transform="scale(0.58) translate(36,36)"
          />
        </symbol>
        <symbol id="icon-rosary" viewBox="0 0 40 40">
          <circle
            cx="20"
            cy="13"
            r="9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path
            d="M20 22 L20 34 M14 34 H26"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
          <circle cx="20" cy="27" r="1.5" fill="currentColor" />
        </symbol>
        <symbol id="icon-family" viewBox="0 0 40 40">
          <path
            d="M8 32 V20 L20 10 L32 20 V32 Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M17 32 V23 H23 V32"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </symbol>
        <symbol id="icon-charity" viewBox="0 0 40 40">
          <path
            d="M20 30 C10 23 6 17 10 12 C13 8.4 18 9 20 13 C22 9 27 8.4 30 12 C34 17 30 23 20 30 Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </symbol>
        <symbol id="icon-youth" viewBox="0 0 40 40">
          <path
            d="M20 10 L34 16 L20 22 L6 16 Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M13 19 V26 C13 28.5 16 30.5 20 30.5 C24 30.5 27 28.5 27 26 V19"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          />
        </symbol>
      </defs>
    </svg>
  );
}
