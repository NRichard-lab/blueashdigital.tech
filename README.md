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

The backend sends Secure, HttpOnly, SameSite=Lax, host-only `__Host-` cookies for
`api.blueashdigital.tech`; it does not share the Portal bearer session with sibling subdomains.
The first release using this policy intentionally expires the legacy `.blueashdigital.tech`
cookies on every API response, so users will perform a one-time sign-in after deployment.

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

Migration `20260825_0005` originally registered Opportunity Radar. The new forward migration
`20260827_0006` prepares its future production registry values without modifying the applied `0005`:

```text
launch_url=https://radar.blueashdigital.tech/
health_check_url=https://radar.blueashdigital.tech/api/health
internal_service_url=NULL
status=UNKNOWN
```

Portal-to-Radar authentication uses a 60-second, opaque, hash-only, one-time authorization code with
S256 PKCE. Radar exchanges it server-to-server using its configured client credentials. The Portal
then issues a hash-only, app-scoped session with a 30-minute idle timeout and an absolute expiration
bounded by the parent Portal session. Exchange, introspection, and revoke endpoints are under
`/api/app-auth`; raw codes, tokens, Portal cookies, and client secrets are never audit metadata.

Every user, including an administrator, needs an explicit `user_applications` assignment for this
handoff. Administrators retain the existing dashboard behavior that displays every enabled app.
Portal login `returnTo` accepts only the exact Radar HTTPS origin and non-`/api` UI paths, and the
server persists the normalized destination through email MFA.

Run one bounded cleanup batch from a scheduler with:

```bash
python -m app.cli.cleanup_application_auth --batch-size 500
```

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

### Phase 3 migration (local validation only)

The Phase 3 database transition is:

```text
20260825_0005 -> 20260827_0006
```

Do not apply `20260827_0006` to production during Phase 3. The future rollout order is: deploy and
verify Radar directly, prepare the Portal release and backup PostgreSQL, apply `0006`, then verify
Portal Launch. Production must provide an independently generated
`OPPORTUNITY_RADAR_CLIENT_SECRET` of at least 32 characters to both backends outside Git.

