# Blue Ash Digital Portal

Production-ready private application portal for `blueashdigital.tech`.

This repo contains a React/Vite frontend, FastAPI backend, PostgreSQL database, Docker Compose deployment files, Alembic migrations, and Traefik labels for a Hostinger VPS running Ubuntu 24.04.

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
- Docker, PostgreSQL, Alembic, and Traefik support

## Local Development

1. Copy environment files:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

2. Start the stack:

```bash
docker compose up --build
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

- Frontend: `http://localhost:5173`
- API health: `http://localhost:8000/api/health`
- API docs, local only: `http://localhost:8000/docs`

## Production Deployment On Hostinger VPS

Target server:

- Ubuntu 24.04
- Docker
- Docker Compose plugin
- Traefik reverse proxy
- DNS pointed to the VPS

Recommended DNS:

```text
blueashdigital.tech      A      <VPS_PUBLIC_IP>
www.blueashdigital.tech  CNAME  blueashdigital.tech
api.blueashdigital.tech  A      <VPS_PUBLIC_IP>
```

Recommended directory:

```text
/srv/apps/portal
```

Deploy:

```bash
cd /srv/apps/portal
cp .env.example .env
nano .env
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -m app.cli.create_admin \
  --username admin \
  --email you@blueashdigital.tech \
  --display-name "Portal Administrator"
```

Production `.env` must include strong generated values for `SECRET_KEY`, `SESSION_SECRET`, and `POSTGRES_PASSWORD`.

## Hostinger And Traefik

The production compose file expects an external Docker network named `traefik-public`.

Create it once if needed:

```bash
docker network create traefik-public
```

Traefik routes:

- `https://blueashdigital.tech` -> frontend
- `https://www.blueashdigital.tech` -> frontend
- `https://api.blueashdigital.tech` -> backend

The backend sends secure cookies for `.blueashdigital.tech` in production. Keep frontend and API on HTTPS.

## Backups

Back up at minimum:

- PostgreSQL database dump
- `/srv/apps/portal/docker-compose.prod.yml`
- `/srv/apps/portal/.env`
- Any uploaded configuration or application-specific compose files

Example database backup:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U portal portal \
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

## Development Notes

- Backend source is under `backend/app`.
- Frontend source is under `frontend/src`.
- Database migrations are under `backend/migrations`.
- Never commit `.env`.
- API secrets stay server-side.
- PostgreSQL is internal-only in production.

