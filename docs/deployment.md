# Production Deployment Notes

## Authoritative Configuration

- `docker-compose.yml` is the only production Compose file.
- Caddy owns `api.blueashdigital.tech` on the VPS.
- Hostinger's managed frontend owns `blueashdigital.tech` and `www.blueashdigital.tech`.
- The public site and portal frontend architecture, including what is still pending before a live website deploy, is in [website.md](website.md).
- As of 22 September 2026 the live Hostinger frontend is Node.js deployment `01a0cc01-5cef-7369-bdfa-8b1f50fc9544` of commit `02097001ca7fa4c60a75b63cc2db13ab0e406723`. Git auto-deployment is enabled for `main`, so a push to `origin/main` starts another frontend build. Rolling back the frontend means redeploying commit `f31acdfbd39b9abf673d24ee026ebeb7e6628887` (deployment `01a05481-ce71-7008-9732-5de55fc03d93`) through the existing Hostinger Node.js deployment. Do not change the API image, database, Agent, or TV app as part of a website deploy. A signed-out sign-in screen no longer waits on an unbounded session probe; see [website.md](website.md).
- `DEPLOYMENT_VERSION` is required and must be the full approved release commit SHA.
- `SOURCE_VERSION` is deprecated and ignored.
- No `traefik-public` network is required.

Use `.env.example` only as a variable checklist. Keep all real secret values in Hostinger's project environment and outside Git.

## Production API reachability (22 September 2026)

The public website deploy did not change DNS, Caddy, the VPS, Compose, the API image, the database, or mail. `https://api.blueashdigital.tech/api/health` failed because the `api` A record pointed at `174.16.206.226` instead of the VPS. On 22 September 2026 that one A record was set back to `31.220.58.251` with `overwrite: true` for name `api` and type `A` only. Nothing else in the zone was changed, and no service was restarted.

Expected path:

```text
browser -> api.blueashdigital.tech -> A record -> Hostinger VPS 31.220.58.251
-> Caddy (blueashdigital-tech-caddy-1, ports 80 and 443)
-> backend:8000 (blueashdigital-tech-backend-1)
-> PostgreSQL on the Compose network only (blueashdigital-tech-postgres-1, port 5432)
```

`/api/health` does not query PostgreSQL or SMTP. Production Compose does not set `SMTP_HOST`. The live files are `/docker/blueashdigital-tech/docker-compose.yml` and `/docker/blueashdigital-tech/Caddyfile`. Caddy proxies `api.blueashdigital.tech` to `backend:8000`.

Checked the same evening, with no restarts and no DNS edit:

| Layer | Result |
|---|---|
| Backend container | Healthy since 30 August 2026, image `c2e75549702ac8a511eca9df87f8a6838d9eec33`, 0 restarts |
| Inside the backend container | HTTP 200 `{"status":"ok","service":"blueash-portal-backend"}` |
| Caddy on the VPS | HTTP 200 for the same URL on `127.0.0.1:443` |
| Public hostname | DNS A `174.16.206.226`. TCP 443 and 80 time out before TLS. No AAAA record |
| Forced connection to `31.220.58.251` | HTTP 200 through Caddy. Certificate `CN=api.blueashdigital.tech`, Let's Encrypt, 23 August 2026 through 21 November 2026 |

PostgreSQL accepts connections. The VPS has been up since 23 August 2026. Host firewall `ufw` is inactive, and the Hostinger firewall group is unset. Ports 80 and 443 on `31.220.58.251` accept TCP.

DNS history for the `api` A record:

- 28 August 2026 and 5 September 2026 13:40 UTC: `31.220.58.251` (snapshot `178362051`)
- 5 September 2026 17:00 UTC: `174.29.193.100` (snapshot `178398432`)
- 12 September 2026: `97.118.224.208` (snapshot `180180679`)
- 22 September 2026: `174.16.206.226`, which does not accept TCP 22, 80, or 443

`radar` and `lab` still point at `174.16.206.226`. Restoring snapshot `180180679` would roll the whole zone backward, so that snapshot is not the repair. To undo only this change, set the `api` A record back to `174.16.206.226`.

After the update, authoritative DNS and public resolvers `1.1.1.1` and `8.8.8.8` returned `31.220.58.251`. `https://api.blueashdigital.tech/api/health` returned HTTP 200 in about 156 ms. On `https://blueashdigital.tech/signin`, `GET /api/profile/me` finished in about 357 ms and left the signed-out form in place. One unknown sign-in returned “Invalid username/email or password.” in about 871 ms and re-enabled Sign In. An unknown forgot-password request reached `/api/auth/password-reset/request` in about 151 ms and returned the generic account message. No production password was changed. A valid production sign-in, MFA, and a completed password reset were not run because no authorized test account was used.

## Phase 3 Migration (Not Yet Authorized For Production)

The locally validated application-auth transition is:

```text
20260825_0005 -> 20260827_0006
```

Do not apply `20260827_0006` until Opportunity Radar is deployed and verified directly at
`https://radar.blueashdigital.tech/`. The eventual order is Radar deployment, direct verification,
Portal release preparation and PostgreSQL backup, `0006` upgrade, then Launch verification. Do not
stamp or modify the production revision during release preparation.

## Application Authentication Secrets And Cookies

Set `OPPORTUNITY_RADAR_CLIENT_ID=opportunity-radar` and provision the same strong, independently
generated `OPPORTUNITY_RADAR_CLIENT_SECRET` in the Portal and Radar server environments. Never put
the real value in Git or frontend build variables.

Production Portal auth cookies use the `__Host-` prefix, Secure, HttpOnly, SameSite=Lax, Path=/, and
no Domain attribute. The first deployment invalidates the old `blueash_session` and
`blueash_pre_auth` parent-domain cookies on ordinary API responses. Existing sessions will therefore
receive a deliberate one-time logout; announce this before rollout. Remove the transitional legacy
cookie-expiry middleware only in a later reviewed release after old cookies can no longer exist.

## Email Secret Encryption

Gmail App Passwords are encrypted before they are stored in PostgreSQL.

Set this environment variable on the Hostinger Docker project during the authorized production credential change:

```text
EMAIL_ENCRYPTION_KEY=<long random secret>
```

Keep this value outside PostgreSQL and outside Git. If it is changed after email settings are saved, the stored Gmail App Password cannot be decrypted and must be replaced from Admin > Settings > Email.

For local development, the backend falls back to `SECRET_KEY` when `EMAIL_ENCRYPTION_KEY` is not set. Production Compose requires a dedicated value.

Local Compose can set `SMTP_HOST` to a development mailbox such as Mailpit. Production Compose does not set `SMTP_HOST`, and the backend refuses to start in production if that variable is present. Do not point production SMTP at a local catcher.

If email credentials were encrypted before `EMAIL_ENCRYPTION_KEY` was configured, they were encrypted with `SECRET_KEY`. Preserve the old key long enough to re-enter and test the email credentials under the new dedicated key; do not rotate both blindly.
