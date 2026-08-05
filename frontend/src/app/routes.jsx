import { createBrowserRouter } from "react-router-dom";

// Layouts
import PublicLayout from "../components/layout/PublicLayout";
import MemberLayout from "../components/layout/MemberLayout";
import AdminLayout from "../components/layout/AdminLayout";

// Guards
import RequireAuth from "../features/auth/components/RequireAuth";
import RequireRole from "../features/auth/components/RequireRole";

// PUBLIC PAGES
import Home from "../features/public/home/Home";
import About from "../features/public/about/About";
import Assemblies from "../features/public/about/Assemblies";
import WhyJoin from "../features/public/about/WhyJoin";

import NewsList from "../features/public/news/NewsList";
import NewsDetail from "../features/public/news/NewsDetail";

import Recognition from "../features/public/recognition/Recognition";
import InMemoriam from "../features/public/memoriam/InMemoriam";

import EventsList from "../features/public/events/EventsList";
import EventDetail from "../features/public/events/EventDetail";

import Officers from "../features/public/leadership/Officers";
import PastGrandKnights from "../features/public/leadership/PastGrandKnights";
import Directors from "../features/public/leadership/Directors";
import DirectorDetail from "../features/public/leadership/DirectorDetail";

import Programs from "../features/public/programs/Programs";
import FaithPrograms from "../features/public/programs/FaithPrograms";
import FamilyPrograms from "../features/public/programs/FamilyPrograms";
import CommunityPrograms from "../features/public/programs/CommunityPrograms";
import YouthPrograms from "../features/public/programs/YouthPrograms";
import FraternalPrograms from "../features/public/programs/FraternalPrograms";

import Prayers from "../features/public/prayer/Prayers";
import PrayersPrint from "../features/public/prayer/PrayersPrint";
import PrayerRequest from "../features/public/prayer/PrayerRequest";
import PrayerRequestGuest from "../features/public/prayer/PrayerRequestGuest";

import PhotoGalleries from "../features/public/media/PhotoGalleries";
import PhotoAlbum from "../features/public/media/PhotoAlbum";
import Newsletters from "../features/public/media/Newsletters";

import MarketHome from "../features/public/market/MarketHome";
import MarketCategory from "../features/public/market/MarketCategory";

import JobCenter from "../features/public/jobs/JobCenter";
import DegreeSchedule from "../features/public/degree/DegreeSchedule";

// MEMBER PAGES
import MemberDashboard from "../features/member/dashboard/MemberDashboard";
import MemberProfile from "../features/member/profile/MemberProfile";
import MemberDocuments from "../features/member/documents/MemberDocuments";
import MemberAnnouncements from "../features/member/announcements/MemberAnnouncements";
import MemberCalendar from "../features/member/calendar/MemberCalendar";

import MemberEvents from "../features/member/events/MemberEvents";
import MemberEventDetail from "../features/member/events/MemberEventDetail";
import VolunteerSignup from "../features/member/events/VolunteerSignup";
import VolunteerHours from "../features/member/events/VolunteerHours";

import MemberPrograms from "../features/member/programs/MemberPrograms";
import CommitteeDetail from "../features/member/programs/CommitteeDetail";
import ProgramDetail from "../features/member/programs/ProgramDetail";
import ProgramVolunteer from "../features/member/programs/ProgramVolunteer";

import MemberOfficers from "../features/member/leadership/MemberOfficers";
import MemberDirectors from "../features/member/leadership/MemberDirectors";
import MemberAssemblies from "../features/member/leadership/MemberAssemblies";

import MemberMarket from "../features/member/market/MemberMarket";
import MemberMarketCategory from "../features/member/market/MemberMarketCategory";
import MerchantLogin from "../features/member/market/MerchantLogin";
import MerchantReports from "../features/member/market/MerchantReports";

import Voting from "../features/member/voting/Voting";
import VotingMonth from "../features/member/voting/VotingMonth";

// ADMIN PAGES
import AdminDashboard from "../features/admin/dashboard/AdminDashboard";
import SystemStatus from "../features/admin/dashboard/SystemStatus";
import AuditLog from "../features/admin/dashboard/AuditLog";

import AdminHomepage from "../features/admin/content/AdminHomepage";
import AdminAbout from "../features/admin/content/AdminAbout";
import AdminNews from "../features/admin/content/AdminNews";
import AdminRecognition from "../features/admin/content/AdminRecognition";
import AdminMemoriam from "../features/admin/content/AdminMemoriam";
import AdminLinks from "../features/admin/content/AdminLinks";

import AdminEvents from "../features/admin/events/AdminEvents";
import AdminEventCreate from "../features/admin/events/AdminEventCreate";
import AdminEventEdit from "../features/admin/events/AdminEventEdit";

import AdminOfficers from "../features/admin/leadership/AdminOfficers";
import AdminDirectors from "../features/admin/leadership/AdminDirectors";
import AdminAssemblies from "../features/admin/leadership/AdminAssemblies";

import AdminPrograms from "../features/admin/programs/AdminPrograms";
import AdminCommitteeEdit from "../features/admin/programs/AdminCommitteeEdit";
import AdminProgramEdit from "../features/admin/programs/AdminProgramEdit";

import AdminPhotos from "../features/admin/media/AdminPhotos";
import AdminPhotoUpload from "../features/admin/media/AdminPhotoUpload";
import AdminPhotoEdit from "../features/admin/media/AdminPhotoEdit";
import AdminNewsletters from "../features/admin/media/AdminNewsletters";
import AdminVideos from "../features/admin/media/AdminVideos";
import AdminSlideshow from "../features/admin/media/AdminSlideshow";

import AdminMembers from "../features/admin/members/AdminMembers";
import AdminMemberImport from "../features/admin/members/AdminMemberImport";
import AdminMemberDues from "../features/admin/members/AdminMemberDues";
import AdminMemberOverdue from "../features/admin/members/AdminMemberOverdue";
import AdminVotingTotals from "../features/admin/members/AdminVotingTotals";
import AdminMemberReports from "../features/admin/members/AdminMemberReports";

import AdminDocuments from "../features/admin/documents/AdminDocuments";
import AdminPublicDocuments from "../features/admin/documents/AdminPublicDocuments";
import AdminMemberDocuments from "../features/admin/documents/AdminMemberDocuments";

import AdminEmailCenter from "../features/admin/communications/AdminEmailCenter";
import AdminEmailTemplates from "../features/admin/communications/AdminEmailTemplates";
import AdminEmailRemoval from "../features/admin/communications/AdminEmailRemoval";
import AdminQrCodes from "../features/admin/communications/AdminQrCodes";

import AdminMarket from "../features/admin/market/AdminMarket";
import AdminMarketReports from "../features/admin/market/AdminMarketReports";
import AdminMarketPasswordReset from "../features/admin/market/AdminMarketPasswordReset";

import WebmasterDashboard from "../features/admin/webmaster/WebmasterDashboard";
import WebmasterSEO from "../features/admin/webmaster/WebmasterSEO";
import WebmasterUploads from "../features/admin/webmaster/WebmasterUploads";
import WebmasterSettings from "../features/admin/webmaster/WebmasterSettings";

import AdminBylaws from "../features/admin/governance/AdminBylaws";
import AdminMinutes from "../features/admin/governance/AdminMinutes";
import AdminMeetingSchedule from "../features/admin/governance/AdminMeetingSchedule";
import AdminBudget from "../features/admin/governance/AdminBudget";
import AdminRoundtable from "../features/admin/governance/AdminRoundtable";


const router = createBrowserRouter([
  // PUBLIC ROUTES
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: "about", element: <About /> },
      { path: "assemblies", element: <Assemblies /> },
      { path: "why-join", element: <WhyJoin /> },

      { path: "news", element: <NewsList /> },
      { path: "news/:id", element: <NewsDetail /> },

      { path: "recognition", element: <Recognition /> },
      { path: "memoriam", element: <InMemoriam /> },

      { path: "events", element: <EventsList /> },
      { path: "events/:id", element: <EventDetail /> },

      { path: "officers", element: <Officers /> },
      { path: "past-grand-knights", element: <PastGrandKnights /> },
      { path: "directors", element: <Directors /> },
      { path: "directors/:id", element: <DirectorDetail /> },

      { path: "programs", element: <Programs /> },
      { path: "programs/faith", element: <FaithPrograms /> },
      { path: "programs/family", element: <FamilyPrograms /> },
      { path: "programs/community", element: <CommunityPrograms /> },
      { path: "programs/youth", element: <YouthPrograms /> },
      { path: "programs/fraternal", element: <FraternalPrograms /> },

      { path: "prayers", element: <Prayers /> },
      { path: "prayers/print", element: <PrayersPrint /> },
      { path: "prayer/request", element: <PrayerRequest /> },
      { path: "prayer/request/guest", element: <PrayerRequestGuest /> },

      { path: "media/photos", element: <PhotoGalleries /> },
      { path: "media/photos/:albumId", element: <PhotoAlbum /> },
      { path: "media/newsletters", element: <Newsletters /> },

      { path: "market", element: <MarketHome /> },
      { path: "market/category/:id", element: <MarketCategory /> },

      { path: "jobs", element: <JobCenter /> },
      { path: "degree-schedule", element: <DegreeSchedule /> },
    ],
  },

  // MEMBER ROUTES (AUTH REQUIRED)
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/member",
        element: <MemberLayout />,
        children: [
          { path: "dashboard", element: <MemberDashboard /> },
          { path: "profile", element: <MemberProfile /> },
          { path: "documents", element: <MemberDocuments /> },
          { path: "announcements", element: <MemberAnnouncements /> },
          { path: "calendar", element: <MemberCalendar /> },

          { path: "events", element: <MemberEvents /> },
          { path: "events/:id", element: <MemberEventDetail /> },
          { path: "events/:id/volunteer", element: <VolunteerSignup /> },
          { path: "events/:id/hours", element: <VolunteerHours /> },

          { path: "programs", element: <MemberPrograms /> },
          { path: "programs/:committeeId", element: <CommitteeDetail /> },
          { path: "programs/:committeeId/:programId", element: <ProgramDetail /> },
          { path: "programs/:programId/volunteer", element: <ProgramVolunteer /> },

          { path: "officers", element: <MemberOfficers /> },
          { path: "directors", element: <MemberDirectors /> },
          { path: "assemblies", element: <MemberAssemblies /> },

          { path: "market", element: <MemberMarket /> },
          { path: "market/category/:id", element: <MemberMarketCategory /> },
          { path: "market/login", element: <MerchantLogin /> },
          { path: "market/reports", element: <MerchantReports /> },

          { path: "voting", element: <Voting /> },
          { path: "voting/:year/:month", element: <VotingMonth /> },
        ],
      },
    ],
  },

  // ADMIN ROUTES (ADMIN ROLE REQUIRED)
  {
    element: <RequireRole role="admin" />,
    children: [
      {
        path: "/admin",
        element: <AdminLayout />,
        children: [
          { path: "dashboard", element: <AdminDashboard /> },
          { path: "system-status", element: <SystemStatus /> },
          { path: "audit-log", element: <AuditLog /> },

          { path: "homepage", element: <AdminHomepage /> },
          { path: "about", element: <AdminAbout /> },
          { path: "news", element: <AdminNews /> },
          { path: "recognition", element: <AdminRecognition /> },
          { path: "memoriam", element: <AdminMemoriam /> },
          { path: "links", element: <AdminLinks /> },

          { path: "events", element: <AdminEvents /> },
          { path: "events/create", element: <AdminEventCreate /> },
          { path: "events/:id", element: <AdminEventEdit /> },

          { path: "officers", element: <AdminOfficers /> },
          { path: "directors", element: <AdminDirectors /> },
          { path: "assemblies", element: <AdminAssemblies /> },

          { path: "programs", element: <AdminPrograms /> },
          { path: "programs/:committeeId", element: <AdminCommitteeEdit /> },
          { path: "programs/:committeeId/:programId", element: <AdminProgramEdit /> },

          { path: "photos", element: <AdminPhotos /> },
          { path: "photos/upload", element: <AdminPhotoUpload /> },
          { path: "photos/:albumId", element: <AdminPhotoEdit /> },
          { path: "newsletters", element: <AdminNewsletters /> },
          { path: "videos", element: <AdminVideos /> },
          { path: "slideshow", element: <AdminSlideshow /> },

          { path: "members", element: <AdminMembers /> },
          { path: "members/import", element: <AdminMemberImport /> },
          { path: "members/dues", element: <AdminMemberDues /> },
          { path: "members/overdue", element: <AdminMemberOverdue /> },
          { path: "members/voting-totals", element: <AdminVotingTotals /> },
          { path: "members/reports", element: <AdminMemberReports /> },

          { path: "documents", element: <AdminDocuments /> },
          { path: "documents/public", element: <AdminPublicDocuments /> },
          { path: "documents/member", element: <AdminMemberDocuments /> },

          { path: "email", element: <AdminEmailCenter /> },
          { path: "email/templates", element: <AdminEmailTemplates /> },
          { path: "email/remove", element: <AdminEmailRemoval /> },
          { path: "qr-codes", element: <AdminQrCodes /> },

          { path: "market", element: <AdminMarket /> },
          { path: "market/reports", element: <AdminMarketReports /> },
          { path: "market/password-reset", element: <AdminMarketPasswordReset /> },

          { path: "webmaster", element: <WebmasterDashboard /> },
          { path: "webmaster/seo", element: <WebmasterSEO /> },
          { path: "webmaster/uploads", element: <WebmasterUploads /> },
          { path: "webmaster/settings", element: <WebmasterSettings /> },

          { path: "governance/bylaws", element: <AdminBylaws /> },
          { path: "governance/minutes", element: <AdminMinutes /> },
          { path: "governance/meeting-schedule", element: <AdminMeetingSchedule /> },
          { path: "governance/budget", element: <AdminBudget /> },
          { path: "governance/roundtable", element: <AdminRoundtable /> },
        ],
      },
    ],
  },
]);

export default router;
