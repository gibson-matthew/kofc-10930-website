import { createRoot } from "react-dom/client";
import { AuthProvider } from "./auth/AuthContext";
import { LOGO_SRC } from "./content/seed";
import App from "./App.jsx";
import "./index.css";
import "../../css/shared.css";
import "../../css/public.css";
import "../../css/member.css";

function installSquareFavicon(src) {
  const image = new Image();
  image.onload = () => {
    const width = image.naturalWidth;
    const height = image.naturalHeight;
    if (!width || !height) return;
    const size = 128;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, size, size);
    const scale = Math.min(size / width, size / height);
    const drawWidth = width * scale;
    const drawHeight = height * scale;
    ctx.drawImage(image, (size - drawWidth) / 2, (size - drawHeight) / 2, drawWidth, drawHeight);
    const link = document.querySelector("link[rel='icon']") || document.createElement("link");
    link.id = "site-favicon";
    link.rel = "icon";
    link.type = "image/png";
    link.sizes = "128x128";
    link.href = canvas.toDataURL("image/png");
    if (!link.parentNode) document.head.appendChild(link);
  };
  image.src = src;
}

installSquareFavicon(LOGO_SRC);

const memberRoute = window.location.pathname === "/member" || window.location.pathname.startsWith("/member/");
document.body.className = memberRoute ? "page-member" : "page-public";
document.body.dataset.page = memberRoute ? "member" : "public";

createRoot(document.getElementById("root")).render(
  <AuthProvider>
    <App />
  </AuthProvider>,
);
