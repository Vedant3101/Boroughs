# Boroughs

Find your next round. Interactive map of Manhattan bars with price filters, visit tracking, ratings, and budget-aware pub crawl routing. (Other boroughs coming later.)

## API

All responses are JSON. Auth uses JWT (`Authorization: Bearer <access>`).

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET    | `/api/health/`        | —    | Liveness + DB probe |
| POST   | `/api/auth/register/` | —    | Create user, return JWT pair |
| POST   | `/api/auth/login/`    | —    | Username + password → JWT pair |
| POST   | `/api/auth/refresh/`  | —    | Refresh token → new access token |
| GET    | `/api/auth/me/`       | yes  | Current user |
| GET    | `/api/bars/`          | —    | List bars. Filters: `search`, `borough`, `price_min`, `price_max`, `lat`+`lng`+`radius`, `ordering` |
| GET    | `/api/bars/{id}/`     | —    | Bar detail with avg rating, num ratings, num visits |
| GET    | `/api/visits/`        | yes  | Current user's visits |
| POST   | `/api/visits/`        | yes  | Log a visit |
| GET    | `/api/visits/{id}/`   | yes  | One visit (owner only) |
| DELETE | `/api/visits/{id}/`   | yes  | Remove a visit |
| GET    | `/api/ratings/`       | yes  | Current user's ratings |
| POST   | `/api/ratings/`       | yes  | Rate a bar (upserts; 201 on create, 200 on update) |
| PATCH  | `/api/ratings/{id}/`  | yes  | Update score/comment |
| DELETE | `/api/ratings/{id}/`  | yes  | Remove a rating |

Paginated endpoints accept `?page=N&page_size=N` (default 50, max 200).

## Stack

- **Frontend:** React + TypeScript + SCSS (Vite)
- **Backend:** Django + Django REST Framework + PostgreSQL/PostGIS
- **Maps:** Google Maps Platform (Maps JS, Places, Directions)

## Project layout

```
boroughs/
├── backend/      Django API
├── frontend/     React app
└── README.md
```

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
cp .env.example .env           # then fill in values
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env           # then fill in values
npm run dev
```

