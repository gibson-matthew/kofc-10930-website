import { Outlet } from "react-router-dom";
import AdminSidebar from "./AdminSidebar";
import Header from "./Header";

export default function AdminLayout() {
  return (
    <div className="admin-layout flex">
      <AdminSidebar />

      <div className="flex-1">
        <Header />
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
