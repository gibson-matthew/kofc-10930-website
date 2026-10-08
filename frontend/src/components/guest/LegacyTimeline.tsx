import { legacyItems } from "../../data/guestContent";
import Reveal from "../ui/Reveal";

export default function LegacyTimeline() {
  return (
    <section className="legacy">
      <div className="container">
        <Reveal className="eyebrow left-only">A Legacy of Service</Reveal>
        <div className="timeline">
          {legacyItems.map((item) => (
            <Reveal className="tl-item" key={item.year}>
              <div className="yr">{item.year}</div>
              <p>{item.body}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
