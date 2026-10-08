import { logoSrc } from "../../data/guestContent";
import CornerMarks from "../ui/CornerMarks";
import HeroCarousel from "./HeroCarousel";

export default function HeroSection() {
  return (
    <section id="top" className="hero">
      <div className="hero-texture" aria-hidden="true" />
      <div className="hero-glow" aria-hidden="true" />
      <CornerMarks />

      <div className="hero-inner">
        <img className="hero-medallion" src={logoSrc} alt="Knights of Columbus" />
        <div className="eyebrow">Knights of Columbus</div>
        <h1>Council 10930</h1>
        <div className="place">Fort Worth, Texas</div>
        <HeroCarousel />
        <a href="#join" className="btn">
          Become a Knight
        </a>
      </div>

      <div className="scroll-cue" aria-hidden="true">
        <span className="line" />
      </div>
    </section>
  );
}
