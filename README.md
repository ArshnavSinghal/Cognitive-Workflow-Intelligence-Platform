# CWIP — Cognitive Workflow Intelligence Platform

An adaptive learning platform that goes beyond recording quiz scores. CWIP tracks learner activity, models skill mastery and prerequisite risk, recommends the next best learning action with a machine-learning model, and measures whether those recommendations actually helped.

**Stack:** React 19 + Vite → FastAPI → PostgreSQL, with a scikit-learn recommendation layer.

---

## Problem Statement

Most learning tools show scores but not why a learner is stuck or what to do next. Skills depend on one another, so a weak prerequisite quietly blocks progress in everything downstream. CWIP models those dependencies, finds the root gap, and recommends targeted next actions, then closes the loop by checking learning outcomes after each recommendation.

---

## Key Features

- User registration and login (bcrypt password hashing, JWT bearer tokens)
- Skill catalogue, enrolment and per-skill learner profiles
- Activity recording (action, duration, score) with validation
- Mastery and confidence estimation from a weighted four-factor formula (average, recent performance, consistency, error burden)
- Skill prerequisite graph (NetworkX DAG): transitive prerequisites, descendants, cycle detection, shortest path, topological order, bottleneck scoring, gap analysis
- ML next-action recommendation (RandomForest over 10 extracted features)
- Feedback loop: recommendations are linked to later activities, and outcomes and adherence are computed
- Analytics endpoints and an ML evaluation-readiness check
- React dashboard with charts (Recharts)

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Recharts, Lucide React |
| Backend | FastAPI, Uvicorn, Pydantic |
| Database | PostgreSQL via SQLAlchemy 2 and psycopg 3 (SQLite for tests) |
| ML | scikit-learn, pandas, NumPy, joblib |
| Graph | NetworkX |
| Auth | python-jose (JWT), passlib (bcrypt) |
| Testing | pytest |

---

## Architecture and Workflow

The learner logs in and picks a skill to enrol in.
Activities are recorded and mastery and confidence are recalculated.
The prerequisite graph is checked for root gaps.
Ten features are extracted and the RandomForest model recommends the next action.
Later activities are linked back to the recommendation session, and outcomes and adherence feed the analytics.

More detail: [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS_AND_CONSTRAINTS.md](DECISIONS_AND_CONSTRAINTS.md), [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), [FILE_STRUCTURE.md](FILE_STRUCTURE.md).

---

## Project Structure

```
CWIP/
├── backend/          # FastAPI app, models, ML code (app/ml/)
├── frontend/         # React + Vite single-page app
├── tests/            # pytest suite (API, ML, skill graph, feedback loop)
├── documentation/    # Project report, figures and generators
└── *.md              # Architecture, status, roadmap
```

---

## Installation

**Prerequisites:** Python 3.11+ (developed on 3.14), Node.js 18+, PostgreSQL 16+.

```bash
git clone https://github.com/ArshnavSinghal/Cognitive-Workflow-Intelligence-Platform.git
cd Cognitive-Workflow-Intelligence-Platform
```

### Database

```sql
CREATE DATABASE cwip;
```

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
cp ../.env.example .env          # then edit DATABASE_URL and SECRET_KEY
```

### ML Model

The trained synthetic development model is included at `backend/app/ml/action_model.joblib` and works out of the box. To regenerate it:

```bash
# from the repository root, with venv active
python -m backend.app.ml.train_model
```

### Frontend

```bash
cd frontend
npm install
```

---

## How to Run

```bash
# Terminal 1 — backend (from repository root, venv active)
python -m uvicorn backend.app.main:app --reload
# API: http://127.0.0.1:8000   Swagger UI: http://127.0.0.1:8000/docs

# Terminal 2 — frontend (from frontend/)
npm run dev
# UI: http://127.0.0.1:5173
```

---

## Tests

```bash
# from the repository root, with venv active
pytest tests -v
```

Tests use an in-memory SQLite database, so PostgreSQL is not needed to run them.

---

## API Documentation

Interactive docs are served at `/docs` (Swagger) when the backend runs. Main routes:

| Area | Endpoints |
|---|---|
| Auth | `POST /register`, `POST /login` |
| Skills | `GET /skills`, `GET /skills/{id}`, `POST /skills/{id}/enroll`, `GET /skills/{id}/profile` |
| Activities | `POST /activities`, `GET /activities` |
| Graph | `POST /skill-dependencies`, `GET /skills/{id}/prerequisites`, `/descendants`, `/diagnosis`, `/path/{target}`, `GET /skills/graph/topological` |
| Intelligence | `GET /skills/{id}/analysis`, `/gap-analysis`, `/recommendation`, `/features` |
| Outcomes | `POST /learning-outcomes`, `GET /learning-outcomes` |
| Analytics / ML | `GET /analytics/effectiveness`, `/analytics/feedback-loop`, `/ml/actions`, `/ml/training-data`, `/ml/evaluation/readiness` |

Protected routes expect an `Authorization: Bearer <token>` header obtained from `POST /login`.

---

## Screenshots

Add images to `documentation/screenshots/` and link them here.

| Dashboard | Recommendations | Skill graph |
|---|---|---|
| coming soon | coming soon | coming soon |

---

## Future Scope

See [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md). Highlights: training on real learner data in place of synthetic data, a model-evaluation gate before deployment, and database migrations.

---

## License

Add a LICENSE file (MIT is a common choice).
