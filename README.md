# Blue Ash Digital Portal

Production-ready private application portal for `blueashdigital.tech`.

This repo contains a React/Vite frontend, FastAPI backend, PostgreSQL database, Docker Compose deployment files, Alembic migrations, and Caddy routing for a Hostinger VPS running Ubuntu 24.04.

## What This Is

Blue Ash Digital is a secure login and launcher for custom applications. Users do not self-register. Administrators create accounts, assign application access, and manage the application registry.

Core capabilities included:

- Username or email sign-in
- Argon2id password hashing
- Secure HTTP-only server session cookies
- Role-based authorization
- User administration
- Application registry and user/application permissions
- Dashboard with search and category filtering
- Audit logging
- TOTP MFA foundation
- Email password-reset token flow foundation
- Docker, PostgreSQL, Alembic, and Caddy support

## Local Development

1. Copy the local-only environment template:

```bash
cp .env.local.example .env
cp frontend/.env.example frontend/.env.local
```

2. Start the stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build postgres backend frontend
```

3. Run database migrations:

```bash
docker compose exec backend alembic upgrade head
```

4. Create the first administrator:

```bash
docker compose exec backend python -m app.cli.create_admin \
  --username admin \
  --email you@blueashdigital.tech \
  --display-name "Portal Administrator"
```

You will be prompted for a password. Do not use a default password in production.

5. Open:

- Frontend: `http://localhost:8080`
- API health: `http://localhost:8000/api/health`
- API docs, local only: `http://localhost:8000/docs`

## Production Architecture On Hostinger

Target server:

- Ubuntu 24.04
- Docker
- Docker Compose plugin
- Caddy reverse proxy for the API
- PostgreSQL on the private Compose network
- Managed Hostinger frontend for the apex and `www` domains

Production ownership is intentionally split:

```text
blueashdigital.tech      -> Hostinger managed frontend
www.blueashdigital.tech  -> Hostinger managed frontend
api.blueashdigital.tech  -> Hostinger VPS Caddy
```

The authoritative VPS configuration is the root `docker-compose.yml`. It uses Caddy and does not require a Traefik network. The obsolete Traefik Compose file has been removed to prevent accidental use.

Recommended VPS directory:

```text
/srv/apps/portal
```

Prepare the production environment outside Git using `.env.example` as a variable checklist. Secret values in that template are intentionally blank. `DEPLOYMENT_VERSION` must be the full approved release commit SHA and is used for both backend and frontend image tags and revision labels.

Validate before an authorized deployment:

```bash
docker compose --env-file .env -f docker-compose.yml config --quiet
docker compose --env-file .env -f docker-compose.yml build
```

Production must provide strong generated values for `SECRET_KEY`, `SESSION_SECRET`, `EMAIL_ENCRYPTION_KEY`, and `POSTGRES_PASSWORD`. `SOURCE_VERSION` is deprecated and ignored.

## Caddy And CORS

Caddy on the VPS serves only `api.blueashdigital.tech`. It does not request certificates for the apex or `www` domains because those domains terminate at Hostinger's managed frontend.

The backend allows these production browser origins explicitly:

```text
https://blueashdigital.tech
https://www.blueashdigital.tech
```

The backend sends secure cookies for `.blueashdigital.tech` in production. Keep both frontend origins and the API on HTTPS.

## Backups

Back up at minimum:

- PostgreSQL database dump
- `/srv/apps/portal/docker-compose.yml`
- `/srv/apps/portal/Caddyfile`
- `/srv/apps/portal/.env`
- Any uploaded configuration or application-specific compose files

Example database backup:

```bash
docker compose -f docker-compose.yml exec -T postgres pg_dump -U portal portal \
  > /srv/backups/portal-$(date +%F).sql
```

Do not keep the only backup inside the database container.

## Application Model

The portal is intentionally separate from future apps:

```text
/srv/apps/
  portal/
  job-radar/
  utilities/
  automation/
```

Register each future app in Admin > Applications, assign users, and launch it from the dashboard.

### Opportunity Radar

Migration `20260825_0005` registers Opportunity Radar in the existing application registry with slug
`opportunity-radar` and launch URL `https://blueashdigital.tech/OpportunityRadar`. Administrators see
the enabled application automatically. Standard users see and may launch it only when its existing
`user_applications` assignment is enabled in User Administration.

Opportunity Radar redirects signed-out users to the portal with a `returnTo` query value. The login
flow accepts only the canonical `/OpportunityRadar` path and its descendants on `blueashdigital.tech`,
normalizes the destination to a relative path, preserves it through email MFA, and restores it after
authentication. Invalid or external destinations are ignored and normal portal navigation is used.

## Development Notes

- Backend source is under `backend/app`.
- Frontend source is under `frontend/src`.
- Database migrations are under `backend/migrations`.
- Never commit `.env`.
- API secrets stay server-side.
- PostgreSQL is internal-only in production.

### Hostinger deployment versioning

The Hostinger Docker project requires `DEPLOYMENT_VERSION` as the immutable backend and frontend
image tag and OCI revision label. Set it to the full approved release commit SHA for every
deployment. There is no fallback tag, so a missing release revision fails Compose validation
instead of silently reusing an older image. `SOURCE_VERSION` is deprecated and ignored.

### Migration for this release

The only expected database transition is:

```text
20260823_0004 -> 20260825_0005
```

Migration `20260825_0005` registers Opportunity Radar. Do not run it until the production database
has been backed up and the current `alembic_version` has been verified as `20260823_0004`.

