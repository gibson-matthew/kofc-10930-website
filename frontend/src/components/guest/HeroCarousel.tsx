import { carouselSlides } from "../../data/guestContent";
import { useHeroCarousel } from "../../hooks/useHeroCarousel";

export default function HeroCarousel() {
  const {
    index,
    rootRef,
    goTo,
    onKeyDown,
    onMouseEnter,
    onMouseLeave,
    onFocus,
    onBlur,
  } = useHeroCarousel(carouselSlides.length);

  return (
    <div
      className="hero-carousel"
      id="heroCarousel"
      ref={rootRef}
      role="region"
      aria-roledescription="carousel"
      aria-label="Council photos"
      onKeyDown={onKeyDown}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      <div className="carousel-track">
        {carouselSlides.map((slide, slideIndex) => (
          <div
            key={slide.alt}
            className={`carousel-slide${slideIndex === index ? " is-active" : ""}`}
          >
            <img src={slide.src} alt={slide.alt} width={800} height={500} />
          </div>
        ))}
      </div>
      <button
        type="button"
        className="carousel-btn prev"
        aria-label="Previous photo"
        onClick={() => goTo(index - 1, true)}
      >
        ‹
      </button>
      <button
        type="button"
        className="carousel-btn next"
        aria-label="Next photo"
        onClick={() => goTo(index + 1, true)}
      >
        ›
      </button>
      <div className="carousel-dots" role="tablist" aria-label="Slide controls">
        {carouselSlides.map((slide, slideIndex) => (
          <button
            key={slide.alt}
            type="button"
            className={`carousel-dot${slideIndex === index ? " is-active" : ""}`}
            role="tab"
            aria-label={`Go to photo ${slideIndex + 1}`}
            onClick={() => goTo(slideIndex, true)}
          />
        ))}
      </div>
    </div>
  );
}
