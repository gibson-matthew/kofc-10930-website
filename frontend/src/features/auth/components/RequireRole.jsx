import { Navigate, Outlet } from "react-router-dom";
import useRole from "../../../app/hooks/useRole";

export default function RequireRole({ role }) {
  const { hasRole } = useRole();

  if (!hasRole(role)) {
    return <Navigate to="/member/dashboard" replace />;
  }

  return <Outlet />;
}
