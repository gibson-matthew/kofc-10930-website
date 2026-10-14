export const HONOR_GROUPS = [
  ["knight_month", "Past Knights of the Month"],
  ["family_month", "Past Families of the Month"],
  ["knight_year", "Past Knights of the Year"],
  ["family_year", "Past Families of the Year"],
  ["past_gk", "Past Grand Knights"],
];

export const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const HONOR_FALLBACK = [
  {
    id: "example-knight-month",
    category: "knight_month",
    name: "James Harrington",
    period: "October 2025",
    note: "He chaired the Coats for Kids sorting crew.",
    photo_url: null,
  },
  {
    id: "example-family-month",
    category: "family_month",
    name: "The Nguyen Family",
    period: "September 2025",
    note: "They led the parish food pantry weekend.",
    photo_url: null,
  },
  {
    id: "example-knight-year",
    category: "knight_year",
    name: "Robert Hale",
    period: "2025",
    note: "He logged charity hours each month and mentored new members.",
    photo_url: null,
  },
  {
    id: "example-family-year",
    category: "family_year",
    name: "The Ortiz Family",
    period: "2025",
    note: "They hosted monthly rosaries and supported the scholarship fund.",
    photo_url: null,
  },
  {
    id: "example-past-gk",
    category: "past_gk",
    name: "William Grant",
    period: "2024–25",
    note: "He led the council through the Coats for Kids year.",
    photo_url: null,
  },
];

export const EVENT_FALLBACK = [
  {
    id: "example-1",
    title: "Online officers meeting",
    event_date: "2026-10-13",
    event_time: "7:00 p.m.",
    location: null,
    description: "Brothers meet online to review the month's business before the council meeting.",
  },
  {
    id: "example-2",
    title: "Council rosary",
    event_date: "2026-10-14",
    event_time: "6:40 p.m.",
    location: "Parish hall",
    description: "The council prays the rosary together in the parish hall before the business meeting.",
  },
  {
    id: "example-3",
    title: "Council business meeting",
    event_date: "2026-10-14",
    event_time: "7:00 p.m.",
    location: "Parish hall",
    description: "Officers report, motions are heard, and brothers plan the next charity work.",
  },
  {
    id: "example-4",
    title: "Red Cross blood drive",
    event_date: "2026-10-24",
    event_time: "9:00 a.m. to 3:00 p.m.",
    location: "5953 Bowman Roberts Rd",
    description: "Give blood at the council hall. Appointments and walk-ins are both welcome.",
  },
  {
    id: "example-5",
    title: "Coats for Kids distribution",
    event_date: "2026-11-14",
    event_time: "8:00 a.m.",
    location: "Parish",
    description: "Sorted coats are handed out to families at the parish from the morning shift.",
  },
];

export function collapse(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}
