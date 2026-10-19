/** Example nominations used when the council records cannot be loaded. */

export const NOMINATION_CATEGORIES = [
  ["knight_month", "Knight of the Month", "month"],
  ["family_month", "Family of the Month", "month"],
  ["knight_year", "Knight of the Year", "year"],
  ["family_year", "Family of the Year", "year"],
];

export const NOMINATION_RESULT_EXAMPLES = {
  month_period: "2026-10",
  year_period: "2026",
  categories: [
    {
      category: "knight_month",
      label: "Knight of the Month",
      nominees: [
        {
          nominee_name: "Walter Shaw",
          nominee_member_id: "1000135",
          votes: 1,
          nominators: [
            {
              member_id: "1000000",
              display_name: "David Hernandez",
              reason: "He keeps the council charity work moving.",
            },
          ],
        },
      ],
    },
    {
      category: "family_month",
      label: "Family of the Month",
      nominees: [
        {
          nominee_name: "The Nguyen Family",
          nominee_member_id: "",
          votes: 1,
          nominators: [
            {
              member_id: "1000001",
              display_name: "Sample Brother",
              reason: "They welcome new brothers and their families.",
            },
          ],
        },
      ],
    },
    { category: "knight_year", label: "Knight of the Year", nominees: [] },
    { category: "family_year", label: "Family of the Year", nominees: [] },
  ],
};
