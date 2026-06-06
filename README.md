# Movie Recommendation System

A full-stack movie recommender. **Phase 1** sets up the project structure and
database; recommendation logic and the LLM integration come in later phases.

## Tech stack
- **Backend:** FastAPI + SQLAlchemy 2.0 (ORM) + Alembic (migrations)
- **Database:** PostgreSQL
- **Frontend:** React (Vite)
- **LLM:** Groq (OpenAI-compatible API, later phase)

## Project structure
```
backend/
  config.py            # env-driven settings (DATABASE_URL, SECRET_KEY, GROQ_API_KEY)
  main.py              # FastAPI app entry point
  seed.py              # sample data: 20 movies, 10 users, interactions
  requirements.txt
  db/                  # Base, engine, session
  models/              # User, Movie, Interaction, SimilarityCache
  routes/              # API endpoints (health check for now)
  services/            # business logic (password hashing for now)
  alembic/             # migrations (initial schema included)
frontend/
  src/
    components/        # reusable UI pieces (MovieCard)
    pages/             # full screens (HomePage)
    services/          # API client (api.js)
```

## Backend setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure environment
copy .env.example .env        # then edit .env with your real values

# Create a PostgreSQL database named to match DATABASE_URL (e.g. "moviedb"),
# then build the schema and load sample data:
alembic upgrade head
python seed.py

# Run the API (http://localhost:8000/docs):
uvicorn main:app --reload
```

## Frontend setup
```powershell
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

## Migrations (Alembic)
```powershell
cd backend
alembic upgrade head                              # apply all migrations
alembic revision --autogenerate -m "describe it"  # after changing models
alembic downgrade -1                              # roll back one
```
