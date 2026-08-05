import { Outlet } from "react-router-dom";
import MemberSidebar from "./MemberSidebar";
import Header from "./Header";

export default function MemberLayout() {
  return (
    <div className="member-layout flex">
      <MemberSidebar />

      <div className="flex-1">
        <Header />
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
