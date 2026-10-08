import { useEffect } from "react";
import GuestView from "../pages/GuestView";
import { usePathname } from "../hooks/usePathname";

const GUEST_PATH = "/guest";

export default function AppRoutes() {
  const pathname = usePathname();

  useEffect(() => {
    if (pathname === GUEST_PATH) return;
    const hash = window.location.hash;
    window.history.replaceState(null, "", `${GUEST_PATH}${hash}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, [pathname]);

  if (pathname !== GUEST_PATH && pathname !== "/") return null;

  return <GuestView />;
}
