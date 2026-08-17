# Visioncore — Nameplate Data Migration

Transform industrial nameplate images into structured, auditable asset data with AI.

React (Vite + TypeScript) · FastAPI (Python 3.12) · PostgreSQL 16 · Claude API · Docker

---

## 1. Quick start (Docker — recommended)

```bash
cp .env.example .env          # then edit ANTHROPIC_API_KEY + JWT_SECRET
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:5173        |
| API      | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |
| Postgres | localhost:5432               |

Seed accounts are created on first boot (change the passwords immediately):

| Role  | Username | Password      |
|-------|----------|---------------|
| Admin | `admin`  | `Admin@123`   |
| User  | `user`   | `User@123`    |

## 2. Running locally in VS Code (no Docker)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # point DATABASE_URL at your Postgres
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5174** — deliberately a different port from the Docker frontend
(`5173`) above, so the two can run side by side without one stealing the other's port.
The Vite dev server proxies `/api` to `http://localhost:8000`, so no CORS setup is needed in dev.

## 3. What the app does

1. A user drops 1–20 images into **New Batch**. Filenames follow
   `12-4020-BV-0074-BALL VALVE.jpg` → tag number `12-4020-BV-0074`,
   description `BALL VALVE`.
2. Images sharing a tag number are grouped (1–3 images per tag, max 10 tags per batch).
3. Each tag runs through `Uploaded → Extracting → Processing → Completed / Failed`.
4. Claude reads every image for the tag in a single vision call and returns 14 structured
   fields, each with a `Confirmed` / `Verify` quality mark.
5. Results land in an editable table. Edit → Save writes the corrected values; the AI's
   original answer is preserved separately for audit.
6. Two workbooks are generated per tag, byte-for-byte matching the supplied reference
   formats:
   - `AI Output-12-4020-BV-0074-BALL VALVE.xlsx`
   - `12-4020-BV-0074-BALL VALVE-Template.xlsx`

**Duplicate protection.** Tag numbers are unique. If a tag already exists, the batch does
not create a second record — the UI shows *"Tag already extracted"* along with the stored
values and links to the workbooks generated the first time round.

## 4. Roles

**Admin** — user management (create, disable, reset password, change role), full
upload/download history across all users, and the Claude API usage dashboard
(tokens in/out, per-request cost, running spend against the configured credit budget).

**User** — upload, edit, save, download, and view their own history.

## 5. Repository layout

```
visioncore/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── core/          config, security, dependencies
│   │   ├── db/            engine, session, seed
│   │   ├── models/        SQLAlchemy 2.x ORM models
│   │   ├── schemas/       Pydantic v2 request/response contracts
│   │   ├── api/v1/        routers
│   │   └── services/      filename parsing, Claude extraction, Excel writers, pipeline
│   └── alembic/           migrations
├── frontend/
│   └── src/
│       ├── api/           typed fetch client
│       ├── store/         auth + theme context
│       ├── components/    header, sidebar, dropzone, status rail, editable table…
│       └── pages/         Login, Home, NewBatch, History, Settings, Admin
└── docs/                  format notes
```

## 6. Swapping in your company logo

Replace `frontend/src/assets/logo.svg` with your own file (keep the name, or update the
import in `src/components/Logo.tsx`). Company name is a single constant in
`frontend/src/config.ts`.

For the login background, drop a photo at `frontend/src/assets/login-bg.jpg` and
uncomment the `background-image` line in `src/styles/login.css`. Without it the page
falls back to a generated industrial gradient, so nothing breaks if you skip this.

## 7. Notes on the Claude usage dashboard

Anthropic does not expose a live account-balance endpoint, so Visioncore measures spend
rather than reading it: every API call's `usage` block is written to `api_usage`, priced
using the per-million rates in `.env`, and totalled against `CLAUDE_CREDIT_BUDGET_USD`.
Update the rates when your plan changes. See `docs/EXCEL_FORMAT.md` for the workbook
specification and `docs/ARCHITECTURE.md` for the request lifecycle.
