# M5 GLM Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute four-dimensional reviews with local rules and GLM‑4.7, persist validated issues and human actions, stream progress, and replace mock reports with real data.

**Architecture:** Review records keep immutable M4 input snapshots. A provider-neutral chat adapter sends one structured request per selected dimension; an orchestrator validates clause references, retries malformed output once, and atomically stores issues. FastAPI exposes SSE execution plus report/action APIs, while Vue consumes those APIs and renders only record-specific results.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, httpx, PostgreSQL, Vue 3, Pinia, Element Plus, Vitest, pytest, Docker Compose.

## Global Constraints

- Default deployment model is `glm-4.7`; API base URL, key, model, and timeout come from environment variables.
- API keys never enter source code, logs, fixtures, screenshots, or Git.
- Rule matching checks only text structure, clause numbering, and writing norms.
- Conflict review uses only user-selected candidate clauses.
- No risk level, confidence score, visual layout, table, scanned-file, or OCR feature.
- Model output must reference submitted snapshot clause IDs; the system supplies original text and evidence locations from trusted snapshots.
- Incomplete or invalid model output is retried once and never persisted as a partial report.

---

### Task 1: M5 issue persistence and migration

**Files:**
- Create: `backend/migrations/versions/20260811_0004_m5_review_issues.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_m5_review_issues.py`

**Interfaces:**
- Produces `ReviewIssue`, `ReviewIssueHistory`, `ReviewIssueOut`, and `IssueActionIn`.
- `ReviewIssue.details` stores dimension-only fields; common fields remain typed columns.

- [ ] Write a failing model/API-shape test that creates one issue with a history and validates all common and dimension-specific output fields.
- [ ] Run `.venv/bin/pytest -q tests/test_m5_review_issues.py` and verify failure because M5 models are absent.
- [ ] Add issue/history models, relationships, schemas, and Alembic upgrade/downgrade; migration resets old M4 `completed_at` values because those records have no real results.
- [ ] Run the focused test and `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` against the test database.
- [ ] Commit with `feat: persist M5 review issues`.

### Task 2: Provider-neutral GLM‑4.7 adapter

**Files:**
- Create: `backend/app/providers/chat.py`
- Modify: `backend/app/config.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_m5_review_issues.py`

**Interfaces:**
- Produces `ChatModelProvider.complete(messages: list[dict], response_format: dict) -> dict`.
- Produces `OpenAICompatibleChatProvider` using `/chat/completions`, Bearer authentication, JSON mode, and optional GLM thinking configuration.

- [ ] Write failing tests for request URL, headers, model `glm-4.7`, JSON response format, success parsing, missing API key, timeout, authentication failure, and malformed provider response.
- [ ] Run the provider tests and verify they fail because the adapter is absent.
- [ ] Implement the protocol, provider errors, httpx request, response extraction, and environment configuration without logging request content or secrets.
- [ ] Run focused provider tests and confirm all pass.
- [ ] Commit with `feat: add GLM compatible chat provider`.

### Task 3: Four-dimensional rules and orchestration

**Files:**
- Create: `backend/app/reviewing/local_rules.py`
- Create: `backend/app/reviewing/prompts.py`
- Create: `backend/app/reviewing/schemas.py`
- Create: `backend/app/services/review_execution.py`
- Modify: `backend/app/services/reviews.py`
- Modify: `backend/tests/test_m5_review_issues.py`

**Interfaces:**
- Produces `ReviewExecutionService.execute(db, review_id, provider) -> list[ReviewIssue]`.
- Produces dimension prompts whose outputs reference `source_clause_id`, optional evidence clause IDs, explanation, consequence, suggestion, and evidence insufficiency.

- [ ] Write failing tests with a fake provider for semantic ambiguity, rule hints, conflict candidate restriction, consistency evidence, no-problem output, invalid clause reference, malformed JSON retry, and all-or-nothing persistence.
- [ ] Run focused orchestration tests and verify expected failures.
- [ ] Implement local ambiguity/rule hints, dimension prompts, Pydantic output validation, trusted snapshot mapping, one correction retry, issue replacement on re-execution, and atomic persistence.
- [ ] Change M4 record creation so `completed_at` remains null until real M5 execution succeeds.
- [ ] Run focused tests plus `tests/test_review_records.py` and confirm all pass.
- [ ] Commit with `feat: execute four-dimensional reviews`.

### Task 4: SSE execution, report, and action APIs

**Files:**
- Modify: `backend/app/api/review_routes.py`
- Modify: `backend/app/serializers.py`
- Modify: `backend/tests/test_m5_review_issues.py`

**Interfaces:**
- `POST /api/v1/reviews/{id}/execute` returns SSE events: `started`, `dimension`, `saving`, `completed`, or `failed`.
- `GET /api/v1/reviews/{id}` returns record summary including creator and problem count.
- `GET /api/v1/reviews/{id}/issues` returns record-specific issues.
- `POST /api/v1/reviews/issues/{issue_id}/actions` persists adopt, ignore, or opinion actions.

- [ ] Write failing API tests for successful SSE, missing API configuration, failed execution without completion, report isolation, invalid record 404, adopt/ignore/opinion histories, and reviewer authentication.
- [ ] Run focused API tests and verify failure.
- [ ] Implement SSE with a fresh database session inside the generator, issue/report queries, summary serialization, and action persistence using the authenticated user identity.
- [ ] Run the focused API tests and all backend tests.
- [ ] Commit with `feat: expose M5 review execution APIs`.

### Task 5: Frontend data integration and real report

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/stores/data.ts`
- Modify: `frontend/src/stores/data.test.ts`
- Modify: `frontend/src/views/reviewer/ReviewStartView.vue`
- Modify: `frontend/src/views/reviewer/ReviewRecordsView.vue`
- Modify: `frontend/src/views/reviewer/ReviewReportView.vue`
- Create: `frontend/src/views/reviewer/ReviewReportView.test.ts`

**Interfaces:**
- Produces `streamApi(path, options, onEvent)` for SSE-over-fetch.
- Produces store methods `executeReview`, `loadReviewReport`, and asynchronous `processIssue`/`addOpinion`.
- Report route resolves the exact record ID and never falls back to another record.

- [ ] Write failing store/view tests for streamed progress, success redirect, failure feedback, record result badges, exact report lookup, four-dimensional mapping, empty dimension, insufficient evidence, and persisted actions.
- [ ] Run focused Vitest tests and verify failure due to mock/global report behavior.
- [ ] Implement SSE parsing, issue mapping, real report loading, progress UI, report action calls, exact 404 handling, and conditional “查看报告”. Remove `initialIssues` from the live store.
- [ ] Run all frontend tests and `pnpm build`.
- [ ] Commit with `feat: connect real M5 review reports`.

### Task 6: Docker configuration and complete verification

**Files:**
- Modify: `event/compose.yaml`
- Modify: `backend/.env.example`
- Modify: `backend/app/main.py`
- Modify: `AI_IMPLEMENTATION_TASKS.md`

**Interfaces:**
- Compose passes `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_TIMEOUT_SECONDS`, and `LLM_THINKING_ENABLED` to the API container.
- Health response reports milestone `M5` without exposing whether a key is configured.

- [ ] Add Docker environment wiring, M5 health version, and concise milestone completion notes.
- [ ] Run backend tests, frontend tests, production build, Alembic round-trip, and `docker compose config`.
- [ ] Rebuild Docker and verify the no-key failure path plus report pages with automated fake-provider tests.
- [ ] Ask the user to place the real key in local `event/.env`, then run one GLM‑4.7 test-dataset review without printing the key or full sensitive request.
- [ ] Verify browser flows, console health, Docker health, Git diff, and secret scans; commit with `chore: complete M5 integration`.
