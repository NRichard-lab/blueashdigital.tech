# Production Deployment Notes

## Authoritative Configuration

- `docker-compose.yml` is the only production Compose file.
- Caddy owns `api.blueashdigital.tech` on the VPS.
- Hostinger's managed frontend owns `blueashdigital.tech` and `www.blueashdigital.tech`.
- `DEPLOYMENT_VERSION` is required and must be the full approved release commit SHA.
- `SOURCE_VERSION` is deprecated and ignored.
- No `traefik-public` network is required.

Use `.env.example` only as a variable checklist. Keep all real secret values in Hostinger's project environment and outside Git.

## Release Migration

The only expected migration for the Opportunity Radar release is:

```text
20260823_0004 -> 20260825_0005
```

Verify production's `alembic_version` and take a restorable PostgreSQL backup before authorizing the upgrade. Do not stamp or modify the production revision during release preparation.

## Email Secret Encryption

Gmail App Passwords are encrypted before they are stored in PostgreSQL.

Set this environment variable on the Hostinger Docker project during the authorized production credential change:

```text
EMAIL_ENCRYPTION_KEY=<long random secret>
```

Keep this value outside PostgreSQL and outside Git. If it is changed after email settings are saved, the stored Gmail App Password cannot be decrypted and must be replaced from Admin > Settings > Email.

For local development, the backend falls back to `SECRET_KEY` when `EMAIL_ENCRYPTION_KEY` is not set. Production Compose requires a dedicated value.

If email credentials were encrypted before `EMAIL_ENCRYPTION_KEY` was configured, they were encrypted with `SECRET_KEY`. Preserve the old key long enough to re-enter and test the email credentials under the new dedicated key; do not rotate both blindly.
