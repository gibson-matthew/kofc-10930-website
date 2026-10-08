import { useCallback, useEffect, useRef, useState } from "react";
import type { FocusEvent, KeyboardEvent } from "react";

const INTERVAL_MS = 5000;

export function useHeroCarousel(total: number) {
  const [index, setIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | null>(null);
  const reducedRef = useRef(false);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    stop();
    if (reducedRef.current || total === 0) return;
    timerRef.current = window.setInterval(() => {
      setIndex((current) => (current + 1) % total);
    }, INTERVAL_MS);
  }, [stop, total]);

  useEffect(() => {
    reducedRef.current = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    start();
    return stop;
  }, [start, stop]);

  const goTo = useCallback(
    (next: number, userInitiated: boolean) => {
      if (total === 0) return;
      setIndex(((next % total) + total) % total);
      if (userInitiated) start();
    },
    [start, total],
  );

  const onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setIndex((current) => (current - 1 + total) % total);
        start();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setIndex((current) => (current + 1) % total);
        start();
      }
    },
    [start, total],
  );

  const onBlur = useCallback(
    (event: FocusEvent<HTMLDivElement>) => {
      const next = event.relatedTarget;
      if (!(next instanceof Node) || !event.currentTarget.contains(next)) {
        start();
      }
    },
    [start],
  );

  return {
    index,
    rootRef,
    goTo,
    onKeyDown,
    onMouseEnter: stop,
    onMouseLeave: start,
    onFocus: stop,
    onBlur,
  };
}
