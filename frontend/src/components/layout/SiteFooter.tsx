import { logoSrc, navLinks } from "../../data/guestContent";

export default function SiteFooter() {
  return (
    <footer>
      <div className="container">
        <div className="footer-inner">
          <div className="footer-brand">
            <img className="hero-medallion-navbar" src={logoSrc} alt="" />
            <span>
              <span className="name">Council 10930</span>
              <span className="sub">Knights of Columbus · Fort Worth, TX</span>
            </span>
          </div>
          <nav className="footer-nav" aria-label="Footer">
            {navLinks.map((link) => (
              <a key={link.href} href={link.href}>
                {link.label}
              </a>
            ))}
          </nav>
        </div>
        <div className="footer-bottom">
          <span>© 2026 Knights of Columbus Council 10930 — Fort Worth, TX</span>
          <span>Charity · Unity · Fraternity · Patriotism</span>
        </div>
      </div>
    </footer>
  );
}
