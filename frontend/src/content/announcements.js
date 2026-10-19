/** Example announcements used when the council records cannot be loaded. */

export const ANNOUNCEMENT_EXAMPLES = [
  {
    id: "example-exemplification",
    title: "Exemplification practice",
    summary: "Practice details stay with the council.",
    posted_on: "2026-10-08",
    body:
      "<p>Exemplification practice stays with the council. Come ready to review the degree and the evening duties.</p><ul><li>Parish hall</li><li>Brothers only</li></ul>",
  },
  {
    id: "example-meeting",
    title: "Business meeting reminder",
    summary: "Officers report on Wednesday.",
    posted_on: "2026-09-20",
    body: "<p>Officers report at the business meeting. Brothers plan the next charity work in the parish hall.</p>",
  },
];

export function exampleAnnouncement(id) {
  return ANNOUNCEMENT_EXAMPLES.find((item) => item.id === id) || null;
}
