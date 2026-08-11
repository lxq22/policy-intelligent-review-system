# Regulation Upload and Clause Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a real file mandatory when creating a regulation, show selected files clearly, and preview parsed temporary-file clauses before clause selection.

**Architecture:** Add one multipart backend endpoint that creates a regulation, stores its initial version, parses it, and removes the incomplete record if parsing fails. Reuse the existing temporary upload API, but trigger it immediately on file selection and render the returned clauses in the source step. Keep existing edit and later-version flows unchanged.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Pinia, Element Plus, pytest, Vitest.

## Global Constraints

- New regulations require a `.docx` or selectable-text PDF file.
- Temporary files never enter the regulation library.
- Scanned PDFs, images, `.doc`, and OCR-dependent files remain unsupported.
- File replacement clears all clause and candidate selections.
- Do not implement AI analysis or report generation in this change.

---

### Task 1: Atomic initial regulation upload

**Files:**
- Modify: `backend/tests/test_parsing_api.py`
- Modify: `backend/app/api/regulation_routes.py`
- Modify: `backend/app/services/file_storage.py`

**Interfaces:**
- Produces: `POST /api/v1/regulations/with-file` accepting multipart form fields plus required `file`.
- Produces: `FileStorage.delete(relative_path: str) -> None` for cleanup after failed creation.

- [ ] **Step 1: Write failing API tests**

Add tests proving that multipart creation returns a parsed regulation and clauses, rejects unsupported files, requires upload permission, and leaves no visible regulation after parsing failure.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/pytest -q tests/test_parsing_api.py -k "create_regulation_with_file"`

Expected: FAIL because `/regulations/with-file` does not exist.

- [ ] **Step 3: Implement file cleanup and the multipart endpoint**

Parse optional form values into the existing `Regulation` fields, validate the file before creating data, save the initial `RegulationVersion`, run `ParseService.parse_version`, and add the operation log only after success. On failure, delete the created regulation, commit the cleanup, remove the stored file, and return the readable 422 message.

- [ ] **Step 4: Run focused and parsing regression tests**

Run: `.venv/bin/pytest -q tests/test_parsing_api.py tests/test_parsing_service.py tests/test_document_parsers.py`

Expected: PASS.

- [ ] **Step 5: Commit backend behavior**

Commit message: `feat: create regulations from uploaded files`

### Task 2: Frontend data store for multipart regulation creation

**Files:**
- Modify: `frontend/src/stores/data.test.ts`
- Modify: `frontend/src/stores/data.ts`

**Interfaces:**
- Produces: `createRegulationWithFile(input, file): Promise<Regulation>`.
- Consumes: `POST /regulations/with-file` from Task 1.

- [ ] **Step 1: Write a failing store test**

Assert that `createRegulationWithFile` sends a `FormData` request containing the real `File`, name, version, dates, IDs, status, and scope, then stores the returned regulation.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `pnpm test -- src/stores/data.test.ts`

Expected: FAIL because the store method does not exist.

- [ ] **Step 3: Implement the store method**

Build multipart fields from the existing regulation form mapping, call `/regulations/with-file`, map the response, insert it into the regulation list, and load its clauses.

- [ ] **Step 4: Run the store tests**

Run: `pnpm test -- src/stores/data.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit the store integration**

Commit message: `feat: submit initial regulation files`

### Task 3: Real upload control in the new-regulation dialog

**Files:**
- Create: `frontend/src/components/SelectedFileCard.vue`
- Create: `frontend/src/views/reviewer/RegulationListView.test.ts`
- Modify: `frontend/src/views/reviewer/RegulationListView.vue`

**Interfaces:**
- `SelectedFileCard` consumes `file: File`, `status`, and optional `message`; emits `remove` and `replace`.
- Consumes: `createRegulationWithFile` from Task 2.

- [ ] **Step 1: Write failing component/view tests**

Verify that saving without a file shows “请上传制度文件”, selecting a file renders its name inside the upload area, and create mode calls `createRegulationWithFile` while edit mode keeps the existing metadata-only save.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `pnpm test -- src/views/reviewer/RegulationListView.test.ts`

Expected: FAIL because the real upload control and file requirement are absent.

- [ ] **Step 3: Implement the shared file card and dialog behavior**

Replace the file-name input with a full-width drag uploader in create mode, show the selected file inside it, support remove/replace, disable duplicate submission, rename the primary action to “保存并解析”, and route to the parsed regulation detail after success. Keep edit mode free of the mandatory file control.

- [ ] **Step 4: Run focused frontend tests**

Run: `pnpm test -- src/views/reviewer/RegulationListView.test.ts src/stores/data.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit the regulation dialog UI**

Commit message: `feat: add real regulation file upload`

### Task 4: Immediate temporary parsing and clause preview

**Files:**
- Modify: `frontend/src/views/reviewer/ReviewStartView.test.ts`
- Modify: `frontend/src/views/reviewer/ReviewStartView.vue`
- Reuse: `frontend/src/components/SelectedFileCard.vue`

**Interfaces:**
- Consumes: existing `uploadTemporaryFile(file): Promise<TemporaryReviewFile>`.
- Produces: visible `uploadState` and parsed-clause preview in review step 1.

- [ ] **Step 1: Write failing review-flow tests**

Verify that file selection immediately calls `uploadTemporaryFile`, the file card displays inside the upload area, successful parsing shows the clause count and preview, and removing/replacing the file clears old clauses, selected clauses, candidates, and comparison state.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pnpm test -- src/views/reviewer/ReviewStartView.test.ts`

Expected: FAIL because upload currently waits for “下一步” and no preview is rendered.

- [ ] **Step 3: Implement immediate parsing and preview**

Make the upload change handler asynchronous, maintain idle/parsing/success/error state, render the selected file card within the upload box, show parsed clauses in collapsed Element Plus panels, and allow next only when parsing succeeded with at least one clause.

- [ ] **Step 4: Run focused and full frontend tests**

Run: `pnpm test`

Expected: PASS.

- [ ] **Step 5: Commit the temporary upload UX**

Commit message: `feat: preview temporary file clauses`

### Task 5: Full verification and rendered QA

**Files:**
- Verify only; do not commit screenshots or temporary scripts.

**Interfaces:**
- Verifies both completed user flows against the running Docker application.

- [ ] **Step 1: Run all backend tests**

Run: `.venv/bin/pytest -q`

Expected: PASS.

- [ ] **Step 2: Run frontend tests and production build**

Run: `pnpm test && pnpm build`

Expected: PASS without warnings or type errors.

- [ ] **Step 3: Validate the rendered regulation flow**

Use the in-app Browser to test `制度库 → 新增制度 → 选择文件 → 保存并解析 → 制度详情 → 解析条款`.

- [ ] **Step 4: Validate the rendered temporary review flow**

Use the in-app Browser to test `发起审查 → 临时上传 → 文件卡片 → 条款预览 → 下一步 → 指定条款`.

- [ ] **Step 5: Check desktop, mobile, console, and repository status**

Confirm no clipping, framework overlay, relevant console warning/error, or unrelated source change. Save QA screenshots outside the repository.
