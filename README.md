# 🎬 MovieRec — AI-Powered Movie & Series Recommender

> Personalized movie and web series recommendations powered by graph-based collaborative filtering, cosine similarity, and Groq/Llama AI.

**Live Demo:** [https://movie-recommendation-with-ai-chat-b.vercel.app](https://movie-recommendation-with-ai-chat-b.vercel.app)

---

## What is MovieRec?

MovieRec is a full-stack recommendation system that learns your taste from what you watch and suggests movies and web series you'll actually enjoy. The more you watch, the smarter it gets.

It also has an AI chat interface — just type "suggest me something like Inception" and get instant personalized suggestions.

---

## Features

- **465+ movies and web series** — Hollywood, Bollywood, top-rated
- **Personalized recommendations** — based on your watch history
- **Mood-based filtering** — detects your current mood from recent watches
- **AI Chat** — natural language movie suggestions via Groq/Llama 3.3
- **Real posters** — fetched live from TMDB API
- **JWT Authentication** — secure register and login
- **Netflix-style UI** — dark theme, hover effects, responsive grid

---

## How It Works

```
User watches movies
       ↓
Graph built (users as nodes, movies as edges)
       ↓
Cosine similarity finds users with similar taste
       ↓
Their watches become your recommendations
       ↓
LLM generates personalized reason for each suggestion
```

---

## DSA Concepts Implemented

| Concept | Where Used |
|---|---|
| Graph (Adjacency List) | User-item relationship mapping |
| Cosine Similarity | Finding similar users (manual, no ML library) |
| Binary Search | Fast movie lookup in sorted catalog |
| Collaborative Filtering | Core recommendation algorithm |

---

## Tech Stack

### Backend
- **FastAPI** — REST API framework
- **PostgreSQL** — relational database
- **SQLAlchemy** — ORM
- **Alembic** — database migrations
- **bcrypt** — password hashing
- **PyJWT** — JWT token auth

### Frontend
- **React** — UI framework
- **Vite** — build tool
- **React Router** — client-side routing
- **CSS Modules** — component-scoped styling

### AI & External APIs
- **Groq (Llama 3.3-70b)** — LLM for recommendation reasons and chat
- **TMDB API** — movie/series metadata and posters

### Deployment
- **Vercel** — frontend hosting
- **Render** — backend hosting
- **Neon** — cloud PostgreSQL database

---

## Project Structure

```
recommendation_systems/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── models/               # SQLAlchemy models
│   ├── routes/               # API endpoints
│   ├── services/
│   │   ├── graph_service.py         # Adjacency list graph
│   │   ├── recommendation_service.py # Cosine similarity + ranking
│   │   ├── catalog_service.py        # Binary search on content
│   │   ├── content_service.py        # Mood-based filtering
│   │   └── llm_service.py           # Groq LLM integration
│   ├── scripts/
│   │   ├── import_movies.py  # TMDB movie importer
│   │   └── import_series.py  # TMDB series importer
│   ├── main.py
│   ├── seed.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ContentCard.jsx   # Movie/series card with hover
    │   │   └── Navbar.jsx
    │   ├── pages/
    │   │   ├── HomePage.jsx          # Browse with tabs + filters
    │   │   ├── RecommendationsPage.jsx
    │   │   ├── ChatPage.jsx
    │   │   ├── MovieDetailPage.jsx
    │   │   ├── LoginPage.jsx
    │   │   └── RegisterPage.jsx
    │   └── services/
    │       └── api.js            # Centralized fetch calls
    └── vercel.json
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, get JWT |
| GET | `/content` | All movies and series |
| GET | `/content/{id}` | Single content item |
| POST | `/interactions` | Mark as watched |
| GET | `/recommendations/{user_id}` | Personalized recommendations |
| POST | `/chat` | AI chat for suggestions |
| GET | `/health` | Health check |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 18

### Backend

```bash
# Clone the repo
git clone https://github.com/amanahma/Movie_recommendation_with_AI_ChatBot.git
cd Movie_recommendation_with_AI_ChatBot/backend

# Install dependencies
pip install -r requirements.txt

# Create .env file (see .env.example)
cp .env.example .env
# Fill in your values

# Run migrations
python -m alembic upgrade head

# Seed sample data
python seed.py

# Start server
python -m uvicorn main:app --reload
```

### Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Add VITE_API_URL and VITE_TMDB_API_KEY

# Start dev server
npm run dev
```

### Environment Variables

**backend/.env**
```
DATABASE_URL=postgresql://user:password@localhost:5432/recommendation_db
SECRET_KEY=your_random_secret_key
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
TMDB_API_KEY=your_tmdb_key
```

**frontend/.env**
```
VITE_API_URL=http://localhost:8000
VITE_TMDB_API_KEY=your_tmdb_key
```

---

## Import Real Movie Data

```bash
# Import Hollywood + Bollywood movies
python scripts/import_movies.py

# Import web series
python scripts/import_series.py

# Restart backend to reload catalog
python -m uvicorn main:app --reload
```

---

## Deployment

| Service | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Set VITE_API_URL env var |
| Backend | Render | Set all backend env vars |
| Database | Neon | Free PostgreSQL cloud |

---

## Screenshots

> Register → Browse 465+ titles → Mark watched → Get personalized recommendations → Chat with AI

---

## What I Learned Building This

- Graph data structures applied to real recommendation problems
- Cosine similarity math and implementation without libraries
- Binary search in a real catalog lookup scenario
- Full-stack architecture: database → API → frontend
- JWT authentication flow
- Cloud deployment across three separate platforms
- Cache invalidation (similarity cache + in-memory graph)

---

*Built as a portfolio project demonstrating DSA, ML concepts, and full-stack development.*
