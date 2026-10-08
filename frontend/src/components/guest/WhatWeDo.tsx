import { whatWeDo } from "../../data/guestContent";
import Reveal from "../ui/Reveal";

export default function WhatWeDo() {
  return (
    <section id="what" className="section on-navy">
      <div className="container">
        <Reveal className="section-head">
          <div className="eyebrow">{whatWeDo.eyebrow}</div>
          <h2>{whatWeDo.title}</h2>
          <p>{whatWeDo.intro}</p>
        </Reveal>
        <div className="grid">
          {whatWeDo.panels.map((panel) => (
            <Reveal as="article" className="panel" key={panel.title}>
              <svg className="icon" viewBox="0 0 40 40" aria-hidden="true">
                <use href={`#${panel.icon}`} />
              </svg>
              <h3>{panel.title}</h3>
              <p>{panel.body}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
