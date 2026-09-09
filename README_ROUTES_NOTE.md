# MCET Visitor Tracking System

## ⚠️ Important — read this first

Your uploaded `backend.zip` was **missing the `routes/` package**. `main.py` does
`from routes import auth, visitor, admin`, but only `auth.py` (JWT helpers), `models.py`,
`schemas.py`, and `database.py` were present — no route handlers at all, so the backend
could not start as-is.

I reconstructed `routes/auth.py`, `routes/visitor.py`, and `routes/admin.py` from your
`schemas.py`/`models.py` (which fully define the data shapes) and built the frontend
against that real, tested API — not guessed endpoint names. It's included below, already
running end-to-end.

Two other things worth knowing:
- Your actual DB schema (`models.py`) is a **GPS/BLE live-tracking system** (visitors
  self-register and stream location; admins log in separately), not quite the
  "gate register" flow described in the brief. I kept the tracking pieces (`/visitors/register`,
  `/visitors/location`, `/visitors/live/all`) for schema compatibility, and added the
  staff-operated `check-in` / `check-out` flow you asked for on top of the same tables.
- There's no `vehicle_number` column in your `Visitor` model, so on the Check-In form
  I mapped "Vehicle Number" to the existing `device_info` field. If you want a real
  dedicated column, add `vehicle_number = Column(String, nullable=True)` to `Visitor`
  in `models.py` and update `schemas.VisitorRegister` + `routes/visitor.py` accordingly.

## What's in this zip

```
backend/            FastAPI backend (yours + reconstructed routes/)
frontend/            React + Vite + Tailwind frontend
```

## Running the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Seed an admin account + demo visitors (safe to re-run)
python3 seed.py

# Start the API
python3 main.py
# → http://localhost:8000  (docs at /docs)
```

Seeded login: **admin / admin123**

Set a real `JWT_SECRET` env var in production — `auth.py` falls back to a hardcoded
dev secret if it's unset.

## Running the frontend

```bash
cd frontend
npm install
cp .env.example .env      # points VITE_API_BASE_URL at http://localhost:8000
npm run dev
# → http://localhost:5173
```

`npm run build` produces a static `dist/` folder for deployment (Netlify, Vercel, Nginx, etc).

## API endpoints the frontend uses

| Method | Path                              | Auth        | Purpose                                    |
|--------|------------------------------------|-------------|---------------------------------------------|
| POST   | `/auth/login`                      | —           | Staff/admin login, returns JWT              |
| GET    | `/admin/dashboard`                 | admin JWT   | Today's stats + live visitor list           |
| POST   | `/visitors/check-in`               | admin JWT   | Log a walk-in visitor, sets status "Inside" |
| POST   | `/visitors/check-out/{visitor_id}` | admin JWT   | Sets exit_time + status "Exited"            |
| GET    | `/visitors/active`                 | admin JWT   | All visitors currently "Inside"             |
| GET    | `/visitors/history`                | admin JWT   | Paginated log with `start_date`/`end_date`/`search`/`department` filters |

The JWT is stored in `localStorage` and attached to every request by an Axios request
interceptor (`frontend/src/api/client.js`); a 401 response clears the session and
redirects to `/login` automatically.

## Deploying

- **Backend → Render**: point it at `backend/`, build command `pip install -r requirements.txt`,
  start command `uvicorn main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL` if you
  move off SQLite, and `JWT_SECRET`.
- **Frontend → GitHub Pages / Vercel / Netlify**: build with `npm run build`, deploy `dist/`.
  Set `VITE_API_BASE_URL` to your deployed backend URL at build time, and make sure the
  backend's CORS `allow_origins` (in `main.py`) includes your frontend's domain instead of `"*"`
  once you're in production.
