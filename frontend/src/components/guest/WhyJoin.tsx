import { whyJoin } from "../../data/guestContent";
import Reveal from "../ui/Reveal";

export default function WhyJoin() {
  return (
    <section id="why" className="section">
      <div className="container">
        <Reveal className="section-head">
          <div className="eyebrow">{whyJoin.eyebrow}</div>
          <h2>{whyJoin.title}</h2>
          <p>{whyJoin.intro}</p>
        </Reveal>
        <div className="grid">
          {whyJoin.panels.map((panel) => (
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
