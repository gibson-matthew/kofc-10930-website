import { useEffect, useRef, useState } from "react";
import type { ReactNode, Ref } from "react";

type RevealProps = {
  as?: "div" | "article";
  className?: string;
  children: ReactNode;
};

export default function Reveal({
  as = "div",
  className = "",
  children,
}: RevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -32px 0px" },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const classNames = ["reveal", visible ? "is-visible" : "", className]
    .filter(Boolean)
    .join(" ");

  if (as === "article") {
    return (
      <article ref={ref as Ref<HTMLElement>} className={classNames}>
        {children}
      </article>
    );
  }

  return (
    <div ref={ref as Ref<HTMLDivElement>} className={classNames}>
      {children}
    </div>
  );
}
