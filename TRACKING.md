# Site tracking

Optional tracking waits for Accept or Decline. Essential sign-in cookies stay on, and the banner does not ask about them. The choice (accepted or declined, version `1`, and the time) is stored in the `koc_consent` cookie and in `consent_choices`. Necessary events are stored either way. Accept events are stored only when the cookie says `accepted`.

Rows go into `audit_events` (event type, time, membership id when there is one, IP, a short browser/OS summary, and JSON details). If that write fails, the event is kept in a short in-memory list and the page request still finishes. Restart the API so an existing database creates the tables.

IP geolocation is not looked up. The stored IP is the request address only.

## Necessary

These are logged without consent:

- `auth.login_success` — successful sign-in
- `auth.login_failure` — failed sign-in, with the attempted membership id, not the password
- `auth.admin_login` — successful sign-in by an admin
- `auth.logout` — sign-out
- `session.start` — when a sign-in starts a session
- `session.end` — when that member signs out, with duration from the latest session start
- `consent.choice` — Accept or Decline, with version
- `security.login_burst` — 5, 10, 15… failed sign-ins from the same IP or the same attempted id within 15 minutes. The account is not locked.
- `security.admin_denied` — a signed-in non-admin, or a signed-out visitor, hits an admin-only route or a private library image
- `error.backend` — server error (status 500 or higher), with a short message and membership id when the access cookie is present
- `error.frontend` — browser error message and membership id when signed in
- `file.upload` — success or failure for a profile photo, honor photo, library document, or media-library image, with type, size when known, and record id
- `file.remove` — profile photo, honor photo, library document, or media-library image removed
- `admin.content_create`, `admin.content_update`, `admin.content_delete` — content blocks, members, birthdays, honors, events, documents, announcements, prayer requests, and media-library images. Details include the admin id, record id, and content type. Content-block values, announcement HTML, and prayer text are not copied.
- `admin.flag_change` — admin or webmaster flag granted or removed
- `admin.title_change` — officer or director title changes, including a title cleared from the previous holder

## Accept

These are logged only after Accept. Browser events also include language and timezone when the browser sends them.

- `page.view` — path
- `page.leave` — path and approximate seconds on that page (capped at one day)
- `ui.click` — Edit, Done, View more, View less, Read More..., Show less, library Open, library Download
- `search.query` — past-honors and both library searches, with the query and result count (`used` is false)
- `search.use` — a search result was opened, downloaded, or edited (`used` is true)
- `document.preview` — PDF Open in the Treasurer or Financial Secretary library
- `document.download` — non-PDF download in those libraries
- `feature.use` — profile photo upload, crop, or remove; event Read More...; birthday list opened

## Skipped

- MFA logging — the site has no MFA.
- Admin impersonation — there is no impersonation feature.
- Active or AFK time — idle detection is not recorded. Session duration is only from sign-in to sign-out.
- Heatmap click coordinates — clicks record the control name, not an x/y position.
- Email open or click tracking — the site does not send tracked mail.
- UTM or campaign tracking — public links are not campaign-tagged.
- Core Web Vitals — page speed metrics are not collected.
- Feature-flag experiments — there is no flag system.
- Real-time activity feed — events are stored, not shown as a live feed.
- Full database change audit — only the admin actions above are recorded, not every row write.
- Scheduled-job success summaries — there are no scheduled jobs.
- Password change — members cannot change a password in the app. Creating a member stores the new id and title, never the password.
- Account lockout and unlock — sign-in is not locked after failures. Repeated failures are counted in `security.login_burst` only.
- IP geolocation — no outside lookup. The IP address itself is stored on the event.

## Admin review

Webmasters open Settings and use Logs & activity. Administrators do not see that section, and `GET /api/audit/log` returns 403 for anyone who is not a webmaster. The summary above the list charts sign-ins, failed sign-ins, top event types, cookie choices, document downloads and opens, page views, and recent content changes. The list shows `audit_events` and `consent_choices` (accepted or declined, time, and version), newest first. Filters cover event type, date, and member. Search matches event type, member, and details text. The list is read-only. If Postgres is unavailable, that section shows a short notice and the rest of Settings still loads. Opening the log does not write a tracking event.
