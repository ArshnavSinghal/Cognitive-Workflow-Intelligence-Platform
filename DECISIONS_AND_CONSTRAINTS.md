# CWIP --- Architectural Decisions and Constraints

**Version:** 1.0  
**Audited:** 31 October 2026  
**Auditor:** Lead Software Architect & Senior Full-Stack AI Engineer  
**Source of Truth:** Repository Tree (`C:\Users\DELL\Desktop\CWIP`) and `PROJECT_MASTER_CONTEXT.md`

---

## 1. Preserved Architectural Decisions

These decisions form the architectural baseline of CWIP and must be preserved:

1. **Technology Stack:**
   - Frontend: React 19 + Vite + Recharts + Lucide Icons.
   - Backend: FastAPI + Pydantic v2 + SQLAlchemy 2.
   - Database: PostgreSQL (production/local runtime) with SQLite in-memory temporary fixture for automated tests.
   - Machine Learning: scikit-learn (`RandomForestClassifier`), Pandas, NumPy, Joblib.

2. **Controlled Action Space:**
   - All recommendations and activities are constrained to six string identifiers:
     `practice_current`, `practice_prerequisite`, `review_concept`, `easy_practice`, `hard_practice`, `take_assessment`.
   - Any client payload containing an unrecognized activity action is rejected with HTTP 422.

3. **Recommendation Session Lifecycle:**
   - A recommendation creates a `RecommendationSession` record with status `pending`.
   - Activities reference `recommendation_session_id`.
   - Validation enforces session existence, user ownership, matching target skill, and single evaluation (`status == 'pending'`).
   - Upon activity submission, an outcome is computed and the session status transitions to `evaluated`.

4. **Strict Data Separation (`is_test` vs `real`):**
   - Controlled exclusively on the server via `CWIP_DATA_MODE` (`development` $\to$ `is_test=True`, `real` $\to$ `is_test=False`).
   - Client-supplied `is_test` flags must never be trusted.
   - Synthetic rows in ML datasets must carry `is_synthetic=True`.

5. **Separate ML Artifacts:**
   - The synthetic baseline is stored in `backend/app/ml/action_model.joblib`.
   - The real model is trained to `backend/app/ml/real_action_model.joblib`.
   - The real pipeline must never overwrite the synthetic artifact.

6. **Authentication Contract:**
   - Custom `HTTPBearer(auto_error=False)` behavior:
     - Missing Authorization header $\to$ HTTP 403 (`Not authenticated`).
     - Invalid / expired / malformed token $\to$ HTTP 401 (`Invalid token`).
   - This exact contract is verified by regression tests and must remain intact.

7. **Baseline Test Suite:**
   - The 68 passing backend tests in `tests/` represent the required regression safety net.

---

## 2. Hard Technical Constraints

### Machine Learning Constraints

1. **Synthetic Accuracy vs Real Efficacy:**
   - The synthetic model's $\approx 98\%$ accuracy is purely an artifact of fitting deterministic heuristic rules from `synthetic.py`. It does **not** reflect real-world learning effectiveness or student mastery growth.
2. **Current Training Label Semantics:**
   - In `backend/app/ml/real_training.py`, the training label `y` is currently `recommended_action`. This means the model learns to **imitate the existing recommendation policy**. It does not model causal mastery gain or predict whether an action will lead to positive outcomes.
3. **Real Training Gates:**
   - Training requires at least 30 real, non-test samples for the specific user and at least 2 distinct action classes. With only 2 real outcomes currently in PostgreSQL, the real training script will and must fail gracefully until data volume is sufficient.
4. **No Automatic Runtime Model Swapping:**
   - `backend/app/ml/predict.py` must continue loading `action_model.joblib` until explicit evaluation, user approval, and rollback mechanisms are established for `real_action_model.joblib`.

### Behavioral & Adherence Constraints

1. **Self-Reported Adherence:**
   - The learner selects `actual_action` from a dropdown upon submitting an activity. The system does not independently observe learner behavior outside CWIP. Therefore, all adherence analytics must be clearly labeled as **self-reported**.
2. **Adherence $\ne$ Effectiveness:**
   - Following a recommendation (adherence) does not guarantee mastery gain (effectiveness). Conversely, deviating from a recommendation might still yield a positive outcome. Adherence and learning effectiveness must be tracked as distinct metrics.
3. **Current API Nuance in `GET /learning-outcomes`:**
   - The `total` and `outcomes` list honor the optional `is_test` query parameter.
   - However, the adherence aggregates (`adherence_rate`, `total_real_evaluated`, `recommendations_followed`) are calculated across **all real outcomes** for the user, regardless of whether `is_test=true` was requested. This behavior is deliberate and tested.

---

## 3. Technical Debt & Known Vulnerabilities

1. **Top-Level Database DDL Execution:**
   - `backend/app/main.py:34` calls `Base.metadata.create_all(bind=engine)` at module load time. When running tests or importing `app` without a live PostgreSQL instance, an `OperationalError` occurs unless network bypass is granted or engine creation is deferred.
2. **Security & Secrets:**
   - In `backend/app/auth.py`, `SECRET_KEY = "cwip-secret-key-change-later"` is hardcoded rather than loaded from environment variables.
   - Generated JWT tokens do not include an `exp` (expiration) timestamp and never expire.
3. **Hardcoded Frontend Catalogue:**
   - `frontend/src/App.jsx` hardcodes skill IDs `1` (Regression) and `2` (Statistics) and subject `"Mathematics"`.
   - The backend lacks catalogue listing endpoints like `GET /skills` or `GET /user-skills`.
4. **Relational Graph Limitation:**
   - Prerequisite checking is limited to 1-hop SQL queries on `skill_dependencies`. Multi-hop dependency trees, circular dependency detection, and transitive prerequisite gaps are unhandled.
5. **Database Schema Management:**
   - No Alembic migrations exist. `Base.metadata.create_all()` cannot alter existing tables, requiring manual SQL statements for column alterations.
