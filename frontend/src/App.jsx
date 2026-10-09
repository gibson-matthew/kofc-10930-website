import MemberPage from "./pages/MemberPage";
import PublicPage from "./pages/PublicPage";
import { usePath } from "./router";

export default function App() {
  const path = usePath();
  if (path === "/member" || path.startsWith("/member/")) return <MemberPage />;
  return <PublicPage />;
}
