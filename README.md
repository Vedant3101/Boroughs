# Boroughs

Find your next round. Interactive map of Manhattan bars with price filters, visit tracking, ratings, and budget-aware pub crawl routing. (Other boroughs coming later.)

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

