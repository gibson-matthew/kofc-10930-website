import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Block, Eyebrow } from "../components/Block";
import { SvgSprite } from "../components/Marks";
import { SignInDialog } from "../components/SignInDialog";
import { ContentProvider, useContent } from "../content/ContentContext";
import { slides } from "../content/seed";

const TITLE = "Knights of Columbus — Council 10930 — Fort Worth, TX";

function Carousel() {
  const { text } = useContent();
  const [index, setIndex] = useState(0);
  const indexRef = useRef(0);
  const rootRef = useRef(null);
  const timerRef = useRef(null);
  const reducedRef = useRef(false);
  const total = slides.length;

  function stop() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function goTo(next, user) {
    const wrapped = (next + total) % total;
    indexRef.current = wrapped;
    setIndex(wrapped);
    if (user) restart();
  }

  function start() {
    stop();
    if (reducedRef.current) return;
    timerRef.current = window.setInterval(() => {
      goTo(indexRef.current + 1, false);
    }, 5000);
  }

  function restart() {
    stop();
    start();
  }

  useEffect(() => {
    reducedRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const root = rootRef.current;
    start();
    if (!root) return stop;
    const pause = () => stop();
    const resume = () => start();
    const onFocusOut = (event) => {
      if (!root.contains(event.relatedTarget)) resume();
    };
    root.addEventListener("mouseenter", pause);
    root.addEventListener("mouseleave", resume);
    root.addEventListener("focusin", pause);
    root.addEventListener("focusout", onFocusOut);
    return () => {
      stop();
      root.removeEventListener("mouseenter", pause);
      root.removeEventListener("mouseleave", resume);
      root.removeEventListener("focusin", pause);
      root.removeEventListener("focusout", onFocusOut);
    };
  }, []);

  return (
    <div
      className="hero-carousel"
      id="heroCarousel"
      role="region"
      aria-roledescription="carousel"
      aria-label="Council photos"
      ref={rootRef}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          goTo(indexRef.current - 1, true);
        }
        if (event.key === "ArrowRight") {
          event.preventDefault();
          goTo(indexRef.current + 1, true);
        }
      }}
    >
      <div className="carousel-track">
        {slides.map((slide, slideIndex) => (
          <div className={slideIndex === index ? "carousel-slide is-active" : "carousel-slide"} key={slide.src}>
            <img src={slide.src} alt={text(slide.altKey)} width="800" height="500" />
          </div>
        ))}
      </div>
      <button type="button" className="carousel-btn prev" aria-label="Previous photo" onClick={() => goTo(index - 1, true)}>
        ‹
      </button>
      <button type="button" className="carousel-btn next" aria-label="Next photo" onClick={() => goTo(index + 1, true)}>
        ›
      </button>
      <div className="carousel-dots" role="tablist" aria-label="Slide controls">
        {slides.map((slide, slideIndex) => (
          <button
            key={slide.src}
            type="button"
            className={slideIndex === index ? "carousel-dot is-active" : "carousel-dot"}
            role="tab"
            aria-label={`Go to photo ${slideIndex + 1}`}
            onClick={() => goTo(slideIndex, true)}
          />
        ))}
      </div>
    </div>
  );
}

function PublicView() {
  const { text } = useContent();
  const [scrolled, setScrolled] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [signInOpen, setSignInOpen] = useState(false);

  useLayoutEffect(() => {
    document.body.className = "page-public";
    document.body.dataset.page = "public";
    document.title = TITLE;
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 36);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const nodes = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -32px 0px" },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  function closeNav() {
    setNavOpen(false);
  }

  function openSignIn() {
    closeNav();
    setSignInOpen(true);
  }

  return (
    <>
      <SvgSprite />
      <header id="siteHeader" className={scrolled ? "is-scrolled" : undefined}>
        <a href="#top" className="brand">
          <img className="hero-medallion-navbar" src="/images/kofc-logo.png" alt="" />
          <span className="brand-text">
            <Block id="brand.name" className="name" />
            <br />
            <Block id="brand.sub" className="sub" />
          </span>
        </a>
        <nav className={navOpen ? "primary-nav open" : "primary-nav"} id="primaryNav" aria-label="Primary">
          <Block id="nav.who" href="#who" locked onClick={closeNav} />
          <Block id="nav.what" href="#what" locked onClick={closeNav} />
          <Block id="nav.why" href="#why" locked onClick={closeNav} />
          <Block id="nav.join" href="#join" locked onClick={closeNav} />
          <button type="button" className="nav-signin" id="signInBtn" onClick={openSignIn}>
            {text("nav.signin")}
          </button>
        </nav>
        <button
          className="nav-toggle"
          id="navToggle"
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={navOpen ? "true" : "false"}
          onClick={() => setNavOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
      </header>

      <section id="top" className="hero">
        <div className="hero-texture" aria-hidden="true" />
        <div className="hero-glow" aria-hidden="true" />
        <span className="corner tl" aria-hidden="true" />
        <span className="corner tr" aria-hidden="true" />
        <span className="corner bl" aria-hidden="true" />
        <span className="corner br" aria-hidden="true" />
        <div className="hero-inner">
          <img className="hero-medallion" src="/images/kofc-logo.png" alt="" />
          <Eyebrow id="hero.eyebrow" />
          <Block id="hero.title" as="h1" />
          <Block id="hero.place" as="div" className="place" />
          <Carousel />
          <Block id="hero.cta" className="btn btn-lg" href="#join" />
        </div>
        <div className="scroll-cue" aria-hidden="true">
          <span className="line" />
        </div>
      </section>

      <section id="who" className="section">
        <div className="container">
          <div className="section-head reveal">
            <Eyebrow id="who.eyebrow" style={{ justifyContent: "center" }} />
            <Block id="who.title" as="h2" />
            <Block id="who.intro" as="p" />
          </div>
          <div className="grid">
            <article className="panel reveal">
              <Block id="who.mission.title" as="h3" />
              <Block id="who.mission.body" as="p" />
            </article>
            <article className="panel reveal">
              <Block id="who.parish.title" as="h3" />
              <Block id="who.parish.body" as="p" />
            </article>
            <article className="panel reveal">
              <Block id="who.members.title" as="h3" />
              <Block id="who.members.body" as="p" />
            </article>
          </div>
        </div>
      </section>

      <section className="legacy">
        <div className="container">
          <Eyebrow id="legacy.eyebrow" className="eyebrow left-only reveal" style={{ marginBottom: "1.4rem" }} />
          <div className="timeline">
            <div className="tl-item reveal">
              <Block id="legacy.1882.year" as="div" className="yr" />
              <Block id="legacy.1882.body" as="p" />
            </div>
            <div className="tl-item reveal">
              <Block id="legacy.1900s.year" as="div" className="yr" />
              <Block id="legacy.1900s.body" as="p" />
            </div>
            <div className="tl-item reveal">
              <Block id="legacy.today.year" as="div" className="yr" />
              <Block id="legacy.today.body" as="p" />
            </div>
          </div>
        </div>
      </section>

      <section id="what" className="section on-navy">
        <div className="container">
          <div className="section-head reveal">
            <Eyebrow id="what.eyebrow" style={{ justifyContent: "center" }} />
            <Block id="what.title" as="h2" />
            <Block id="what.intro" as="p" />
          </div>
          <div className="grid">
            <article className="panel reveal">
              <svg className="icon" viewBox="0 0 40 40" aria-hidden="true">
                <use href="#icon-rosary" />
              </svg>
              <Block id="what.faith.title" as="h3" />
              <Block id="what.faith.body" as="p" />
            </article>
            <article className="panel reveal">
              <svg className="icon" viewBox="0 0 40 40" aria-hidden="true">
                <use href="#icon-family" />
              </svg>
              <Block id="what.family.title" as="h3" />
              <Block id="what.family.body" as="p" />
            </article>
            <article className="panel reveal">
              <svg className="icon" viewBox="0 0 40 40" aria-hidden="true">
                <use href="#icon-charity" />
              </svg>
              <Block id="what.community.title" as="h3" />
              <Block id="what.community.body" as="p" />
            </article>
            <article className="panel reveal">
              <svg className="icon" viewBox="0 0 40 40" aria-hidden="true">
                <use href="#icon-youth" />
              </svg>
              <Block id="what.youth.title" as="h3" />
              <Block id="what.youth.body" as="p" />
            </article>
          </div>
        </div>
      </section>

      <Block id="banner" as="div" className="banner-stripe" />

      <section id="why" className="section">
        <div className="container">
          <div className="section-head reveal">
            <Eyebrow id="why.eyebrow" style={{ justifyContent: "center" }} />
            <Block id="why.title" as="h2" />
            <Block id="why.intro" as="p" />
          </div>
          <div className="grid">
            <article className="panel reveal">
              <Block id="why.faith.title" as="h3" />
              <Block id="why.faith.body" as="p" />
            </article>
            <article className="panel reveal">
              <Block id="why.serve.title" as="h3" />
              <Block id="why.serve.body" as="p" />
            </article>
            <article className="panel reveal">
              <Block id="why.brotherhood.title" as="h3" />
              <Block id="why.brotherhood.body" as="p" />
            </article>
            <article className="panel reveal">
              <Block id="why.lead.title" as="h3" />
              <Block id="why.lead.body" as="p" />
            </article>
          </div>
        </div>
      </section>

      <section id="join" className="join-section">
        <div className="container">
          <div className="join-frame reveal">
            <span className="corner tl" aria-hidden="true" />
            <span className="corner tr" aria-hidden="true" />
            <span className="corner bl" aria-hidden="true" />
            <span className="corner br" aria-hidden="true" />
            <img className="hero-medallion-end" src="/images/kofc-logo.png" alt="" />
            <Block id="join.title" as="h2" />
            <Block id="join.body" as="p" />
            <Block id="join.cta" className="btn btn-lg" href="#" />
          </div>
        </div>
      </section>

      <footer>
        <div className="container">
          <div className="footer-inner">
            <div className="footer-brand">
              <img className="hero-medallion-navbar" src="/images/kofc-logo.png" alt="" />
              <span>
                <Block id="footer.name" className="name" />
                <Block id="footer.sub" className="sub" />
              </span>
            </div>
            <nav className="footer-nav" aria-label="Footer">
              <Block id="footer.nav.who" href="#who" />
              <Block id="footer.nav.what" href="#what" />
              <Block id="footer.nav.why" href="#why" />
              <Block id="footer.nav.join" href="#join" />
            </nav>
          </div>
          <div className="footer-bottom">
            <Block id="footer.copy" />
            <Block id="footer.principles" />
          </div>
        </div>
      </footer>

      <SignInDialog open={signInOpen} onClose={() => setSignInOpen(false)} />
    </>
  );
}

export default function PublicPage() {
  return (
    <ContentProvider slug="public">
      <PublicView />
    </ContentProvider>
  );
}
