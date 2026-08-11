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

  it('starts with no mock issues and loads the exact historical report', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => response([
        {
          id: 7,
          record_code: '第一份-01',
          source_type: 'regulation',
          regulation_name: '第一份',
          dimensions: ['semantic'],
          source_snapshot: [{ clause_id: 1 }],
          candidate_snapshot: [],
          created_at: '2026-08-11T10:00:00',
          completed_at: '2026-08-11T10:01:00',
          created_by_name: '李明',
          problem_count: 1,
          has_report: true,
        },
        {
          id: 8,
          record_code: '第二份-01',
          source_type: 'regulation',
          regulation_name: '第二份',
          dimensions: ['rule'],
          source_snapshot: [{ clause_id: 2 }],
          candidate_snapshot: [],
          created_at: '2026-08-11T11:00:00',
          completed_at: '2026-08-11T11:01:00',
          created_by_name: '王芳',
          problem_count: 1,
          has_report: true,
        },
      ]))
      .mockImplementationOnce(() => response([
        {
          id: 88,
          review_record_id: 8,
          dimension: 'rule',
          original: '第二份制度原文。。',
          location: '第三条',
          explanation: '存在重复标点。',
          consequence: '影响规范性。',
          suggestion: '删除重复标点。',
          status: '待处理',
          details: { rule_category: '行文规范' },
          created_at: '2026-08-11T11:01:00',
          histories: [],
        },
      ]))
    const store = useDataStore()

    expect(store.issues).toEqual([])
    await store.loadReviewRecords()
    const record = await store.loadReviewReport('第二份-01')

    expect(record.id).toBe('第二份-01')
    expect(store.issues).toHaveLength(1)
    expect(store.issues[0]).toMatchObject({ id: '88', dimension: 'rule', issueType: '行文规范' })
    expect(store.issues[0].original).toBe('第二份制度原文。。')
  })

  it('persists issue actions through the backend instead of changing mock state', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() => response({
      id: 88,
      review_record_id: 8,
      dimension: 'rule',
      original: '制度原文。。',
      location: '第三条',
      explanation: '存在重复标点。',
      consequence: '影响规范性。',
      suggestion: '删除重复标点。',
      status: '已采纳',
      details: { rule_category: '行文规范' },
      created_at: '2026-08-11T11:01:00',
      histories: [{ id: 1, actor_name: '李明', action: '采纳修改建议', created_at: '2026-08-11T11:02:00' }],
    }))
    const store = useDataStore()

    await store.processIssue('88', '采纳修改建议')

    expect(fetchMock.mock.calls[0][0]).toContain('/reviews/issues/88/actions')
    expect(JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string)).toEqual({
      action: '采纳修改建议',
      opinion: null,
    })
    expect(store.issues[0].status).toBe('已采纳')
    expect(store.issues[0].histories[0].actor).toBe('李明')
  })

  it('consumes live review progress and marks the record report as available', async () => {
    const stream = [
      'event: started\ndata: {"message":"开始智能审查"}\n\n',
      'event: heartbeat\ndata: {"review_id":9}\n\n',
      'event: dimension\ndata: {"message":"semantic"}\n\n',
      'event: completed\ndata: {"problem_count":3}\n\n',
    ].join('')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(stream, {
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
    }))
    const store = useDataStore()
    const record = {
      id: '测试制度-01',
      internalId: 9,
      regulationId: 1,
      regulationName: '测试制度',
      clauseCount: 1,
      dimensions: ['semantic' as const],
      createdBy: '李明',
      createdAt: '',
      completedAt: '',
      problemCount: 0,
      hasReport: false,
    }
    const progress: string[] = []

    await store.executeReview(record, (message) => progress.push(message))

    expect(fetchMock.mock.calls[0][0]).toContain('/reviews/9/execute')
    expect(progress).toEqual(['开始智能审查', 'semantic'])
    expect(record.hasReport).toBe(true)
    expect(record.problemCount).toBe(3)
  })

  it('does not mark a report successful when the progress stream ends early', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(
      'event: started\ndata: {"message":"开始智能审查"}\n\n',
      { status: 200, headers: { 'Content-Type': 'text/event-stream' } },
    ))
    const store = useDataStore()
    const record = {
      id: '中断测试-01', internalId: 10, regulationId: 1, regulationName: '中断测试',
      clauseCount: 1, dimensions: ['semantic' as const], createdBy: '李明',
      createdAt: '', completedAt: '', problemCount: 0, hasReport: false,
    }

    await expect(store.executeReview(record)).rejects.toThrow('连接中断')
    expect(record.hasReport).toBe(false)
    expect(record.problemCount).toBe(0)
  })
})
