import { useEffect } from "react";
import HeroSection from "../components/guest/HeroSection";
import JoinSection from "../components/guest/JoinSection";
import LegacyTimeline from "../components/guest/LegacyTimeline";
import PrinciplesBanner from "../components/guest/PrinciplesBanner";
import SvgSprite from "../components/guest/SvgSprite";
import WhatWeDo from "../components/guest/WhatWeDo";
import WhoWeAre from "../components/guest/WhoWeAre";
import WhyJoin from "../components/guest/WhyJoin";
import SiteFooter from "../components/layout/SiteFooter";
import SiteHeader from "../components/layout/SiteHeader";
import { pageTitle } from "../data/guestContent";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export default function GuestView() {
  useDocumentTitle(pageTitle);

  useEffect(() => {
    const hash = window.location.hash;
    if (hash.length < 2) return;
    const target = document.getElementById(decodeURIComponent(hash.slice(1)));
    target?.scrollIntoView();
  }, []);

  return (
    <>
      <SvgSprite />
      <SiteHeader />
      <main>
        <HeroSection />
        <WhoWeAre />
        <LegacyTimeline />
        <WhatWeDo />
        <PrinciplesBanner />
        <WhyJoin />
        <JoinSection />
      </main>
      <SiteFooter />
    </>
  );
}
