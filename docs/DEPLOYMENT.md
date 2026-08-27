# Deployment

How to put Visioncore on a production VPS (Hostinger or equivalent) using the
existing Docker Compose stack. A packaged desktop `.exe` is deliberately not
covered here — the app is five coordinated services (Postgres, Redis, the
FastAPI backend, a Celery worker, and the frontend) sharing a database and a
storage volume, which is a server workload, not a desktop one. Recreating
that outside Docker means running Postgres and Redis as separate Windows
services and losing the reproducibility Compose already gives you, for no
real benefit.

## 1. Provision the VPS

- **Plan:** Hostinger KVM 2 or higher (2 vCPU / 8 GB RAM / Ubuntu 22.04).
  Five containers plus Docker image builds need headroom — a 4 GB plan will
  struggle during `docker compose build`.
- **OS:** Ubuntu 22.04 LTS.
- Point your domain's **A record** at the VPS's public IP before you start —
  DNS propagation takes time, so kick it off early.

## 2. Initial server hardening

```bash
ssh root@your-vps-ip
adduser deploy && usermod -aG sudo deploy      # don't run everything as root
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

Only 22/80/443 stay open to the internet. Postgres, Redis, and the app's own
ports (8000, 5174) must never be exposed publicly — they're reached only
through the reverse proxy or internally between containers (see §5).

## 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```

## 4. Deploy the code

```bash
su - deploy
git clone <your-repo-url> visioncore && cd visioncore
cp .env.example .env
nano .env
```

Production values to change before first boot — don't ship the `.env.example`
defaults:

| Variable | Change to |
|---|---|
| `POSTGRES_PASSWORD` | a strong random password |
| `JWT_SECRET` | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ANTHROPIC_API_KEY` | your real key |
| `ANTHROPIC_ADMIN_API_KEY` | set this if you want the Admin usage dashboard live |
| `SEED_ADMIN_PASSWORD` / `SEED_USER_PASSWORD` | leave as-is, but change both via Settings → Reset password right after first login |
| `CORS_ORIGINS` | `https://yourdomain.com` — must match the real frontend origin, not `localhost` |

## 5. Put a reverse proxy in front (TLS)

Don't expose the frontend/backend ports directly to the internet. **Caddy**
is the simplest option — one binary, automatic Let's Encrypt HTTPS, no
manual certificate renewal.

```bash
sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`:

```
yourdomain.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /* localhost:5174
}
```

```bash
sudo systemctl reload caddy
```

In `docker-compose.yml`, bind the exposed ports to localhost only, so Caddy
can reach them but the internet can't:

```yaml
backend:
  ports: ["127.0.0.1:8000:8000"]
frontend:
  ports: ["127.0.0.1:5174:80"]
db:
  ports: ["127.0.0.1:5433:5432"]   # or drop this line entirely if you never need external psql access
```

## 6. Bring it up

```bash
docker compose up -d --build
docker compose logs -f backend    # confirm migrations ran and there's no missing-API-key warning
```

Visit `https://yourdomain.com`, log in as `admin` / the seed password, and
**change both seed passwords immediately** under Settings → Reset password.

## 7. Backups

Two things need backing up: the Postgres data, and the `storage` Docker
volume (every uploaded nameplate photo and generated workbook — see
[ARCHITECTURE.md](ARCHITECTURE.md#storage-layout)). A backup that lives only
on the same disk as the server doesn't survive a disk failure, so ship these
off-box.

```bash
# crontab -e
0 2 * * * docker exec visioncore-db pg_dump -U visioncore visioncore | gzip > /home/deploy/backups/db-$(date +\%F).sql.gz
0 2 * * * docker run --rm -v visioncore_storage:/data -v /home/deploy/backups:/backup alpine tar czf /backup/storage-$(date +\%F).tar.gz -C /data .
```

Sync `/home/deploy/backups` to remote storage (rclone to S3/Backblaze,
Hostinger's own backup add-on, etc.) on the same cron or a follow-up job.

## 8. Updates

```bash
cd visioncore && git pull
docker compose up -d --build
```

Alembic migrations run automatically on backend startup — no separate
migration step needed.

## Scaling beyond a single VPS

See the scaling table in [ARCHITECTURE.md](ARCHITECTURE.md#scaling-notes):
move extraction to Celery/ARQ with retry + DLQ (already partly true — the
`worker` service exists for this), move file storage to S3/Azure Blob behind
a storage interface, and consider a read replica for History once a single
Postgres instance becomes the bottleneck.
