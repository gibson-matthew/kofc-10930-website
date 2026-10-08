import { logoSrc } from "../../data/guestContent";
import CornerMarks from "../ui/CornerMarks";
import Reveal from "../ui/Reveal";

export default function JoinSection() {
  return (
    <section id="join" className="join-section">
      <div className="container">
        <Reveal className="join-frame">
          <CornerMarks />
          <img
            className="hero-medallion-end"
            src={logoSrc}
            alt="Knights of Columbus"
          />
          <h2>Ready to Join Council 10930?</h2>
          <p>Take the first step toward becoming a Knight. We’ll walk you through it.</p>
          <a href="#" className="btn">
            Begin Your Journey
          </a>
        </Reveal>
      </div>
    </section>
  );
}
