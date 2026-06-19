# jobjob webapp

Local dashboard for managing job applications — queue, launch, and review results.
Runs on `127.0.0.1` only (never network-exposed).

## Setup

### 1. Install the jobjob package (once)

From the repo root:

```sh
pip install -e .
```

### 2. Install backend dependencies

```sh
pip install -r webapp/backend/requirements.txt
```

### 3. Install frontend dependencies

```sh
cd webapp/frontend
npm install
```

## Running (development)

Two terminals:

```sh
# Terminal 1 — backend
cd webapp/backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend dev server (with hot reload)
cd webapp/frontend
npm run dev
```

Open `http://127.0.0.1:5173`.

## Running (production build)

```sh
cd webapp/frontend
npm run build          # outputs to webapp/frontend/dist/

cd ../backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The backend serves the built frontend from `/`.

## Security notes

- Backend binds `127.0.0.1` only — not accessible from the network.
- CSRF: double-submit cookie pattern. All state-changing API requests require
  an `X-CSRF-Token` header matching the `csrf_token` cookie.
- Secrets (`ANTHROPIC_API_KEY`, etc.) are **never** returned by any API
  response. The config editor shows secrets as "set / not set" only.
- File operations are sandboxed to `static/`, `data/`, and `env/`. Paths are
  resolved and verified before any read/write; symlink escapes are rejected.
- Cost guard: per-run ($2.00) and daily ($20.00) budgets enforced before
  launching any job. Limits are configurable in `webapp/backend/main.py`
  (`app.state.settings`).
