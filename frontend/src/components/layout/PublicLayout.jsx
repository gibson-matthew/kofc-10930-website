import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

export default function PublicLayout() {
  return (
    <div className="public-layout">
      <Header />
      <main>
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
