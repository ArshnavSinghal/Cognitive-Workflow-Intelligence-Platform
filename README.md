# CWIP

**Stack:** React → FastAPI → PostgreSQL (+ ML layer coming next)

## Project Structure

```
CWIP/
├── backend/      # FastAPI app
├── frontend/     # React app (coming next)
├── ml/           # ML models and inference
├── data/         # Raw / processed datasets
├── database/     # Migrations and seed scripts
├── tests/        # Integration and unit tests
└── docs/         # Project documentation
```

## Backend (FastAPI)

### First-time setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### Run the dev server

```bash
uvicorn app.main:app --reload
```

- API root:  http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
