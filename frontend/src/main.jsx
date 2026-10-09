import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
import "../../css/shared.css";
import "../../css/public.css";
import "../../css/member.css";

const memberRoute = window.location.pathname === "/member" || window.location.pathname.startsWith("/member/");
document.body.className = memberRoute ? "page-member" : "page-public";
document.body.dataset.page = memberRoute ? "member" : "public";

createRoot(document.getElementById("root")).render(<App />);
