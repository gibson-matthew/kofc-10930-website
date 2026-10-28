import { MONTHS } from "./content/records";

export function daysInMonth(month) {
  const value = Number(month);
  if (value === 2) return 29;
  if (value === 4 || value === 6 || value === 9 || value === 11) return 30;
  return 31;
}

export function birthdayGroups(members, today = new Date()) {
  const month = today.getMonth() + 1;
  const next = month === 12 ? 1 : month + 1;
  function people(value) {
    return (Array.isArray(members) ? members : [])
      .filter((member) => Number(member?.birth_month) === value && Number(member?.birth_day) >= 1)
      .map((member) => ({
        memberid: member.memberid,
        name: member.display_name || "Member",
        day: Number(member.birth_day),
      }))
      .sort((a, b) => a.day - b.day || a.name.localeCompare(b.name) || String(a.memberid).localeCompare(String(b.memberid)));
  }
  return [month, next].map((value) => ({
    month: value,
    label: MONTHS[value - 1],
    people: people(value),
  }));
}
