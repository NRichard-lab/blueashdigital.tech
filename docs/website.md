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
- Email MFA is restyled inside the existing sign-in card. A live MFA challenge was not exercised.

### Deferred

- Formal privacy policy.
- Formal terms of use.
- Product documentation. The support page says it will be published when a product is available.
- A dark marketing theme. The approved design is the light Figma palette.
- Remember-me and public registration.

### Pending before a live website deploy

- Signed-in browser checks for `/signin` and `/forgot-password` redirecting to `/portal`.
- Successful username login, successful email login, incorrect credentials against a responding API, MFA challenge, incorrect MFA code, and successful MFA completion.
- Invalid, expired, and valid password-reset completion. A missing token is already handled in the page and does not call the API.
- The production API did not accept a connection from this environment. Docker CLI is installed, but the Docker Desktop engine pipe `dockerDesktopLinuxEngine` is not running, so the isolated stack could not be started. No production infrastructure was changed to work around that.
- A separate authorization to deploy. This document does not authorize one.

The live rollback source remains `f31acdfbd39b9abf673d24ee026ebeb7e6628887`. The previous local candidate was `d183155f610a25a21010b597e49cac2369701868`. The session-probe change on `main` is the current local candidate and is not deployed.

### Current production

Checked read-only on 22 September 2026. Nothing was deployed.

- Live frontend: Hostinger Node.js site for `blueashdigital.tech`, username `u832905293`, order `1009908557`.
- Build settings: Node 22, Vite, root directory `frontend`, output `dist`, npm, build script `build`.
- Latest completed deployment: `01a05481-ce71-7008-9732-5de55fc03d93`, git commit `f31acdfbd39b9abf673d24ee026ebeb7e6628887`, updated 30 August 2026.
- The live homepage title was still “Blue Ash Digital Portal”.
- `https://blueashdigital.tech/signin` returned HTTP 200 HTML, which is the existing SPA fallback.
- `docker-compose.yml` pins a frontend image at `9eb0da3b0c5c6fa12c127d6d7348e20b9b3c6108`. Caddy publishes the API, not the apex site. A website deploy must not replace that image, the API, the database, the Agent, or the TV app.

The local production bundle after the session-probe change was CSS 25.83 kB (6.20 kB gzip) and JS 269.54 kB (79.42 kB gzip). No project lint configuration exists; TypeScript checking is the `tsc -b` step inside `npm run build`. Frontend tests: 29 passed.

## Next step

Start the isolated local stack, or another non-production API, and complete the pending signed-in, MFA, and password-reset checks. Do not deploy the Hostinger frontend until those checks pass and a separate deployment approval is given. The rollback source until then remains commit `f31acdfbd39b9abf673d24ee026ebeb7e6628887`.
