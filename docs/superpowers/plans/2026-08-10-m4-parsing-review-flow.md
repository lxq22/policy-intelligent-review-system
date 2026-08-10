# M4 Parsing and Review Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver real DOCX/PDF parsing, clause persistence, review-source selection, hybrid candidate retrieval, and immutable review-input records for milestone M4.

**Architecture:** Extend the existing FastAPI monolith with isolated parser, storage, retrieval, and review services. Keep format extraction separate from clause segmentation, persist PostgreSQL vectors through pgvector while using a SQLite-compatible JSON variant in tests, and replace the M2 mock review flow with real REST-backed Vue state.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, python-docx, PyMuPDF, jieba, pgvector, PostgreSQL 18, pytest, Vue 3, TypeScript, Pinia, Element Plus, Docker Compose.

## Global Constraints

- Supported inputs are `.docx` and text-layer PDF only; reject `.doc`, images, scanned PDF, OCR, and table parsing.
- Source location uses heading path, original clause number, and paragraph sequence; never expose page numbers.
- Reviewers select one or more clauses and one, multiple, or all four dimensions; never default to full-document review.
- Only user-selected candidate clauses enter conflict-review input.
- Review records have no user-visible task name and no persisted task status.
- M4 creates immutable review-input records but does not create M5 issues, evidence, reports, risk levels, or confidence scores.
- Temporary files never appear in the regulation library and are not automatically deleted in M4.
- Existing M3 permissions remain authoritative: formal regulation upload requires `PERM-001`; ordinary reviewers may upload a temporary review source.
- New production behavior follows test-driven development: test fails for the intended missing behavior before implementation.

---

### Task 1: Generate deterministic DOCX and text-PDF fixtures

**Files:**
- Create: `scripts/generate_m4_fixtures.py`
- Create: `制度审查测试数据集/生成文件/*.docx`
- Create: `制度审查测试数据集/生成文件/*.pdf`
- Test: `event/backend/tests/test_m4_fixtures.py`

**Interfaces:**
- Consumes: the four Markdown files below `制度审查测试数据集/` whose names begin with `待审查_`.
- Produces: `generate_all(source_root: Path, output_root: Path) -> list[tuple[Path, Path]]`, with one DOCX/PDF pair per source.

- [ ] **Step 1: Write the failing fixture contract test**

```python
def test_generated_docx_and_pdf_have_matching_policy_text(generated_fixture_pairs):
    assert len(generated_fixture_pairs) == 4
    for docx_path, pdf_path in generated_fixture_pairs:
        docx_text = extract_docx_text(docx_path)
        pdf_text = extract_pdf_text(pdf_path)
        assert "第一章" in docx_text
        assert normalize_text(docx_text) == normalize_text(pdf_text)
```

- [ ] **Step 2: Run the fixture test and verify RED**

Run: `cd event/backend && .venv/bin/pytest tests/test_m4_fixtures.py -q`

Expected: FAIL because `scripts/generate_m4_fixtures.py` and generated fixture pairs do not exist.

- [ ] **Step 3: Implement deterministic generation**

Implement Markdown cleanup that removes the title marker and explanatory blockquote, maps `## 第一章` to a heading, and writes article paragraphs as body text. Create DOCX with explicit Chinese fonts and PDF with an embedded CJK font. Keep source text unchanged after whitespace normalization.

- [ ] **Step 4: Render and inspect all generated documents**

Run the bundled DOCX renderer for every DOCX and Poppler for every PDF. Inspect every rendered page for missing Chinese glyphs, clipping, overlap, or accidental inclusion of Markdown markers.

- [ ] **Step 5: Run the fixture test and verify GREEN**

Run: `cd event/backend && .venv/bin/pytest tests/test_m4_fixtures.py -q`

Expected: PASS for four matching DOCX/PDF pairs.

- [ ] **Step 6: Commit the fixture generator and fixtures**

```bash
git add scripts/generate_m4_fixtures.py 制度审查测试数据集 event/backend/tests/test_m4_fixtures.py
git commit -m "test: add M4 policy document fixtures"
```

### Task 2: Implement format extraction and replaceable clause segmentation

**Files:**
- Create: `event/backend/app/parsers/__init__.py`
- Create: `event/backend/app/parsers/base.py`
- Create: `event/backend/app/parsers/docx_parser.py`
- Create: `event/backend/app/parsers/pdf_parser.py`
- Create: `event/backend/app/parsers/segmenter.py`
- Test: `event/backend/tests/test_document_parsers.py`

**Interfaces:**
- Produces: `ExtractedParagraph(sequence: int, text: str)` and `DocumentParser.extract(path: Path) -> list[ExtractedParagraph]`.
- Produces: `ParsedClause(original_no: str, title: str, content: str, level: str, heading_path: list[str], paragraph_start: int, paragraph_end: int, sequence: int)`.
- Produces: `ClauseSegmenter.segment(paragraphs: Sequence[ExtractedParagraph]) -> list[ParsedClause]`.
- Raises: `UnsupportedDocumentError`, `ScannedPdfError`, or `DocumentParseError` with user-readable Chinese messages.

- [ ] **Step 1: Write failing parser and segmentation tests**

```python
@pytest.mark.parametrize("suffix", [".docx", ".pdf"])
def test_fixture_preserves_chapter_path_article_number_and_order(fixture_path_for):
    clauses = parse_fixture(fixture_path_for(suffix, "综合审查样例"))
    assert [item.original_no for item in clauses[7:10]] == ["第八条", "第九条", "第十一条"]
    assert clauses[8].heading_path == ["第三章 审批与备案"]
    assert "《专项事项管理制度》第十八条" in clauses[8].content
```

Also test table exclusion, multiline article merging, preamble handling, `.doc` rejection, corrupt DOCX/PDF, and a text-empty PDF raising `ScannedPdfError`.

- [ ] **Step 2: Run parser tests and verify RED**

Run: `cd event/backend && .venv/bin/pytest tests/test_document_parsers.py -q`

Expected: FAIL because parser modules do not exist.

- [ ] **Step 3: Implement minimal extractors and segmenter**

Use `python-docx` for paragraph-only DOCX extraction and PyMuPDF for text blocks ordered by document flow. Use compiled regular expressions for chapter, section, article, paragraph, and item markers. Do not infer a missing article number.

- [ ] **Step 4: Run parser tests and verify GREEN**

Run: `cd event/backend && .venv/bin/pytest tests/test_document_parsers.py -q`

Expected: all format and segmentation tests PASS.

- [ ] **Step 5: Commit parser behavior**

```bash
git add event/backend/app/parsers event/backend/tests/test_document_parsers.py event/backend/pyproject.toml
git commit -m "feat: parse DOCX and text PDF into clauses"
```

### Task 3: Persist files, clauses, parse state, and vectors

**Files:**
- Modify: `event/backend/app/config.py`
- Modify: `event/backend/app/models.py`
- Modify: `event/backend/app/schemas.py`
- Create: `event/backend/app/services/file_storage.py`
- Create: `event/backend/app/services/parsing.py`
- Create: `event/backend/migrations/versions/20260810_0002_m4_parsing.py`
- Modify: `event/backend/tests/conftest.py`
- Test: `event/backend/tests/test_parsing_service.py`

**Interfaces:**
- Produces: `StoredFile(relative_path: str, original_name: str, mime_type: str, size: int, sha256: str)`.
- Produces: `FileStorage.save(upload: UploadFile, namespace: str) -> StoredFile` with path containment and generated disk names.
- Produces: `ParseService.parse_version(db: Session, version_id: int) -> list[Clause]`.
- Produces: `ParseService.parse_temporary_file(db: Session, temporary_file_id: int) -> list[Clause]`.
- Persists: `TemporaryReviewFile`, `Clause`, enriched `RegulationVersion`, and a 256-dimension `Clause.embedding` with SQLite JSON variant and PostgreSQL `Vector(256)`.

- [ ] **Step 1: Write failing persistence tests**

```python
def test_successful_reparse_atomically_replaces_clauses(db, parsed_version):
    old_ids = clause_ids(db, parsed_version.id)
    replace_source_file(parsed_version, "two_articles.docx")
    result = parse_service.parse_version(db, parsed_version.id)
    assert len(result) == 2
    assert not set(old_ids) & set(clause_ids(db, parsed_version.id))
    assert parsed_version.parse_status == "解析成功"
```

Also test SHA-256 metadata, safe relative paths, failed reparse preserving the previous successful clauses, all four parse states, and temporary-file isolation.

- [ ] **Step 2: Run persistence tests and verify RED**

Run: `cd event/backend && .venv/bin/pytest tests/test_parsing_service.py -q`

Expected: FAIL because M4 models and services are absent.

- [ ] **Step 3: Add models and explicit Alembic migration**

Add file metadata and parse fields to `regulation_versions`; add `temporary_review_files` and `clauses`; expand `review_records` only in Task 6. Use database check constraints only for the confirmed parse states and source ownership invariant.

- [ ] **Step 4: Implement safe storage and transactional parsing**

Write uploads to a temporary sibling path, fsync, then atomically rename. During reparse, extract before deleting existing clauses; replace rows and update status in one transaction. On failure, roll back replacement and persist only `解析失败` plus the readable reason when no prior successful result exists.

- [ ] **Step 5: Run migration and persistence tests**

Run: `cd event/backend && .venv/bin/alembic upgrade head`

Run: `cd event/backend && .venv/bin/pytest tests/test_parsing_service.py -q`

Expected: migration succeeds and all persistence tests PASS.

- [ ] **Step 6: Commit persistence layer**

```bash
git add event/backend/app/config.py event/backend/app/models.py event/backend/app/schemas.py event/backend/app/services event/backend/migrations event/backend/tests
git commit -m "feat: persist M4 files and parsed clauses"
```

### Task 4: Expose formal and temporary parsing APIs

**Files:**
- Modify: `event/backend/app/api/regulation_routes.py`
- Create: `event/backend/app/api/parsing_routes.py`
- Modify: `event/backend/app/main.py`
- Modify: `event/backend/app/schemas.py`
- Test: `event/backend/tests/test_parsing_api.py`

**Interfaces:**
- Produces: `POST /api/v1/regulations/{id}/versions/upload` multipart fields `file`, `version`, `effective_date`, and `note`.
- Produces: `GET /api/v1/regulations/{id}/clauses`.
- Produces: `POST /api/v1/regulation-versions/{id}/reparse`.
- Produces: `POST /api/v1/temporary-files` multipart field `file`.
- Produces: `GET /api/v1/temporary-files/{id}` and `/clauses`.
- Produces: `POST /api/v1/temporary-files/{id}/reparse`.

- [ ] **Step 1: Write failing API tests**

```python
def test_temporary_upload_parses_but_never_appears_in_regulation_list(reviewer_client, docx_fixture):
    response = reviewer_client.post(
        "/api/v1/temporary-files",
        files={"file": (docx_fixture.name, docx_fixture.read_bytes(), DOCX_MIME)},
    )
    assert response.status_code == 201
    temporary = response.json()
    assert temporary["parse_status"] == "解析成功"
    assert reviewer_client.get(f"/api/v1/temporary-files/{temporary['id']}/clauses").json()
    assert temporary["original_name"] not in [item["name"] for item in reviewer_client.get("/api/v1/regulations").json()]
```

Also test `PERM-001` on formal upload, reviewer access to temporary upload, unsupported extension, scanned PDF error, and reparse endpoints.

- [ ] **Step 2: Run API tests and verify RED**

Run: `cd event/backend && .venv/bin/pytest tests/test_parsing_api.py -q`

Expected: 404 for missing M4 routes.

- [ ] **Step 3: Implement routes and response schemas**

Keep parse responses synchronous for the M4 prototype while persisting every defined state transition. Return the common JSON error envelope through existing FastAPI exception handling.

- [ ] **Step 4: Run API tests and verify GREEN**

Run: `cd event/backend && .venv/bin/pytest tests/test_parsing_api.py -q`

Expected: all upload, parse, isolation, permission, and reparse tests PASS.

- [ ] **Step 5: Commit parsing API**

```bash
git add event/backend/app/api event/backend/app/main.py event/backend/app/schemas.py event/backend/tests/test_parsing_api.py
git commit -m "feat: expose M4 file parsing APIs"
```

### Task 5: Implement relationship-scoped hybrid retrieval

**Files:**
- Create: `event/backend/app/retrieval/__init__.py`
- Create: `event/backend/app/retrieval/tokenizer.py`
- Create: `event/backend/app/retrieval/embeddings.py`
- Create: `event/backend/app/retrieval/ranking.py`
- Create: `event/backend/app/services/candidates.py`
- Create: `event/backend/app/api/review_routes.py`
- Modify: `event/backend/app/main.py`
- Modify: `event/backend/app/config.py`
- Test: `event/backend/tests/test_candidate_retrieval.py`

**Interfaces:**
- Produces: `DeterministicEmbeddingProvider.embed(text: str) -> list[float]` with exactly 256 normalized values.
- Produces: `rrf(keyword_ids: list[int], vector_ids: list[int], k: int) -> list[tuple[int, float, list[str]]]`.
- Produces: `CandidateService.for_regulation(db, regulation_id, clause_ids) -> list[CandidateClause]`.
- Produces: `CandidateService.for_temporary(db, temporary_file_id, clause_ids, comparison_regulation_ids) -> list[CandidateClause]`.
- Produces: `POST /api/v1/reviews/candidates`.

- [ ] **Step 1: Write failing retrieval tests**

```python
def test_rrf_merges_and_labels_keyword_and_vector_evidence():
    result = rrf([10, 20], [20, 30], k=60)
    assert [item[0] for item in result] == [20, 10, 30]
    assert result[0][2] == ["关键词", "向量"]
```

Add database tests proving deleted, unrelated, and parse-failed regulations are excluded; automatic and manual visible relations are accepted; temporary sources search only explicitly selected comparison regulations.

- [ ] **Step 2: Run retrieval tests and verify RED**

Run: `cd event/backend && .venv/bin/pytest tests/test_candidate_retrieval.py -q`

Expected: FAIL because retrieval modules do not exist.

- [ ] **Step 3: Implement tokenizer, deterministic embeddings, and RRF**

Use jieba tokens plus character bigrams. Hash features with SHA-256 into 256 signed buckets, L2-normalize, and label the model `local-hash-zh-v1`. Keep the provider protocol compatible with a later Zhipu adapter.

- [ ] **Step 4: Implement scoped candidate service and API**

Resolve formal relation scope through `collect_relations`; calculate keyword and cosine rankings only inside that scope. Validate all requested source clauses before ranking and return no configurable threshold as a business promise.

- [ ] **Step 5: Run retrieval tests and verify GREEN**

Run: `cd event/backend && .venv/bin/pytest tests/test_candidate_retrieval.py -q`

Expected: all RRF, scoping, exclusion, and temporary-source tests PASS.

- [ ] **Step 6: Commit retrieval behavior**

```bash
git add event/backend/app/retrieval event/backend/app/services/candidates.py event/backend/app/api/review_routes.py event/backend/app/config.py event/backend/app/main.py event/backend/tests/test_candidate_retrieval.py event/backend/pyproject.toml
git commit -m "feat: recall relationship-scoped candidate clauses"
```

### Task 6: Persist immutable review-input records and numbering

**Files:**
- Modify: `event/backend/app/models.py`
- Modify: `event/backend/app/schemas.py`
- Modify: `event/backend/app/api/review_routes.py`
- Create: `event/backend/app/services/reviews.py`
- Create: `event/backend/migrations/versions/20260810_0003_m4_review_records.py`
- Test: `event/backend/tests/test_review_records.py`

**Interfaces:**
- Produces: `ReviewService.create(db: Session, user: User, payload: ReviewCreate) -> ReviewRecord`.
- Produces: `POST /api/v1/reviews`, `GET /api/v1/reviews`, and `GET /api/v1/reviews/{id}`.
- Accepts dimensions only from `semantic`, `rule`, `conflict`, and `consistency`.
- Stores selected clause and candidate snapshots as JSON arrays containing IDs, names, versions, original numbers, locations, and text.

- [ ] **Step 1: Write failing record tests**

```python
def test_repeated_review_gets_independent_immutable_number_and_snapshot(reviewer_client, parsed_regulation):
    first = create_review(reviewer_client, parsed_regulation)
    second = create_review(reviewer_client, parsed_regulation)
    assert first["record_code"].endswith("-01")
    assert second["record_code"].endswith("-02")
    assert first["id"] != second["id"]
    assert "status" not in first
    assert "task_name" not in first
```

Also test invalid dimensions, source-clause ownership, candidate-scope validation, conflict requiring selected candidates, non-conflict ignoring candidate input, and historical snapshots surviving reparse.

- [ ] **Step 2: Run review tests and verify RED**

Run: `cd event/backend && .venv/bin/pytest tests/test_review_records.py -q`

Expected: FAIL because review creation behavior is absent.

- [ ] **Step 3: Implement model expansion and transactional numbering**

Add a unique constraint on `record_code`, generate `显示名称-YYYYMMDD-NN`, and retry the transaction on a unique conflict. Set `completed_at` at creation because M4 stores a completed input-preparation result, not an asynchronous task.

- [ ] **Step 4: Implement record routes and strict input validation**

Serialize only confirmed M4 fields. Keep report issue counts at zero and do not generate M5 rows.

- [ ] **Step 5: Run review tests and verify GREEN**

Run: `cd event/backend && .venv/bin/pytest tests/test_review_records.py -q`

Expected: all numbering, validation, snapshot, and repeat-review tests PASS.

- [ ] **Step 6: Commit review record behavior**

```bash
git add event/backend/app/models.py event/backend/app/schemas.py event/backend/app/api/review_routes.py event/backend/app/services/reviews.py event/backend/migrations/versions/20260810_0003_m4_review_records.py event/backend/tests/test_review_records.py
git commit -m "feat: save immutable M4 review inputs"
```

### Task 7: Replace Vue M4 mock data with real APIs

**Files:**
- Modify: `event/frontend/src/types/index.ts`
- Modify: `event/frontend/src/stores/data.ts`
- Modify: `event/frontend/src/views/reviewer/RegulationDetailView.vue`
- Modify: `event/frontend/src/views/reviewer/ReviewStartView.vue`
- Modify: `event/frontend/src/views/reviewer/ReviewRecordsView.vue`
- Modify: `event/frontend/src/api/client.ts`
- Create: `event/frontend/src/api/multipart.ts`
- Test: `event/frontend/src/stores/data.test.ts`
- Test: `event/frontend/src/views/reviewer/ReviewStartView.test.ts`

**Interfaces:**
- Produces: store actions `uploadRegulationVersion`, `uploadTemporaryFile`, `loadClauses`, `retryParse`, `loadCandidates`, `createReview`, and `loadReviewRecords`.
- Consumes: the exact M4 REST interfaces from Tasks 4–6.

- [ ] **Step 1: Add Vitest and write failing store tests**

```typescript
it('sends only selected clauses, dimensions, and candidates', async () => {
  const store = useDataStore()
  await store.createReview({
    sourceType: 'regulation',
    regulationId: 1,
    clauseIds: [11],
    dimensions: ['conflict'],
    candidateClauseIds: [21],
  })
  expect(lastJsonBody()).toEqual({
    source_type: 'regulation', regulation_id: 1, temporary_file_id: null,
    clause_ids: [11], dimensions: ['conflict'], candidate_clause_ids: [21],
  })
})
```

Add component tests for temporary upload, parse failure display, disabled navigation without clauses/dimensions/candidates, and the absence of task-status filters.

- [ ] **Step 2: Run frontend tests and verify RED**

Run: `cd event/frontend && pnpm test --run`

Expected: FAIL because M4 store actions and test setup do not exist.

- [ ] **Step 3: Implement typed API and store mapping**

Remove M4 use of `initialRegulations` clauses and `initialRecords`. Keep M5 mock issues isolated to existing demo reports only. Represent numeric backend clause IDs as numbers in new M4 interfaces.

- [ ] **Step 4: Wire regulation detail and review wizard**

Show real parse status, failure reason, clauses, and reparse. In the review wizard support both source types, explicit comparison-regulation selection for temporary conflict review, real candidate cards, and successful input-record creation without fake M5 completion.

- [ ] **Step 5: Run frontend tests, typecheck, and build**

Run: `cd event/frontend && pnpm test --run`

Run: `cd event/frontend && pnpm exec vue-tsc --noEmit`

Run: `cd event/frontend && pnpm build`

Expected: all tests PASS; typecheck and production build exit 0.

- [ ] **Step 6: Commit frontend integration**

```bash
git add event/frontend
git commit -m "feat: connect M4 parsing and review flow UI"
```

### Task 8: Verify Docker/PostgreSQL integration and document M4 delivery

**Files:**
- Modify: `event/backend/Dockerfile`
- Modify: `event/backend/.env.example`
- Modify: `event/compose.yaml`
- Modify: `event/README.md`
- Modify: `AI_IMPLEMENTATION_TASKS.md`
- Create: `event/M4_DELIVERY.md`

**Interfaces:**
- Consumes: `FILE_STORAGE_ROOT`, `RETRIEVAL_TOP_K`, and `RRF_K` environment values.
- Produces: a Compose stack where API storage uses `file-data`, PostgreSQL has the vector extension, and M4 endpoints work through the frontend proxy.

- [ ] **Step 1: Run the full pre-integration suite**

Run: `cd event/backend && .venv/bin/pytest -q`

Run: `cd event/frontend && pnpm test --run && pnpm exec vue-tsc --noEmit && pnpm build`

Expected: all unit tests pass before container verification.

- [ ] **Step 2: Rebuild and migrate the Compose stack**

Run: `cd event && docker compose build`

Run: `cd event && docker compose up -d`

Run: `cd event && docker compose exec api alembic upgrade head`

Expected: `db`, `api`, and `frontend` are healthy and migration `20260810_0002` is at head.

- [ ] **Step 3: Run PostgreSQL-specific integration checks**

Upload one generated DOCX and one generated PDF, confirm vector rows have dimension 256, query candidates across an existing relation, restart the stack, and confirm files, clauses, and review records persist.

- [ ] **Step 4: Run browser end-to-end checks**

Verify formal upload, parse display, temporary upload isolation, clause and dimension selection, conflict candidate selection, review record creation, history listing, and no console errors.

- [ ] **Step 5: Write delivery documentation and milestone status**

Document exact commands, test counts, supported boundaries, generated fixtures, known M5 exclusions, and the local URLs. Update M4 tasks from blocked to complete only when the corresponding verification evidence exists.

- [ ] **Step 6: Run final verification and inspect diff**

Run: `cd event/backend && .venv/bin/pytest -q`

Run: `cd event/frontend && pnpm test --run && pnpm exec vue-tsc --noEmit && pnpm build`

Run: `cd event && docker compose config --quiet`

Run: `git diff --check`

Expected: every command exits 0 with no test failures or whitespace errors.

- [ ] **Step 7: Commit M4 delivery evidence**

```bash
git add AI_IMPLEMENTATION_TASKS.md event
git commit -m "docs: record M4 delivery and verification"
```
