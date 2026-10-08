import { useState } from "react";
import { logoSrc, navLinks } from "../../data/guestContent";
import { useScrolled } from "../../hooks/useScrolled";

export default function SiteHeader() {
  const scrolled = useScrolled(36);
  const [open, setOpen] = useState(false);

  return (
    <header id="siteHeader" className={scrolled ? "is-scrolled" : undefined}>
      <a href="#top" className="brand">
        <img className="hero-medallion-navbar" src={logoSrc} alt="" />
        <span className="brand-text">
          <span className="name">Council 10930</span>
          <br />
          <span className="sub">Knights of Columbus</span>
        </span>
      </a>
      <button
        className="nav-toggle"
        id="navToggle"
        type="button"
        aria-label="Toggle navigation"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span />
        <span />
        <span />
      </button>
      <nav
        className={`primary-nav${open ? " open" : ""}`}
        id="primaryNav"
        aria-label="Primary"
      >
        {navLinks.map((link) => (
          <a key={link.href} href={link.href} onClick={() => setOpen(false)}>
            {link.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
