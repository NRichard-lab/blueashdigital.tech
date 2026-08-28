# Production Deployment Notes

## Authoritative Configuration

- `docker-compose.yml` is the only production Compose file.
- Caddy owns `api.blueashdigital.tech` on the VPS.
- Hostinger's managed frontend owns `blueashdigital.tech` and `www.blueashdigital.tech`.
- `DEPLOYMENT_VERSION` is required and must be the full approved release commit SHA.
- `SOURCE_VERSION` is deprecated and ignored.
- No `traefik-public` network is required.

Use `.env.example` only as a variable checklist. Keep all real secret values in Hostinger's project environment and outside Git.

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

If email credentials were encrypted before `EMAIL_ENCRYPTION_KEY` was configured, they were encrypted with `SECRET_KEY`. Preserve the old key long enough to re-enter and test the email credentials under the new dedicated key; do not rotate both blindly.
