# Public Website

This document is the architecture record for the public Blue Ash Digital site. The application portal remains the signed-in product described in the README. There is no `AGENTS.md` in this repository.

The public site and the portal share one React/Vite frontend. They do not share one screen. `/` is the company homepage. `/portal` is the existing authenticated portal. Sign-in, MFA, password reset, sessions, and `returnTo` stay on the existing API helpers in `frontend/src/api.ts` and the existing allowlist in `frontend/src/returnTo.ts`.

## Route map

| Path | Screen |
|---|---|
| `/` | Marketing homepage |
| `/#products`, `/#about`, `/#building` | Homepage sections |
| `/products`, `/about`, `/development` | Aliases that open the homepage at those sections |
| `/products/blue-ash-reel` | Blue Ash Reel product page |
| `/support` | Support entry, including `#documentation` |
| `/privacy`, `/terms` | Notices that formal documents are not published |
| `/signin` | Existing sign-in and email MFA, restyled |
| `/forgot-password` | Existing reset request |
| `/reset-password` | Existing reset completion |
| `/portal` | Existing authenticated portal |
| Any other path | Not found |

Routes are resolved in `frontend/src/site/routes.ts`. Links are normal document navigations, so refresh, Back, and Forward use the browser history. Hostinger serves the built SPA with `frontend/public/.htaccess`, which Vite copies into `dist`. The Docker frontend image uses `frontend/nginx.conf` for the same fallback, but that image is not what serves the apex domain.

## Marketing, authentication, and portal

Public marketing routes render immediately and do not call the Portal API. `/signin`, `/forgot-password`, and `/reset-password` also render immediately. `GET /api/profile/me` still runs in the background on those auth routes, and on `/portal` and `/?returnTo=…`, with a 4 second abort (`SESSION_PROBE_TIMEOUT_MS`). A successful probe still redirects a signed-in visitor from `/signin` or `/forgot-password` to `/portal`, or follows an allowlisted `returnTo`. Timeout, offline, HTTP 401, HTTP 500, and a malformed response all fail closed: the visitor stays signed out, and the portal shell is not shown.

The earlier sign-in delay happened because auth screens waited for that probe, and the probe used `fetch` with no timeout. An unreachable `https://api.blueashdigital.tech` therefore held the boot screen until the browser connection timeout, about 16 seconds. The form is no longer behind that wait. A signed-in visitor may see the form briefly before the probe redirects them. That does not create a session.

Login, MFA verify, MFA resend, MFA cancel, forgot-password, and reset-password submissions use a separate 12 second client bound (`AUTH_REQUEST_TIMEOUT_MS`). That is longer than the session probe so a slow but healthy authentication response can still finish. If the request aborts or the network fails, the form leaves its pending state, the submit control is enabled again, and the page shows: “We couldn't reach Blue Ash Digital. Check your connection and try again.” That message is not the invalid-credentials message, and a timeout does not create a session. HTTP error text from the API, including “Invalid username/email or password.”, is unchanged.

`/portal` and a homepage `returnTo` stay gated on the probe so an unconfirmed session cannot see the portal or skip the allowlist. If the probe does not succeed within 4 seconds, those routes send the visitor to sign-in.

After that check:

- A valid session with an allowlisted `returnTo` continues only to that URL.
- A homepage `/?returnTo=…` without a session becomes `/signin?returnTo=…`.
- Login without `returnTo` goes to `/portal`.
- A signed-in visit to `/signin` or `/forgot-password` goes to `/portal`.
- A signed-out visit to `/portal` goes to `/signin`.
- `/reset-password` stays available even when a session exists, because a reset link must remain usable.
- A rejected `returnTo` is not followed. The sign-in screen keeps the normal account copy.
- A session-expiry message is stored in `sessionStorage` under `blueash-auth-notice` and shown once on sign-in.

`navigationAfterSessionCheck` is the shared decision used by the app and covered in `frontend/src/site/routes.test.ts`. `normalizeReturnTo` is unchanged.

The sign-in field label is “Username or email”. There is no public registration and no remember-me control. “Request development access” goes to `/support`. A reset link with no token shows an error and does not call the API.

## Products

Future products are added as entries in `frontend/src/site/products.ts`. The homepage card, footer, and product URL list read that catalog. Blue Ash Reel is the only entry. Its status is In Development. The required public description is:

> Your personal media, beautifully organized and ready to share, all in one place. Your library stays at home, with built-in privacy and only essential data collected.

Reel is not described as a streaming service. Device sections are labeled “Television concept” and “Browser / computer concept”.

## Figma deviations

- Remember-me is omitted because the API does not support it.
- The identifier field says “Username or email” because the API accepts both.
- An allowlisted `returnTo` uses “Continue” and “Sign in to continue to your application.”
- Development access links to `/support`.
- The active lifecycle label uses cream text on the blue pill for contrast.
- Privacy and terms are honest unpublished notices. Figma has no legal pages.
- The signed-in header and footer say Portal and link to `/portal`.

## Header, motion, and accessibility

The header is sticky. Section targets use `scroll-margin-top` so hash navigation lands below it. At widths of 980px and below, primary links collapse into a menu button. Opening the menu moves focus to the first link. Tab stays inside the menu and the button. Escape closes it and returns focus to the button. A wider viewport closes the menu.

Focus indicators use `:focus-visible`. The marketing palette is the fixed Figma cream and navy theme (`color-scheme: light`). It does not switch to a dark theme with the operating system. Tree drift and hover movement run only under `prefers-reduced-motion: no-preference`.

Decorative images have empty alt text. Library titles are adjacent text. Each marketing page has one `h1`.

## Assets

Images, marks, and fonts are in `frontend/public/brand` and `frontend/public/fonts`. Inter and Newsreader are self-hosted, preloaded, and use `font-display: swap`. There are no Figma or Google Fonts runtime requests.

## Release status

### Completed

- Company homepage, Reel page, support, privacy notice, terms notice, and not-found page.
- Sign-in, forgot-password, and reset-password presentation on the existing API helpers.
- Product catalog extension point.
- Route and `returnTo` regression tests.
- Production frontend build.

### Partial

- Signed-out routes, history, and `returnTo` rejection were checked in the browser against the local dev server while `https://api.blueashdigital.tech` was unreachable.
- Public pages made no Portal API requests and still rendered.
- `/signin` showed the form on first paint. Document load was about 85 ms. Forgot-password and reset-password also rendered immediately.
- With the API unreachable, `/portal` and `/?returnTo=…` reached sign-in in about 4.2 seconds instead of waiting for the browser connection timeout.
- The production build was previewed locally at `http://127.0.0.1:4174/`. Every listed route returned HTTP 200.
- Email MFA is restyled inside the existing sign-in card. The live challenge was completed later against the local mailbox, recorded below.

### Deferred

- Formal privacy policy.
- Formal terms of use.
- Product documentation. The support page says it will be published when a product is available.
- A dark marketing theme. The approved design is the light Figma palette.
- Remember-me and public registration.

### Authentication checks on the isolated local stack

Checked on 22 September 2026 against Docker Postgres and the local backend only. The frontend dev server used `http://localhost:8000`. No production account, DNS record, or Hostinger site was changed. The mailbox, MFA, and reset-email results are in the following sections. The two email-disabled outcomes below are from the pass before Mailpit was added.

- Email login and username login both opened `/portal`. Refresh kept the session.
- A signed-in visit to `/signin` or `/forgot-password` went to `/portal`. A signed-out visit to `/portal` went to `/signin`. No redirect loop.
- An incorrect password stayed on sign-in with “Invalid username/email or password.” and re-enabled Sign In. An unknown account returned the same API message. Empty required fields were blocked by the form before a request.
- With the API unreachable, login, forgot-password, and reset-password each returned to an enabled form in about 12 seconds with the unreachable message above. That message is distinct from the invalid-credentials message.
- Stopping the local API while a session already existed sent `/portal` back to sign-in. The portal shell was not left on screen. Starting the API again restored the existing local session.
- An invalid session cookie returned HTTP 401. An empty login body returned HTTP 422.
- `https://evil.example` kept the normal sign-in copy and, after a successful login, opened `/portal`. `https://radar.blueashdigital.tech/jobs` showed the continue copy. The local API origin is `https://radar.localhost`, so that production Radar URL was not returned and the session opened `/portal`. A return URL on the local origin, `https://radar.localhost/jobs`, was returned. Frontend tests still allow the production Radar origin and reject encoded external URLs, nested hosts, path traversal, and double encoding.
- Before the local mailbox existed, administrator login did not open a session. The form showed “Email service is currently disabled.” and Sign In was enabled again.
- Before the local mailbox existed, unknown forgot-password returned the generic account message and a known account returned “Email service is currently disabled.” Invalid and expired reset tokens were rejected. A valid local reset token completed, the previous password was then rejected, and the new password signed in. Password mismatch is rejected in the page before a request. A missing token disables submit and does not call the API.

### Local mailbox

Local Compose starts Mailpit and sets `SMTP_HOST=mailpit` on the backend only. The mailbox UI is `http://127.0.0.1:8025`. SMTP is `mailpit:1025` inside the Compose network, published on `127.0.0.1:1025`. The catcher does not deliver mail to the internet. Production Compose does not set `SMTP_HOST`, and production startup rejects that variable.

The application still uses the existing email service. On development startup, when `SMTP_HOST` is set, that service writes one enabled local mailbox row and sends through plain SMTP to the catcher. The sender used for these checks was `no-reply@localhost`.

To exercise an allowlisted local return, start the frontend with `VITE_API_BASE_URL=http://localhost:8000` and `VITE_RADAR_PUBLIC_ORIGIN=https://radar.localhost`. The local API allowlist origin is `https://radar.localhost`. Use an administrator account so MFA is required. Read the challenge from the local mailbox. Do not copy production mailbox credentials into this environment.

### MFA and password-reset email checks

Checked on 22 September 2026 against the isolated local stack and Mailpit. No production email setting, DNS record, Hostinger site, or production credential was changed.

- A development test message reached the local mailbox. The sender was `no-reply@localhost`, the recipient matched the requested address, and the HTML body rendered. Backend logs did not include mailbox passwords or message bodies.
- Administrator email login showed the MFA challenge and did not create a session. The profile request stayed unauthorized. The challenge email arrived in the local mailbox for the administrator address.
- A wrong code stayed on the challenge, showed “Invalid or expired verification code.”, re-enabled Verify, and left the profile request unauthorized.
- The matching code opened `/portal`. Refresh kept the session.
- Refresh during an open challenge returned the sign-in form and left the profile request unauthorized. A direct `/portal` visit during that challenge redirected to `/signin`. Back returned to `/signin` with the same unauthorized profile request. Forward returns to `/portal`, and that route redirects to `/signin` while the challenge is unfinished.
- Resend before the configured delay did not add a message. After the delay, resend added a new message and the previous code no longer matched the active challenge. The resend delay and existing rate limits were left unchanged.
- Cancel returned the sign-in form with no session. A following `/portal` visit redirected to `/signin`.
- After MFA, `https://radar.localhost/jobs` left the local site for that allowlisted URL. The Radar host is not running locally, so the browser showed a connection error instead of a Radar page. Returning to `/portal` still showed the authenticated session. `https://evil.example` stayed on the normal sign-in copy through the challenge and, after the correct code, opened `/portal`.
- An unknown password-reset request returned the generic account message and created no mailbox message. A known account returned the same message and the reset email arrived locally. A valid link completed the reset. The previous password was then rejected and the new password signed in. A long invalid token returned “Password reset link is invalid or expired.”
- With Mailpit stopped, administrator login, MFA resend, and a known-account reset each returned “Unable to send email.” within a few seconds. The submit controls were enabled again. None of those responses used the invalid-credentials message, and login did not open a session or a challenge. The 12 second client bound was not changed. Mailpit was started again after the check.

With the mailbox available, a known account and an unknown account both receive the generic reset response. A known account still receives “Unable to send email.” when delivery fails. That existing response was left in place.

### Still required before a live website deploy

A separate authorization to deploy. This document does not authorize one.

The live rollback source remains `f31acdfbd39b9abf673d24ee026ebeb7e6628887`. The previous local candidate was `888647533f4b393aac012b98b42c36a4757e1365`. The local mail verification on `main` is the current local candidate and is not deployed.

### Current production

Checked read-only on 22 September 2026. Nothing was deployed.

- Live frontend: Hostinger Node.js site for `blueashdigital.tech`, username `u832905293`, order `1009908557`.
- Build settings: Node 22, Vite, root directory `frontend`, output `dist`, npm, build script `build`.
- Latest completed deployment: `01a05481-ce71-7008-9732-5de55fc03d93`, git commit `f31acdfbd39b9abf673d24ee026ebeb7e6628887`, updated 30 August 2026.
- The live homepage title was still “Blue Ash Digital Portal”.
- `https://blueashdigital.tech/signin` returned HTTP 200 HTML, which is the existing SPA fallback.
- `docker-compose.yml` pins a frontend image at `9eb0da3b0c5c6fa12c127d6d7348e20b9b3c6108`. Caddy publishes the API, not the apex site. A website deploy must not replace that image, the API, the database, the Agent, or the TV app.

The local production bundle after the auth-request bound was CSS 25.83 kB (6.20 kB gzip) and JS 270.11 kB (79.56 kB gzip). No project lint configuration exists. TypeScript checking is the `tsc -b` step inside `npm run build`. Frontend tests: 33 passed.

## Next step

The public site and the local MFA checks are complete enough for a release decision. Deploying the Hostinger frontend still requires a separate approval. The rollback source until that approval is commit `f31acdfbd39b9abf673d24ee026ebeb7e6628887`. Remaining risk: production SMTP was not exercised, and the local Radar return was confirmed by navigation to `https://radar.localhost/jobs` rather than by a running Radar application.
