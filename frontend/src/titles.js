export const OFFICER_TITLES = [
  ["Grand Knight", "GK"],
  ["Deputy Grand Knight", "DGK"],
  ["Chancellor", "CH"],
  ["Chaplain", "CHP"],
  ["Recorder", "REC"],
  ["Financial Secretary", "FS"],
  ["Treasurer", "TR"],
  ["Advocate", "ADV"],
  ["Warden", "WRD"],
  ["Inside Guard", "IG"],
  ["Outside Guard", "OG"],
  ["Lecturer", "LEC"],
  ["Trustee 1-Year", "T1"],
  ["Trustee 2-Year", "T2"],
  ["Trustee 3-Year", "T3"],
  ["Program Director", "PD"],
  ["Membership Director", "MD"],
  ["Faith Director", "FD"],
  ["Family Director", "FAM"],
  ["Community Director", "COM"],
  ["Life Director", "LIFE"],
  ["Vocations Director", "VOC"],
  ["Past Grand Knight", "PGK"],
];

export const OFFICER_ROLES = [
  ["Chaplain", "CHP"],
  ["Grand Knight", "GK"],
  ["Deputy Grand Knight", "DGK"],
  ["Chancellor", "CH"],
  ["Recorder", "REC"],
  ["Financial Secretary", "FS"],
  ["Treasurer", "TR"],
  ["Lecturer", "LEC"],
  ["Advocate", "ADV"],
  ["Warden", "WRD"],
  ["Inside Guard", "IG"],
  ["Outside Guard", "OG"],
  ["Trustee, 3rd year", "T3"],
  ["Trustee, 2nd year", "T2"],
  ["Trustee, 1st year", "T1"],
];

export const DIRECTOR_ROLES = [
  ["Program Director", "PD"],
  ["Faith Director", "FD"],
  ["Family Director", "FAM"],
  ["Community Director", "COM"],
  ["Life Director", "LIFE"],
  ["Membership Director", "MD"],
];

export function memberLabel(user) {
  const name = (user && String(user.display_name || "").trim()) || "Member";
  const title = user && user.title ? String(user.title).trim() : "";
  return title ? `${title} ${name}` : name;
}
