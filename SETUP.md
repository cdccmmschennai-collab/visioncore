# Setup checklist

Work through this once; it takes about five minutes.

## 1. Configure

```bash
cp .env.example .env
```

Edit `.env` and set two values before anything else:

| Variable | What to put |
|---|---|
| `ANTHROPIC_API_KEY` | Your key from console.anthropic.com. Without it, uploads reach the extraction step and fail. |
| `JWT_SECRET` | A long random string. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

Optional but worth checking:

- `TEMPLATE_INPUT_PATH_PREFIX` / `TEMPLATE_OUTPUT_PATH_PREFIX` — the network
  paths written into the Template sheet's INPUT PHOTOS and OUTPUT WITH IMAGES
  columns. Defaults reproduce the reference workbook. Blank writes bare filenames.
- `CLAUDE_CREDIT_BUDGET_USD` and the two price-per-million rates — these drive
  the admin spend dashboard.

## 2. Run

```bash
docker compose up --build
```

First boot pulls images, runs migrations and seeds two accounts. Open
http://localhost:5173.

| Role  | Username | Password    |
|-------|----------|-------------|
| Admin | `admin`  | `Admin@123` |
| User  | `user`   | `User@123`  |

**Change both passwords immediately** under Settings → Reset password.

## 3. Verify the round trip

1. Sign in as `user`.
2. Go to **New Batch** and drop `12-4020-BV-0074-BALL VALVE.jpg`.
3. Watch the rail advance: Uploaded → Extracting → Processing → Completed.
4. Choose **Edit**, correct a field, choose **Save**.
5. Choose **Download Template** and confirm the corrected value appears in blue.
6. Upload the same file again — you should see **"Tag already extracted"** with
   the existing record, and no second row in the database.

## 4. Brand it

- **Logo** — replace `frontend/src/assets/logo.svg` with your own file, same
  name. Also copy it to `frontend/public/favicon.svg`.
- **Company name** — `COMPANY_NAME` in `frontend/src/config.ts`.
- **Login photograph** — drop a JPEG at `frontend/src/assets/login-bg.jpg` and
  uncomment the three `background-image` lines in `frontend/src/styles/login.css`.
  Skip it and the page uses a generated industrial gradient instead.
- **Colours** — `frontend/src/styles/theme.css`, one token block per theme.

## Troubleshooting

**Uploads fail immediately at Extracting**
`ANTHROPIC_API_KEY` is missing or wrong. Check `docker compose logs backend` —
the API logs a warning at startup when the key is unset.

**"None of those files could be read"**
Filenames must be `<TAG>-<DESCRIPTION>.jpg`, e.g. `12-4020-BV-0074-BALL VALVE.jpg`.
The dropzone previews the parse before you upload, so you can spot this early.

**Frontend can't reach the API in local dev**
Start the backend on port 8000. Vite proxies `/api` there; the proxy target is
in `frontend/vite.config.ts`.

**Local dev (`npm run dev`) opens the same URL as Docker, or shows the wrong app**
The Docker frontend and the local Vite dev server used to both default to
`http://localhost:5173`, so whichever one started second silently lost the port
and you'd land on the wrong build. Local dev now binds `5174` instead
(`frontend/vite.config.ts` → `server.port`) — Docker stays on `5173`. If you still
see a clash, confirm nothing else on your machine is also bound to one of those
ports (`netstat -ano | findstr :5173` on Windows).

**Migrations fail on first boot**
Postgres may still be starting. `docker compose up` again — the healthcheck
usually handles this, and the API retries on restart.

**Port already in use**
Change the left-hand side of the port mappings in `docker-compose.yml`
(`5173:80`, `8000:8000`, `5432:5432`).
