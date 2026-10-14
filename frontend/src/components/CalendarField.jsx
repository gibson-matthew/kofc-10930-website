import { useEffect, useState } from "react";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function parseIsoDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1900 || year > 2100 || month < 1 || month > 12) return null;
  const date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
  return date;
}

export function formatLongDate(value) {
  const date = parseIsoDate(value);
  if (!date) return "";
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function isoFrom(year, monthIndex, day) {
  return `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function sameDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate()
  );
}

export default function CalendarField({ value, onChange, disabled }) {
  const selected = parseIsoDate(value);
  const [view, setView] = useState(() => {
    const start = selected || new Date();
    return new Date(start.getFullYear(), start.getMonth(), 1);
  });

  useEffect(() => {
    const parsed = parseIsoDate(value);
    if (!parsed) return;
    setView(new Date(parsed.getFullYear(), parsed.getMonth(), 1));
  }, [value]);

  const year = view.getFullYear();
  const month = view.getMonth();
  const atMin = year < 1900 || (year === 1900 && month === 0);
  const atMax = year > 2100 || (year === 2100 && month === 11);
  const firstWeekday = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  const monthLabel = view.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const cells = [];
  for (let index = 0; index < firstWeekday; index += 1) cells.push(null);
  for (let day = 1; day <= days; day += 1) cells.push(day);

  function shift(delta) {
    setView((current) => {
      const next = new Date(current.getFullYear(), current.getMonth() + delta, 1);
      if (next.getFullYear() < 1900 || next.getFullYear() > 2100) return current;
      return next;
    });
  }

  return (
    <div className="calendar">
      <div className="calendar-head">
        <button
          type="button"
          className="btn btn-quiet"
          aria-label="Previous month"
          disabled={disabled || atMin}
          onClick={() => shift(-1)}
        >
          Prev
        </button>
        <div className="calendar-month">{monthLabel}</div>
        <button
          type="button"
          className="btn btn-quiet"
          aria-label="Next month"
          disabled={disabled || atMax}
          onClick={() => shift(1)}
        >
          Next
        </button>
      </div>
      <div className="calendar-week" aria-hidden="true">
        {WEEKDAYS.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      <div className="calendar-grid" role="grid" aria-label={monthLabel}>
        {cells.map((day, index) => {
          if (!day) return <span key={`empty-${index}`} />;
          const date = new Date(year, month, day);
          const iso = isoFrom(year, month, day);
          const isSelected = Boolean(selected && sameDay(selected, date));
          const isToday = sameDay(today, date);
          const className = ["calendar-day", isToday ? "is-today" : "", isSelected ? "is-selected" : ""]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={iso}
              type="button"
              role="gridcell"
              className={className}
              aria-label={date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              aria-pressed={isSelected ? "true" : "false"}
              disabled={disabled}
              onClick={() => onChange(iso)}
            >
              {day}
            </button>
          );
        })}
      </div>
      <div className="calendar-chosen">{formatLongDate(value) || "Choose a day"}</div>
    </div>
  );
}
