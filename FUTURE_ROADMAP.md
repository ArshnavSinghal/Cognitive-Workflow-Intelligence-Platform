# CWIP --- Future Implementation Roadmap

**Version:** 1.0  
**Audited:** 31 October 2026  
**Auditor:** Lead Software Architect & Senior Full-Stack AI Engineer  

This roadmap outlines the prioritized engineering phases required to transition CWIP from its current prototype state into a production-grade adaptive learning intelligence platform.

---

## Phase 1: Dashboard Adherence KPI Integration & ESLint Cleanup [COMPLETED]

**Status:** Completed & Verified (31 October 2026)  
**Deliverables Completed:**
1. **Frontend Overview Metrics Integration:**
   - Consumed live adherence fields (`adherence_rate`, `recommendations_followed`, `recommendations_not_followed`, `total_real_evaluated`) from `GET /learning-outcomes`.
   - Added responsive "Action adherence rate" KPI card with percentage, `${followed} / ${total} followed (${notFollowed} not followed)`, explicit label `"Self-reported by learner"`, and disclaimer `"Adherence tracking only · Not learning effectiveness"`.
   - Handled zero real outcomes, loading states, and API error states gracefully.
2. **Dashboard Synchronization:**
   - Verified that submitting a recommended activity automatically re-queries `/learning-outcomes` and refreshes live adherence metrics alongside mastery and activities.
3. **Frontend Clean Lint & Build:**
   - Resolved the unused `outcomesError` ESLint error by rendering it when errors occur.
   - `npm run lint` passes with 0 errors and 0 warnings.
   - `npm run build` generates production bundle in 1.38s.
4. **Backend Regression & Integration Tests:**
   - Added 5 unit/regression tests in `tests/test_api.py` covering zero outcomes, all followed (100%), mixed adherence, test outcome exclusion, and user-level data isolation.
   - Added 1 full end-to-end integration lifecycle test (`test_full_recommendation_activity_adherence_lifecycle`).
   - Test suite baseline upgraded from 68 to **74 passed, 1 warning**.

---

## Phase 2: Learning Effectiveness Analytics [COMPLETED]

**Status:** Completed & Verified (31 October 2026)  
**Deliverables Completed:**
1. **Backend Effectiveness Aggregation Endpoint (`GET /analytics/effectiveness`):**
   - Implemented in `backend/app/main.py` with authentication and user-level data isolation.
   - Strictly excludes synthetic/test outcomes (`is_test=False`).
   - Supports optional `skill_id` query parameter for skill-specific filtering.
   - Gracefully handles empty outcomes, missing sessions, and zero divisions.
   - Computes overall sample counts, average $\Delta \text{mastery}$, positive, neutral, and negative outcomes.
   - Groups metrics by skill, recommended action, and actual action taken.
   - Computes comparative analysis: Recommendations Followed vs Alternative / Divergent Actions.
   - Includes mandatory observational notice caveats on observational data.
2. **Frontend Effectiveness Visualizations (`frontend/src/App.jsx`, `frontend/src/App.css`):**
   - Integrated into the "Learning Progress" dashboard view.
   - Top KPI cards: Average mastery change (`pp`), Positive, Neutral, and Negative outcome counts.
   - Recommendation adherence comparison cards (`.comparison-card.followed` vs `.comparison-card.not-followed`).
   - Skill-wise breakdown table and tabbed action breakdown table (Actual action vs Recommended action).
   - Observational disclaimer card (`ShieldAlert`) preventing false causal attribution.
   - Loading, empty, and error states handled gracefully.
3. **Frontend Quality Verification:**
   - `npm --prefix frontend run lint` passed with 0 errors and 0 warnings.
   - `npm --prefix frontend run build` passed cleanly.
4. **Backend Regression Test Coverage:**
   - Added 7 dedicated regression tests to `tests/test_api.py`.
   - Test suite baseline expanded from 74 to **81 passed, 1 warning**.

---

## Phase 3: Dynamic Skill Catalogue & Profile Endpoints [COMPLETED]

**Status:** Completed & Verified (1 November 2026)  
**Deliverables Completed:**
1. **Backend Skill Catalogue & Profile Endpoints (`backend/app/main.py`):**
   - `GET /skills`: Dynamically lists all platform skills with optional authentication support (populating enrollment and mastery metadata for authenticated learners).
   - `GET /skills/{skill_id}`: Retrieves individual skill details.
   - `POST /skills/{skill_id}/enroll`: Safely enrolls the authenticated learner into a skill with duplicate enrollment rejection (enforced via transactional application logic; no database migration required).
   - `GET /skills/{skill_id}/profile`: Returns comprehensive empirical learner profile for a skill, including mastery, confidence, trend, total activities, recent activity details, real evaluated outcome counts (positive, neutral, negative), average $\Delta \text{mastery}$ (non-fabricated, `None` if zero outcomes), and recommendation adherence rate (`None` if zero outcomes).
2. **Frontend Dynamic Integration (`frontend/src/App.jsx`, `frontend/src/App.css`, `frontend/src/api.js`):**
   - Eliminated hardcoded skill array in `frontend/src/App.jsx`.
   - Upgraded `MySkills` view to render enrolled skills (with progress tracks, deep analytics, and recommendation CTAs) alongside available unenrolled skills (with "Enroll in skill" CTA).
   - Added interactive `SkillProfileModal` displaying enrollment timestamp, mastery, recent activity, outcome distributions, and adherence metrics with accessibility and keyboard support.
   - Dynamic synchronization: submitting an activity automatically refreshes `/skills` and updates progress bars.
   - Quality checks: `npm run lint` clean (0 errors, 0 warnings), `npm run build` clean.
3. **Automated Backend Regression Suite (`tests/test_api.py`):**
   - Added 11 dedicated integration tests covering catalogue retrieval, individual skill queries, successful enrollment, duplicate rejection, 404s for unknown IDs, user data isolation, empty learner profiles, populated metric calculations, and authentication enforcement.
   - Total test suite expanded from 81 to **92 passed, 1 warning**.
4. **Phase 3 Corrective Security & Data-Integrity Patch (1 November 2026):**
   - **FIX 1 (M-1 - Concurrency Serialization):** In `backend/app/main.py:enroll_in_skill`, acquired PostgreSQL row-level lock on `User` via SQLAlchemy `with_for_update()`, serializing concurrent enrollment attempts per learner. Added transactional `IntegrityError` rollback handling returning clean HTTP 400.
   - **FIX 2 (M-2 - Authorization Boundary):** In `backend/app/main.py:create_skill`, restricted global skill creation from ordinary learners returning HTTP 403 (`Administrative privileges required`). Validated `SkillCreate` schema in `backend/app/schemas.py` (whitespace trimming, `min_length=2`).
   - **FIX 3 (L-1 - Dynamic Recommendation Targeting):** In `frontend/src/App.jsx:RecommendationsPage`, eliminated hardcoded skill fallback. Added target skill selector across enrolled skills and clear 0-enrolled empty state with catalogue navigation CTA.
   - Added 5 dedicated tests in `tests/test_api.py` verifying learner 403 rejection, unauthenticated 403, schema validation, integrity rollback, and IntegrityError constraint classification. Test baseline expanded to **97 passed, 1 warning**.

---

## Phase 4: Prerequisite Graph Intelligence & NetworkX Integration [COMPLETED]

**Status:** Completed & Verified (1 November 2026)  
**Deliverables Completed:**
1. **NetworkX DAG Architecture (`backend/app/ml/skill_graph.py`):**
   - Integrated `networkx==3.7` into virtual environment and pinned in `requirements.txt` & `requirements-lock.txt`.
   - Directed edge convention: `Prerequisite -> Dependent` (`parent_skill_id -> child_skill_id`).
   - Upstream traversal via `nx.ancestors` and `G.predecessors`; downstream traversal via `nx.descendants` and `G.successors`.
   - Graph construction pulls isolated skills as valid nodes.
   - Pre-insert cycle validation (`validate_dependency_addition`): rejects self-loops, duplicate edges, and cycle-creating edges (`nx.has_path(G, target, parent)`).
   - Topological sorting (`get_topological_order`) via `nx.topological_sort`.
   - Shortest path resolution (`get_dependency_path`) with path IDs, names, and hop distances.
2. **Deterministic Bottleneck Scoring & Multi-Hop Diagnosis:**
   - Designed and implemented deterministic 5-factor bottleneck scoring formula:
     $$\text{Score} = \max(0, 1 - \text{mastery}) \times \text{strength} \times [1 + 0.2(d - 1)] \times [1 - 0.4 \times \text{confidence}] \times [1 + 0.1 \times \min(k_{\text{downstream}}, 5)]$$
   - Multi-hop diagnosis (`diagnose_prerequisites`): evaluates transitive ancestors, identifies weak prerequisites ($\text{mastery} < 0.60, \text{risk} \ge 0.30$), identifies the primary bottleneck, and generates explainable diagnostic text differentiating direct gaps from root foundational blockers.
   - Enforces strict user isolation; does not fabricate unearned progress for unenrolled prerequisites.
3. **API Integration & Security Authorization (`backend/app/main.py`, `backend/app/schemas.py`):**
   - Configured `POST /skill-dependencies` administrative authorization boundary: disabled dependency creation for ordinary client learners returning HTTP 403 (`Global skill dependency creation is disabled. Administrative privileges required.`). Preserved internal graph seeding and validation utilities until formal RBAC is introduced.
   - Upgraded `GET /skills/{id}/gap-analysis` with multi-hop diagnosis while preserving existing schema fields.
   - Upgraded `GET /skills/{id}/recommendation` to detect weak prerequisites, prioritize `practice_prerequisite`, link `RecommendationSession`, and generate explainable root-cause guidance.
   - Added 5 new endpoints: `GET /skills/{id}/prerequisites`, `GET /skills/{id}/descendants`, `GET /skills/{id}/diagnosis`, `GET /skills/{source}/path/{target}`, `GET /skills/graph/topological`.
4. **Frontend Integration (`frontend/src/App.jsx`, `frontend/src/App.css`, `frontend/src/api.js`):**
   - Added API wrapper functions for prerequisites, diagnosis, path, and topological ordering.
   - Integrated Prerequisite & Dependency Intelligence Panel into `SkillProfileModal`: renders primary bottleneck alert (with "Target bottleneck →" CTA), healthy/foundational indicators, distance badges, and prerequisite cards.
   - Upgraded `RecommendationsPage` to render primary prerequisite bottleneck warnings and dependency chains.
   - Added comprehensive CSS styling for prerequisite nodes, badges, and dependency paths.
   - Verified zero ESLint errors and clean Vite production build.
5. **Automated Test Coverage & Security Verification:**
   - Created `tests/test_skill_graph.py` with 12 comprehensive unit and intelligence tests.
   - Added 8 integration tests in `tests/test_api.py` covering graph traversal, multi-hop recommendation, cycle rejection, and authorization boundaries (HTTP 403 for learners, 401/403 for unauthenticated).
   - Test suite baseline upgraded from 97 to **117 passed, 1 warning in 18.88s**.

---

## Phase 5: Real-Data ML Pipeline & Model Maturation (Priority 5)

**Goal:** Transition from synthetic policy imitation to genuine learner intelligence once sufficient data is accumulated.

### Tasks
1. **Target Formulation & Clarification:**
   - Clarify the three distinct ML targets:
     - *Policy Imitation:* Predict what action the current rule engine would recommend (Current).
     - *Adherence Prediction:* Predict probability $P(\text{adhere} \mid \text{features}, \text{action})$.
     - *Effectiveness Prediction:* Predict expected $\Delta \text{mastery}$ given $(\text{state}, \text{action})$.
2. **Data Accumulation Gates:**
   - Accumulate $\ge 50$ real learner outcomes across multiple skills and action types.
3. **Model Validation & Evaluation:**
   - Implement cross-validation with time-based or user-grouped splits to prevent data leakage.
   - Compute F1-score, precision, recall, and ROC-AUC against baseline random/majority-class models.
4. **Safe Deployment & Rollback:**
   - Build a model registry and configuration flag (`CWIP_MODEL_SOURCE="real"|"synthetic"`).
   - Only activate `real_action_model.joblib` after offline evaluation outperforms heuristic baselines.

---

## Phase 6: Architecture Hardening & Production Readiness (Priority 6)

**Goal:** Harden security, database lifecycle, and deployment infrastructure.

### Tasks
1. **Decouple DDL from Import:**
   - Remove `Base.metadata.create_all(bind=engine)` from the top level of `backend/app/main.py`.
   - Place table creation inside a FastAPI startup lifespan handler or explicit migration command.
2. **Security & JWT Hardening:**
   - Move `SECRET_KEY` from `auth.py` to environment variables (`.env`).
   - Add token expiration (`exp` claim) with configurable TTL (e.g. 24 hours) and refresh token mechanics.
3. **Database Migration Tooling:**
   - Initialize Alembic (`alembic init`) in `backend/` to manage future schema revisions safely.
4. **Containerization & Deployment:**
   - Author a root `Dockerfile` (multi-stage build for frontend & backend) and `docker-compose.yml` (PostgreSQL + CWIP API + Vite static server).
   - Configure production CORS and environment secret injection.
