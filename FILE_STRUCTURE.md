# CWIP --- Repository File Structure

**Generated:** 31 October 2026  
**Auditor:** Lead Software Architect & Senior Full-Stack AI Engineer  
**Source of Truth:** Repository Tree (`C:\Users\DELL\Desktop\CWIP`)

---

## 1. Top-Level Directory Tree

```text
CWIP/
├── .pytest_cache/                  # Pytest run cache
├── backend/                        # FastAPI application & ML pipeline
│   ├── app/                        # Application source package
│   │   ├── ml/                     # Machine learning models, pipelines & data gen
│   │   │   ├── __init__.py         # Package marker
│   │   │   ├── actions.py          # Action space definition & validator
│   │   │   ├── action_model.joblib # Serialized RandomForest synthetic model
│   │   │   ├── features.py         # 10-feature skill vector extractor
│   │   │   ├── mastery.py          # Basic score-based mastery utility
│   │   │   ├── model.py            # Model training & loader functions
│   │   │   ├── predict.py          # Inference entry point for recommendation engine
│   │   │   ├── real_training.py    # Real learner outcome extraction & validation
│   │   │   ├── synthetic.py        # Scenario-based synthetic dataset generator
│   │   │   ├── training.py         # Feature matrix assembly & action mapping
│   │   │   ├── train_model.py      # CLI script: Train synthetic development model
│   │   │   └── train_real_model.py # CLI script: Train real learner model
│   │   ├── __init__.py             # Package marker
│   │   ├── auth.py                 # JWT token generation, password hashing & verification
│   │   ├── config.py               # Environment configuration & data mode switch
│   │   ├── database.py             # SQLAlchemy engine & session setup
│   │   ├── main.py                 # FastAPI application routes, lifecycle & business logic
│   │   ├── models.py               # SQLAlchemy ORM models (7 entities)
│   │   └── schemas.py              # Pydantic schemas & field validators
│   ├── .env                        # Local environment variables (DATABASE_URL, CWIP_DATA_MODE)
│   ├── correct_test_outcome.py     # One-off historical DB maintenance script
│   └── requirements.txt            # Python dependencies (UTF-16LE formatted freeze)
├── data/                           # [EMPTY PLACEHOLDER] Historical proposal for dataset storage
├── database/                       # [EMPTY PLACEHOLDER] Historical proposal for SQL/migrations
├── docs/                           # [EMPTY PLACEHOLDER] Historical proposal for design documentation
├── frontend/                       # React 19 + Vite frontend application
│   ├── dist/                       # Vite production build artifacts
│   ├── node_modules/               # NPM dependencies
│   ├── public/                     # Public static assets (favicon.svg, icons.svg)
│   ├── src/                        # React application source code
│   │   ├── assets/                 # Static images (hero.png, react.svg, vite.svg)
│   │   ├── api.js                  # Frontend API client & authenticated fetch wrappers
│   │   ├── App.css                 # Application styling
│   │   ├── App.jsx                 # Single-page dashboard application & sub-views
│   │   ├── index.css               # Base CSS & resets
│   │   └── main.jsx                # React root mount entry point
│   ├── .gitignore                  # Git ignore rules for frontend
│   ├── eslint.config.js            # ESLint flat configuration
│   ├── index.html                  # HTML entry template
│   ├── package-lock.json           # NPM deterministic dependency tree
│   ├── package.json                # NPM project definition and dependencies
│   ├── README.md                   # Vite default documentation
│   └── vite.config.js              # Vite bundler configuration
├── ml/                             # [EMPTY PLACEHOLDER] Historical proposal for standalone ML
├── tests/                          # Automated backend test suite
│   ├── __init__.py                 # Package marker
│   ├── conftest.py                 # Pytest fixtures, SQLite engine & dependency overrides
│   ├── test_api.py                 # 49 API integration tests
│   ├── test_ml.py                  # 12 ML module unit tests
│   └── test_real_training.py       # 7 Real-data validation & training tests
├── venv/                           # Python 3.14 virtual environment
├── README.md                       # Initial project README
├── requirements-lock-backup.txt    # Previous requirements freeze
└── requirements-lock.txt           # Current pip requirements freeze
```

---

## 2. File-by-File Inventory and Functionality

### Root Directory

| File | Purpose | Status |
| :--- | :--- | :--- |
| `README.md` | Initial overview of CWIP stack and backend setup instructions. | Outdated (references placeholder structure). |
| `requirements-lock.txt` | Explicit pip freeze of all 52 installed Python packages in `venv`. | Active lockfile. |
| `requirements-lock-backup.txt` | Previous lockfile backup before Starlette/FastAPI version bumps. | Preserved historical backup. |

### Backend Source (`backend/app/`)

| File | Purpose | Key Symbols / Exports |
| :--- | :--- | :--- |
| `__init__.py` | Package marker for `backend.app`. | None |
| `config.py` | Server-side data mode determination (`development` vs `real`). | `get_cwip_data_mode()`, `is_test_mode()` |
| `database.py` | Engine initialization (PostgreSQL + Psycopg, SQLite fallback) and ORM `Base`. | `engine`, `SessionLocal`, `Base` |
| `auth.py` | Password hashing (`bcrypt`) and JWT encode/decode routines. | `hash_password`, `verify_password`, `create_token`, `verify_token` |
| `models.py` | SQLAlchemy ORM tables: User, Activity, Skill, UserSkill, SkillDependency, LearningOutcome, RecommendationSession. | `User`, `Activity`, `Skill`, `UserSkill`, `SkillDependency`, `LearningOutcome`, `RecommendationSession` |
| `schemas.py` | Pydantic request/response validation with action validators. | `UserCreate`, `UserLogin`, `ActivityCreate`, `SkillCreate`, `UserSkillCreate`, `SkillDependencyCreate`, `RecommendationCreate`, `LearningOutcomeCreate` |
| `main.py` | FastAPI application, middleware, dependencies, 16 route handlers, and metric calculation. | `app`, `get_db()`, `get_current_user()`, `calculate_skill_metrics()` |

### Backend ML Subpackage (`backend/app/ml/`)

| File | Purpose | Key Symbols / Exports |
| :--- | :--- | :--- |
| `__init__.py` | Package marker for `backend.app.ml`. | None |
| `actions.py` | Controlled 6-action recommendation space and validation check. | `ACTIONS`, `ACTION_SET`, `is_valid_action()` |
| `features.py` | Computes 10 normalized feature metrics from activity history. | `build_skill_features()`, `DIFFICULTY_WEIGHTS` |
| `mastery.py` | Standalone basic score-averaging calculation. | `calculate_mastery()` |
| `model.py` | RandomForest classifier training, metric generation, joblib persistence. | `FEATURE_COLUMNS`, `MODEL_PATH`, `train_action_model()`, `load_action_model()` |
| `predict.py` | Loads `action_model.joblib` and evaluates input feature vector. | `predict_action()` |
| `synthetic.py` | Generates 600 synthetic learner records with deterministic scenarios. | `generate_synthetic_dataset()`, `_choose_action()`, `_determine_outcome()` |
| `training.py` | Maps actions to integer labels `[0..5]` and formats Pandas DataFrame. | `ACTION_MAP`, `prepare_training_dataframe()` |
| `train_model.py` | Executable script: Generates synthetic dataset and saves `action_model.joblib`. | `main()` |
| `real_training.py` | Queries non-test learner outcomes, validates snapshots, filters eligible rows. | `MIN_REAL_SAMPLES`, `REQUIRED_FEATURES`, `fetch_real_training_data()`, `prepare_real_training_dataframe()` |
| `train_real_model.py` | Executable script: Filters user's real outcomes and trains `real_action_model.joblib`. | `main(user_id)` |
| `action_model.joblib` | Active serialized scikit-learn RandomForest model trained on synthetic data. | Binary artifact |

### Frontend Source (`frontend/src/`)

| File | Purpose | Key Components / Functions |
| :--- | :--- | :--- |
| `main.jsx` | React DOM root rendering into `#root`. | Entry point |
| `App.jsx` | Root application component; contains routing state, layout, auth check, and views. | `App`, `RecommendationsPage`, `MySkills`, `LearningProgress`, `LearningOutcomeHistory`, `Metric` |
| `api.js` | API client handling JWT bearer headers, fetch calls, error parsing. | `apiRequest()`, `login()`, `getSkillAnalysis()`, `getSkillRecommendations()`, `getLearningOutcomes()`, `getActivities()`, `createActivity()`, `logout()` |
| `App.css` | All styling for layout, navigation, cards, tables, modal, forms, and badges. | CSS classes |
| `index.css` | Global styles, typography imports, and CSS root variables. | Global styles |

### Test Suite (`tests/`)

| File | Purpose | Test Count |
| :--- | :--- | :--- |
| `conftest.py` | SQLite in-memory temporary database fixture, mock users/skills, and FastAPI dependency overrides. | N/A (Fixture provider) |
| `test_api.py` | Integration tests for authentication, activities, skills, recommendations, outcomes, training data. | 49 tests |
| `test_ml.py` | Unit tests for prediction, DataFrame assembly, model training gates, synthetic vs real data isolation. | 12 tests |
| `test_real_training.py` | Unit tests for real data fetching, snapshot validation, user isolation, separate model paths. | 7 tests |
| **Total** | | **68 tests** |

### Empty Historical Placeholders

The following directories exist at the repository root as empty folders from an initial scaffolding proposal:
- `data/`
- `database/`
- `docs/`
- `ml/`

*Note: All active ML code is housed under `backend/app/ml/`, and database models are in `backend/app/models.py`.*
