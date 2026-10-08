import logo from "../../../uknight/images/CouncilSite_about.asp/logo-kofc-r.png";
import slideGathering from "../../../uknight/images/CouncilSite_photo-galleries.asp/c10930_PG_P_20250710_185821.jpg";
import slideService from "../../../uknight/images/CouncilSite_photo-galleries.asp/IMG_0147.jpg";
import slideFellowship from "../../../uknight/images/CouncilSite_photo-galleries.asp/DALvCOL0764.jpg";
import slideCharity from "../../../uknight/images/CouncilSite_photo-galleries.asp/c10930_PG_P_IMG_20251105_202614.jpg";

/**
 * Static Guest View copy. mockup.html points at ./images/kofc-logo.png and
 * ./images/carousel1.jpg–carousel4.jpg, which are not in this repo. These
 * council files keep the same roles, alt text, and layout.
 */
export const logoSrc = logo;

export const navLinks = [
  { href: "#who", label: "Who We Are" },
  { href: "#what", label: "What We Do" },
  { href: "#why", label: "Why Join" },
  { href: "#join", label: "Join Us" },
] as const;

export const carouselSlides = [
  { src: slideGathering, alt: "Council 10930 gathering" },
  { src: slideService, alt: "Knights of Columbus service" },
  { src: slideFellowship, alt: "Council 10930 fellowship" },
  { src: slideCharity, alt: "Charity in action" },
] as const;

export const whoWeAre = {
  eyebrow: "Our Brotherhood",
  title: "Who We Are",
  intro:
    "We are a council of practicing Catholic men, bound together by faith and by a shared duty to our parish, our families, and our neighbors.",
  panels: [
    {
      title: "Our Mission",
      body: "We live out the Order’s founding principles — charity, unity, fraternity, and patriotism — through prayer, service, and fellowship rooted in the Catholic faith.",
    },
    {
      title: "Our Parish",
      body: "We stand behind our parish in ways both visible and quiet: staffing ministries, funding needs, and showing up wherever the work is.",
    },
    {
      title: "Our Members",
      body: "We are fathers, husbands, tradesmen, and professionals — ordinary men trying, together, to live our faith a little better each day.",
    },
  ],
} as const;

export const legacyItems = [
  {
    year: "1882",
    body: "Father Michael J. McGivney founds the Knights of Columbus in New Haven, Connecticut, to support Catholic families in need.",
  },
  {
    year: "1900s",
    body: "The Order spreads across the country, chartering councils in parishes that needed a brotherhood of service.",
  },
  {
    year: "Today",
    body: "Council 10930 carries that same charter forward here in Fort Worth, one meeting and one act of charity at a time.",
  },
] as const;

export const whatWeDo = {
  eyebrow: "In Practice",
  title: "What We Do",
  intro:
    "Faith, family, community, and youth — the four pillars our council builds its year around.",
  panels: [
    {
      title: "Faith",
      icon: "icon-rosary",
      body: "Rosary devotions, Holy Hours, and retreats that keep prayer at the center of our brotherhood.",
    },
    {
      title: "Family",
      icon: "icon-family",
      body: "Gatherings and ministries — from Christmas baskets to family rosary nights — that support our households.",
    },
    {
      title: "Community",
      icon: "icon-charity",
      body: "Food drives, Coats for Kids, and support for Special Olympics athletes across our community.",
    },
    {
      title: "Youth",
      icon: "icon-youth",
      body: "Scholarships, mentorship, and support for seminarians discerning a vocation to the priesthood.",
    },
  ],
} as const;

export const whyJoin = {
  eyebrow: "The Case for Joining",
  title: "Why Join",
  intro: "Membership asks something of you — and gives back more than most men expect.",
  panels: [
    {
      title: "Grow in Faith",
      body: "Deepen your relationship with Christ alongside men pursuing the same thing.",
    },
    {
      title: "Serve Your Community",
      body: "Put your time toward charity that has a visible, lasting impact nearby.",
    },
    {
      title: "Build Brotherhood",
      body: "Form the kind of friendships that hold up under real life.",
    },
    {
      title: "Lead & Inspire",
      body: "Take on leadership within the council — and carry it home to your family.",
    },
  ],
} as const;

export const pageTitle =
  "Knights of Columbus — Council 10930 — Fort Worth, TX";
