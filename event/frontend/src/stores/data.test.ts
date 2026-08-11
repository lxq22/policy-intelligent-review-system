import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDataStore } from './data'


function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}


describe('M4 data store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('loads parsed clauses from the real regulation endpoint', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response([
      {
        id: 11,
        sequence: 1,
        original_no: '第一条',
        title: '',
        content: '制度正文',
        level: 'article',
        heading_path: ['第一章 总则'],
        paragraph_start: 1,
        paragraph_end: 1,
      },
    ]))
    const store = useDataStore()
    store.regulations.push({
      id: 1,
      name: '测试制度',
      code: '',
      department: '',
      category: '',
      hierarchy: '二级单位制度',
      version: 'V1',
      publishDate: '',
      effectiveDate: '',
      status: '生效中',
      scope: '',
      fileName: '',
      parseStatus: '解析成功',
      clauses: [],
      versions: [],
      relations: [],
      deleted: false,
      updatedAt: '',
    })

    const clauses = await store.loadClauses(1)

    expect(clauses[0]).toMatchObject({ id: 11, originalNo: '第一条' })
    expect(store.regulations[0].clauses[0].location).toBe('第一章 总则 > 第一条')
  })

  it('sends only selected clauses, dimensions, and candidates', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({
      id: 7,
      record_code: '测试制度-20260810-01',
      source_type: 'regulation',
      regulation_id: 1,
      regulation_name: '测试制度',
      dimensions: ['conflict'],
      source_snapshot: [{ clause_id: 11 }],
      candidate_snapshot: [{ clause_id: 21 }],
      created_at: '2026-08-10T10:00:00',
      completed_at: '2026-08-10T10:00:00',
    }))
    const store = useDataStore()

    await store.createReview({
      sourceType: 'regulation',
      regulationId: 1,
      clauseIds: [11],
      dimensions: ['conflict'],
      candidateClauseIds: [21],
      comparisonRegulationIds: [],
    })

    const request = fetchMock.mock.calls[0]
    expect(request[0]).toContain('/reviews')
    expect(JSON.parse((request[1] as RequestInit).body as string)).toEqual({
      source_type: 'regulation',
      regulation_id: 1,
      temporary_file_id: null,
      clause_ids: [11],
      dimensions: ['conflict'],
      candidate_clause_ids: [21],
      comparison_regulation_ids: [],
    })
    expect(store.records[0].id).toBe('测试制度-20260810-01')
  })

  it('creates a regulation with its real initial file', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => response({
        id: 9,
        name: '上传制度',
        code: 'TEST-009',
        version: 'V1.0',
        status: '生效中',
        file_name: '上传制度.docx',
        parse_status: '解析成功',
        deleted: false,
        updated_at: '2026-08-11T10:00:00',
        versions: [],
        relations: [],
      }, 201))
      .mockImplementationOnce(() => response([]))
    const store = useDataStore()
    const file = new File(['制度正文'], '上传制度.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    const created = await store.createRegulationWithFile({
      name: '上传制度',
      code: 'TEST-009',
      version: 'V1.0',
      status: '生效中',
      hierarchy: '二级单位制度',
      scope: '当前单位',
    }, file)

    const request = fetchMock.mock.calls[0]
    expect(request[0]).toContain('/regulations/with-file')
    const body = (request[1] as RequestInit).body as FormData
    expect(body.get('file')).toBe(file)
    expect(body.get('name')).toBe('上传制度')
    expect(body.get('version')).toBe('V1.0')
    expect(body.get('status')).toBe('生效中')
    expect(created.id).toBe(9)
    expect(store.regulations[0].fileName).toBe('上传制度.docx')
  })
})
