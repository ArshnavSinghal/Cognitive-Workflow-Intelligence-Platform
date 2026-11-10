# CWIP --- Persistent AI Agent Instructions & Guidelines

**Handover Target:** Antigravity / Any Future AI Coding Agent  
**Project:** CWIP (Cognitive Workflow Intelligence Platform)  
**Last Updated:** 31 October 2026  

---

## 1. Prime Directive & Operating Philosophy

CWIP is an existing, partially completed, carefully tested adaptive learning intelligence system. **Do NOT rebuild, scaffold over, or wholesale rewrite this project.**

1. **Repository as Source of Truth:** Never assume external documentation or historical notes represent current state. Inspect the actual working tree before writing or modifying code.
2. **Incremental Development:** Make surgical, targeted, well-tested edits. Preserve all working functionality.
3. **Preserve Test Baseline:** All changes must keep the existing 68 backend tests passing (`tests/`). Never deselect, mock out, or delete existing tests to force a build to pass.
4. **Data Integrity:** Keep synthetic/development data strictly isolated from genuine learner data. Never allow client-submitted `is_test` flags to dictate record classification.

---

## 2. Hard Architectural Rules

### Machine Learning Governance
- **Never describe synthetic model accuracy as real-world educational effectiveness.** Synthetic data is generated via deterministic heuristic policies; high accuracy ($98\%$) is only proof of policy imitation.
- **Never overwrite `backend/app/ml/action_model.joblib` with a real model.** Real models must be trained to `backend/app/ml/real_action_model.joblib`.
- **Never automatically switch `predict.py` to the real model** without explicit offline evaluation, documented performance gates, and user approval.
- **Adherence is self-reported.** Always label adherence metrics in the UI and API as self-reported by the learner.

### Database & Migrations
- **Do NOT run destructive database resets, `DROP TABLE`, or re-seed scripts** against PostgreSQL without explicit user confirmation and an existing backup.
- Note that `Base.metadata.create_all()` does **not** alter existing PostgreSQL tables or add missing columns to populated tables.
- Keep in mind that `backend/app/main.py:34` calls `Base.metadata.create_all(bind=engine)` upon module import.

### Authentication Contract
- CWIP relies on custom `HTTPBearer(auto_error=False)` semantics:
  - Missing Authorization header $\to$ HTTP 403 (`Not authenticated`).
  - Invalid / malformed / expired token $\to$ HTTP 401 (`Invalid token`).
- Do not replace this with default FastAPI `HTTPBearer(auto_error=True)` (which returns 403 for everything) because multiple integration tests verify this exact distinction.

---

## 3. Development Workflow & Commands

### Local Environment
- Root directory: `C:\Users\DELL\Desktop\CWIP`
- Virtual environment: `.\venv\Scripts\Activate.ps1`
- Python runtime: Python 3.14.0

### Running Tests
Always run tests using the project virtual environment:
```powershell
.\venv\Scripts\python -m pytest tests -v
```
*Note: Because `main.py` connects to PostgreSQL at top-level import, pytest requires the local PostgreSQL database to be reachable (or run with network bypass).*

### Running Backend
```powershell
# In root directory
.\venv\Scripts\python -m uvicorn backend.app.main:app --reload
```
- API Base: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

### Running Frontend
```powershell
cd frontend
npm run dev
```
- Vite Dev Server: `http://127.0.0.1:5173`

### Linting & Building Frontend
```powershell
npm --prefix frontend run lint
npm --prefix frontend run build
```

---

## 4. Environment Variables Reference

Defined in `backend/.env`:

| Variable | Values | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/cwip_db` | PostgreSQL connection string. Converted to `postgresql+psycopg://` in `database.py`. |
| `CWIP_DATA_MODE` | `development` or `real` | Controls whether created `LearningOutcome` records are flagged `is_test=True` (`development`) or `is_test=False` (`real`). |

---

## 5. Implementation Status & Next Priority

- **Phase 1 (Completed & Verified 31 Oct 2026):**
  - Action Adherence Rate KPI integrated into React Overview dashboard.
  - ESLint cleanup (`outcomesError` active and rendered).
  - 6 new backend tests added (74 passing tests total).
  - Clean `npm run lint`, `npm run build`, and `pytest` execution.

- **Phase 2 (Completed & Verified 31 Oct 2026):**
  - Learning Effectiveness Analytics backend endpoint (`GET /analytics/effectiveness`) implemented and tested.
  - Excluded test/synthetic data; restricted to authenticated user; handled empty states and missing sessions gracefully.
  - Provided multi-group breakdown ($\Delta \text{mastery}$ by skill, recommended action, actual action) and adherence comparison (followed vs not-followed).
  - Integrated into React "Learning Progress" dashboard with top KPIs, comparison cards, breakdown tables, and observational notice.
  - 7 new regression tests added (81 passing tests total).
  - Clean `npm run lint`, `npm run build`, and `pytest` execution.

- **Phase 3 (Completed & Verified 1 Nov 2026):**
  - Dynamic Skill Catalogue and Profile Endpoints implemented: `GET /skills`, `GET /skills/{id}`, `POST /skills/{id}/enroll`, `GET /skills/{id}/profile`.
  - Enforced safe transactional enrollment with duplicate rejection without database migrations.
  - Profile endpoint calculates empirical mastery, confidence, trend, activities, outcomes, and adherence without fabricating missing values.
  - Eliminated hardcoded skill array in `frontend/src/App.jsx`.
  - Upgraded `MySkills` to dynamically render enrolled vs available catalogue, handle enrollment, and inspect deep `SkillProfileModal`.
  - 11 new regression tests added (92 passing tests total).
  - **Phase 3 Corrective Patch Applied & Verified (1 Nov 2026):**
    - M-1: Serialized concurrent duplicate enrollments per learner via PostgreSQL row-level locking (`with_for_update()`) on `User` and `IntegrityError` rollback handling.
    - M-2: Enforced authorization boundary on `POST /skills` (HTTP 403 for learners) and added `SkillCreate` schema input validation.
    - L-1: Dynamically resolved recommendation targets across enrolled skills in `RecommendationsPage` and added 0-skill empty state notice.
    - 5 new security/regression tests added (97 passing tests total).
  - Clean `npm run lint`, `npm run build`, and `pytest` execution.

- **Phase 4 (Completed & Verified 1 Nov 2026):**
  - Integrated `networkx==3.7` into virtual environment and requirements.
  - Formulated Directed Acyclic Graph (`nx.DiGraph`) with edge convention `Prerequisite -> Dependent`.
  - Implemented multi-hop transitive prerequisite and descendant discovery, shortest path resolution, topological sort, and cycle prevention.
  - Designed deterministic 5-factor bottleneck scoring formula and multi-hop diagnosis module (`diagnose_prerequisites`).
  - Integrated diagnosis into recommendation engine (`GET /skills/{id}/recommendation`) and gap analysis (`GET /skills/{id}/gap-analysis`).
  - Added 5 new endpoints: `GET /skills/{id}/prerequisites`, `GET /skills/{id}/descendants`, `GET /skills/{id}/diagnosis`, `GET /skills/{source}/path/{target}`, `GET /skills/graph/topological`.
  - Integrated Prerequisite & Dependency Intelligence Panel into `SkillProfileModal` and bottleneck warning in `RecommendationsPage`.
  - **Phase 4 Security Correction (1 Nov 2026):** Enforced authorization boundary on `POST /skill-dependencies` (HTTP 403 for ordinary learners).
  - 20 new tests added (12 unit in `test_skill_graph.py` + 8 integration in `test_api.py`), bringing baseline to 117 passing tests total.
  - Clean `npm run lint`, `npm run build`, and `pytest` execution.

- **Phase 5, Step 3.3 (Completed & Verified 7 Nov 2026):**
  - Legacy Training Provenance Hardening implemented: `validate_and_extract_training_record` shared across loader and API.
  - Strict mandatory session linkage (`recommendation_session_id` non-null), ownership, skill concordance, and numerical validation enforced.
  - 12 new regression tests added in `tests/test_training_provenance_hardening.py` (142 passing tests total).
  - Clean `npm run lint`, `npm run build`, and `pytest` execution.

- **Phase 5, Step 4 (Completed & Verified 8 Nov 2026):**
  - Real-Data Model Evaluation Readiness & Statistical Governance Module implemented in `backend/app/ml/evaluation.py`.
  - Data readiness audit reusing shared training record validator with 12 distinct exclusion categories.
  - Deterministic data sufficiency gates ($N \ge 30, N \ge 150, K \ge 15, \text{diversity} \ge 2, \text{support} \ge 3 \times 20, K_{\text{eval}} \ge 20, K_{\text{cal},a} \ge 19$).
  - Partitioning infrastructure: Track A (disjoint unseen learner clusters) and Track B (chronological with zero future leakage).
  - Regression baselines: Zero mastery change, global mean, action-specific mean (with support threshold and intersection evaluation).
  - New API endpoint `GET /ml/evaluation/readiness` exposed in `backend/app/main.py`.
  - 11 new tests added in `tests/test_evaluation_readiness.py` (153 passing tests total).
  - Clean `npm run lint`, `npm run build`, and `pytest` execution. Zero database alterations. No `real_action_model.joblib` created.

- **Phase 5, Step 5 (Completed & Verified 9 Nov 2026):**
  - Real-World Learning Data Collection & Feedback Loop Architecture implemented across backend and frontend.
  - Hardened activity lifecycle: validated `ActivityCreate` schema (positive bounded duration $\le 1440$, score $\in [0, 100]$, errors $\ge 0$, canonical difficulty enum).
  - Row-level concurrency locking (`with_for_update()`) on recommendation sessions during activity submission.
  - End-to-end feedback loop: recommendation generation $\to$ activity logging $\to$ atomic mastery recalculation $\to$ transactional learning outcome attribution $\to$ session evaluation.
  - Preserved server-controlled `is_test` classification and authoritative server snapshots.
  - Verified training record validator concordance: genuine outcomes advance real training dataset and Step 4 evaluation readiness counters.
  - Implemented `GET /analytics/feedback-loop` endpoint exposing conversion funnel, adherence (labeled self-reported), outcome breakdowns, and evaluation readiness progress with learner isolation.
  - Extended frontend API client with `getFeedbackLoopAnalytics`.
  - 18 new comprehensive integration and unit tests added in `tests/test_feedback_loop.py` (176 passing tests total).
  - Phase 5 Step 5 Corrective Audit applied and verified: platform analytics authorization enforced (HTTP 403), target vs remediation skill semantics decoupled across API and frontend, cumulative mastery attribution documented with intervening activity regression coverage, PostgreSQL row-level locking concurrency verified with multi-threaded integration test, and non-finite score rejection (NaN, Inf) enforced.
  - Clean `npm run lint`, `npm run build`, and `pytest` execution. Zero database alterations. No `real_action_model.joblib` created. Synthetic model preserved intact.

- **Phase 5, Step 6 (Next Priority upon user approval):**
  - Offline Model Training, Cross-Validation & Calibration Deployment Pipeline.

