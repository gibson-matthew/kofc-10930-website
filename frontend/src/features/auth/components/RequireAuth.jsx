import { Navigate, Outlet } from "react-router-dom";
import useAuth from "../../../app/hooks/useAuth";

export default function RequireAuth() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
