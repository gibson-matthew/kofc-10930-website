import { whoWeAre } from "../../data/guestContent";
import Reveal from "../ui/Reveal";

export default function WhoWeAre() {
  return (
    <section id="who" className="section">
      <div className="container">
        <Reveal className="section-head">
          <div className="eyebrow">{whoWeAre.eyebrow}</div>
          <h2>{whoWeAre.title}</h2>
          <p>{whoWeAre.intro}</p>
        </Reveal>
        <div className="grid">
          {whoWeAre.panels.map((panel) => (
            <Reveal as="article" className="panel" key={panel.title}>
              <h3>{panel.title}</h3>
              <p>{panel.body}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
