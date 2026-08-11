import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiRequest, jsonBody, streamApi } from '../api/client'
import { multipartBody } from '../api/multipart'
import type {
  CandidateClause,
  Clause,
  DimensionKey,
  MasterDataItem,
  OperationLog,
  PermissionSet,
  Regulation,
  RelationSuggestion,
  ReviewIssue,
  ReviewCreateInput,
  ReviewRecord,
  Role,
  UnitItem,
  User,
  TemporaryReviewFile,
} from '../types'

interface ApiVersion {
  id: number
  version?: string
  effective_date?: string
  file_name?: string
  note?: string
  parse_status?: Regulation['parseStatus']
}

interface ApiClause {
  id: number
  sequence: number
  original_no: string
  title: string
  content: string
  level: string
  heading_path: string[]
  paragraph_start: number
  paragraph_end: number
}

interface ApiTemporaryFile {
  id: number
  original_name: string
  parse_status: Regulation['parseStatus']
  parse_error?: string
}

interface ApiCandidate {
  clause_id: number
  regulation_id: number
  regulation_name: string
  version?: string
  original_no: string
  content: string
  heading_path: string[]
  score: number
  evidence: string[]
}

interface ApiReviewRecord {
  id: number
  record_code: string
  source_type: 'regulation' | 'temporary'
  regulation_id?: number
  temporary_file_id?: number
  regulation_name?: string
  dimensions: DimensionKey[]
  source_snapshot: Array<{ clause_id: number }>
  candidate_snapshot: Array<{ clause_id: number }>
  created_at: string
  completed_at?: string
  created_by_name?: string
  problem_count: number
  has_report: boolean
}

interface ApiIssueHistory {
  actor_name: string
  action: string
  opinion?: string
  created_at: string
}

interface ApiReviewIssue {
  id: number
  review_record_id: number
  dimension: DimensionKey
  original: string
  location: string
  explanation: string
  consequence: string
  suggestion: string
  evidence_status?: string
  status: ReviewIssue['status']
  opinion?: string
  details: Record<string, unknown>
  histories: ApiIssueHistory[]
}

interface ApiRelation {
  id: string
  type: Regulation['relations'][number]['type']
  target_id: number
  target_name: string
  source: Regulation['relations'][number]['source']
  note?: string
}

interface ApiRegulation {
  id: number
  name?: string
  code?: string
  department_id?: number
  department?: string
  category_id?: number
  category?: string
  unit_id?: number
  unit?: string
  hierarchy?: Regulation['hierarchy']
  version?: string
  publish_date?: string
  effective_date?: string
  expiry_date?: string
  status?: Regulation['status']
  scope?: string
  file_name?: string
  parse_status: Regulation['parseStatus']
  deleted: boolean
  updated_at: string
  versions?: ApiVersion[]
  relations?: ApiRelation[]
}

interface ApiUnit {
  id: number
  name?: string
  level: UnitItem['level']
  parent_id?: number
  parent_name?: string
}

interface ApiLog {
  id: number
  type: OperationLog['type']
  regulation_id?: number
  regulation_name?: string
  operator?: string
  operated_at: string
  report_count: number
}

interface ApiSuggestion {
  id: number
  target_id?: number
  target_name?: string
  type: Regulation['relations'][number]['type']
  evidence?: string
  status: '待确认' | '已确认'
}

function formatDateTime(value: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : ''
}

function mapRegulation(item: ApiRegulation): Regulation {
  return {
    id: item.id,
    name: item.name || '未命名制度',
    code: item.code || '',
    departmentId: item.department_id,
    department: item.department || '',
    categoryId: item.category_id,
    category: item.category || '',
    unitId: item.unit_id,
    unit: item.unit,
    hierarchy: item.hierarchy || '二级单位制度',
    version: item.version || '',
    publishDate: item.publish_date || '',
    effectiveDate: item.effective_date || '',
    expiryDate: item.expiry_date,
    status: item.status || '生效中',
    scope: item.scope || '',
    fileName: item.file_name || '',
    parseStatus: item.parse_status,
    clauses: [],
    versions: (item.versions || []).map((version) => ({
      id: version.id,
      version: version.version || '',
      effectiveDate: version.effective_date || '',
      fileName: version.file_name || '',
      note: version.note || '',
      parseStatus: version.parse_status,
    })),
    relations: (item.relations || []).map((relation) => ({
      id: relation.id,
      type: relation.type,
      targetId: relation.target_id,
      targetName: relation.target_name,
      source: relation.source,
      note: relation.note || '',
    })),
    deleted: item.deleted,
    updatedAt: formatDateTime(item.updated_at),
  }
}

function mapClause(item: ApiClause): Clause {
  return {
    id: item.id,
    originalNo: item.original_no,
    title: item.title,
    content: item.content,
    level: item.level,
    location: [...item.heading_path, item.original_no].join(' > '),
  }
}

function mapCandidate(item: ApiCandidate): CandidateClause {
  return {
    id: item.clause_id,
    regulationId: item.regulation_id,
    regulationName: item.regulation_name,
    version: item.version || '',
    originalNo: item.original_no,
    content: item.content,
    location: [...item.heading_path, item.original_no].join(' > '),
    score: item.score,
    evidence: item.evidence,
  }
}

function mapReviewRecord(item: ApiReviewRecord): ReviewRecord {
  return {
    id: item.record_code,
    internalId: item.id,
    regulationId: item.regulation_id || 0,
    regulationName: item.regulation_name || '临时待审文件',
    clauseCount: item.source_snapshot.length,
    dimensions: item.dimensions,
    createdBy: item.created_by_name || '—',
    createdAt: formatDateTime(item.created_at),
    completedAt: formatDateTime(item.completed_at || ''),
    problemCount: item.problem_count || 0,
    hasReport: item.has_report,
  }
}

function detailText(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function mapReviewIssue(item: ApiReviewIssue, currentRegulationName = ''): ReviewIssue {
  const base = {
    id: String(item.id),
    dimension: item.dimension,
    original: item.original,
    location: item.location,
    explanation: item.explanation,
    consequence: item.consequence,
    suggestion: item.suggestion,
    insufficientEvidence: item.evidence_status === '证据不足，请人工判断',
    status: item.status,
    opinion: item.opinion,
    histories: item.histories.map((history) => ({
      actor: history.actor_name,
      time: formatDateTime(history.created_at),
      action: history.action,
      opinion: history.opinion,
    })),
  }
  if (item.dimension === 'semantic') {
    return { ...base, dimension: 'semantic', ambiguousExpression: detailText(item.details.ambiguous_expression) }
  }
  if (item.dimension === 'rule') {
    return { ...base, dimension: 'rule', issueType: detailText(item.details.rule_category) || '规则问题' }
  }
  if (item.dimension === 'conflict') {
    return {
      ...base,
      dimension: 'conflict',
      currentRegulationName,
      comparisonRegulationName: detailText(item.details.comparison_regulation_name),
      comparisonOriginal: detailText(item.details.comparison_original),
      comparisonLocation: detailText(item.details.comparison_location),
      conflictPoint: detailText(item.details.conflict_type) || item.explanation,
    }
  }
  const related = Array.isArray(item.details.related_evidence) ? item.details.related_evidence[0] as Record<string, unknown> | undefined : undefined
  return {
    ...base,
    dimension: 'consistency',
    relatedOriginal: detailText(related?.original),
    relatedLocation: detailText(related?.location),
    inconsistentItem: detailText(item.details.consistency_type) || item.explanation,
  }
}

function mapLog(item: ApiLog): OperationLog {
  return {
    id: item.id,
    type: item.type,
    regulationId: item.regulation_id || 0,
    regulationName: item.regulation_name || '未命名制度',
    operator: item.operator || '—',
    operatedAt: formatDateTime(item.operated_at),
    reportCount: item.report_count,
  }
}

export const useDataStore = defineStore('data', () => {
  const regulations = ref<Regulation[]>([])
  const users = ref<User[]>([])
  const records = ref<ReviewRecord[]>([])
  const candidateClauses = ref<CandidateClause[]>([])
  const issues = ref<ReviewIssue[]>([])
  const logs = ref<OperationLog[]>([])
  const relationSuggestions = ref<Record<number, RelationSuggestion[]>>({})
  const departmentItems = ref<MasterDataItem[]>([])
  const categoryItems = ref<MasterDataItem[]>([])
  const units = ref<UnitItem[]>([])
  const loading = ref(false)
  const lastError = ref('')

  const departments = computed(() => departmentItems.value.map((item) => item.name))
  const categories = computed(() => categoryItems.value.map((item) => item.name))
  const activeRegulations = computed(() => regulations.value.filter((item) => !item.deleted))
  const deletedRegulations = computed(() => regulations.value.filter((item) => item.deleted))

  async function loadForRole(role?: Role) {
    loading.value = true
    lastError.value = ''
    try {
      if (role === 'reviewer') {
        const [regulationData, departmentData, categoryData, unitData] = await Promise.all([
          apiRequest<ApiRegulation[]>('/regulations'),
          apiRequest<Array<{ id: number; name?: string }>>('/master-data/departments'),
          apiRequest<Array<{ id: number; name?: string }>>('/master-data/categories'),
          apiRequest<ApiUnit[]>('/master-data/units'),
        ])
        regulations.value = regulationData.map(mapRegulation)
        departmentItems.value = departmentData.map((item) => ({ id: item.id, name: item.name || '' }))
        categoryItems.value = categoryData.map((item) => ({ id: item.id, name: item.name || '' }))
        units.value = unitData.map((item) => ({ id: item.id, name: item.name || '', level: item.level, parentId: item.parent_id, parentName: item.parent_name }))
        await loadReviewRecords()
      } else if (role === 'admin') {
        const [userData, deletedData, logData] = await Promise.all([
          apiRequest<User[]>('/admin/users'),
          apiRequest<ApiRegulation[]>('/admin/deleted-regulations'),
          apiRequest<ApiLog[]>('/admin/operation-logs'),
        ])
        users.value = userData
        regulations.value = deletedData.map(mapRegulation)
        logs.value = logData.map(mapLog)
      }
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : '数据加载失败'
      throw error
    } finally {
      loading.value = false
    }
  }

  async function loadRegulation(id: number) {
    const item = mapRegulation(await apiRequest<ApiRegulation>(`/regulations/${id}`))
    const index = regulations.value.findIndex((candidate) => candidate.id === id)
    if (index >= 0) regulations.value[index] = item
    else regulations.value.push(item)
    if (item.parseStatus === '解析成功') await loadClauses(id)
    return item
  }

  async function loadClauses(regulationId: number) {
    const clauses = (await apiRequest<ApiClause[]>(`/regulations/${regulationId}/clauses`)).map(mapClause)
    const regulation = getRegulation(regulationId)
    if (regulation) regulation.clauses = clauses
    return clauses
  }

  function getRegulation(id: number) {
    return regulations.value.find((item) => item.id === id)
  }

  function regulationPayload(input: Partial<Regulation>) {
    return {
      name: input.name || null,
      code: input.code || null,
      department_id: input.departmentId || departmentItems.value.find((item) => item.name === input.department)?.id || null,
      category_id: input.categoryId || categoryItems.value.find((item) => item.name === input.category)?.id || null,
      unit_id: input.unitId || null,
      hierarchy: input.hierarchy || null,
      version: input.version || null,
      publish_date: input.publishDate || null,
      effective_date: input.effectiveDate || null,
      expiry_date: input.expiryDate || null,
      status: input.status || null,
      scope: input.scope || null,
      file_name: input.fileName || null,
    }
  }

  async function saveRegulation(input: Partial<Regulation> & Pick<Regulation, 'name'>) {
    const path = input.id ? `/regulations/${input.id}` : '/regulations'
    const item = mapRegulation(await apiRequest<ApiRegulation>(path, {
      method: input.id ? 'PATCH' : 'POST',
      ...jsonBody(regulationPayload(input)),
    }))
    const index = regulations.value.findIndex((candidate) => candidate.id === item.id)
    if (index >= 0) regulations.value[index] = item
    else regulations.value.unshift(item)
    return item
  }

  async function createRegulationWithFile(
    input: Partial<Regulation> & Pick<Regulation, 'name'>,
    file: File,
  ) {
    const payload = regulationPayload(input)
    const item = mapRegulation(await apiRequest<ApiRegulation>('/regulations/with-file', {
      method: 'POST',
      ...multipartBody({
        file,
        name: input.name,
        code: input.code || undefined,
        department_id: payload.department_id ? String(payload.department_id) : undefined,
        category_id: payload.category_id ? String(payload.category_id) : undefined,
        unit_id: payload.unit_id ? String(payload.unit_id) : undefined,
        hierarchy: input.hierarchy || undefined,
        version: input.version || undefined,
        publish_date: input.publishDate || undefined,
        effective_date: input.effectiveDate || undefined,
        expiry_date: input.expiryDate || undefined,
        status: input.status || undefined,
        scope: input.scope || undefined,
      }),
    }))
    regulations.value.unshift(item)
    if (item.parseStatus === '解析成功') await loadClauses(item.id)
    return item
  }

  async function deleteRegulation(id: number) {
    await apiRequest<void>(`/regulations/${id}`, { method: 'DELETE' })
    regulations.value = regulations.value.filter((item) => item.id !== id)
  }

  async function restoreRegulation(id: number) {
    await apiRequest<ApiRegulation>(`/admin/regulations/${id}/restore`, { method: 'POST' })
    await loadForRole('admin')
  }

  async function addRelation(regulationId: number, targetId: number, type: Regulation['relations'][number]['type']) {
    const relations = await apiRequest<ApiRelation[]>(`/regulations/${regulationId}/relations`, {
      method: 'POST',
      ...jsonBody({ target_id: targetId, type }),
    })
    const source = getRegulation(regulationId)
    if (source) source.relations = mapRegulation({ ...regulationToApi(source), relations }).relations
  }

  async function deleteRelation(regulationId: number, relationId: string) {
    if (!relationId.startsWith('manual-')) throw new Error('系统自动关系不能手工删除')
    await apiRequest<void>(`/regulations/${regulationId}/relations/${relationId.slice('manual-'.length)}`, { method: 'DELETE' })
    await loadRegulation(regulationId)
  }

  async function loadRelationSuggestions(regulationId: number) {
    const items = await apiRequest<ApiSuggestion[]>(`/regulations/${regulationId}/suggestions`)
    relationSuggestions.value[regulationId] = items.map((item) => ({
      id: item.id,
      targetId: item.target_id,
      targetName: item.target_name,
      type: item.type,
      evidence: item.evidence,
      status: item.status,
    }))
    return relationSuggestions.value[regulationId]
  }

  async function confirmRelationSuggestion(regulationId: number, suggestionId: number) {
    await apiRequest<ApiRelation[]>(`/regulations/${regulationId}/suggestions/${suggestionId}/confirm`, { method: 'POST' })
    await Promise.all([loadRegulation(regulationId), loadRelationSuggestions(regulationId)])
  }

  async function uploadRegulationVersion(regulationId: number, input: { version: string; effectiveDate: string; note?: string; file: File }) {
    await apiRequest<ApiVersion>(`/regulations/${regulationId}/versions/upload`, {
      method: 'POST',
      ...multipartBody({ file: input.file, version: input.version, effective_date: input.effectiveDate, note: input.note }),
    })
    return loadRegulation(regulationId)
  }

  function regulationToApi(item: Regulation): ApiRegulation {
    return {
      id: item.id,
      name: item.name,
      parse_status: item.parseStatus,
      deleted: item.deleted,
      updated_at: new Date().toISOString(),
    }
  }

  async function retryParse(id: number) {
    const target = getRegulation(id)
    const versionId = target?.versions[0]?.id
    if (!target || !versionId) throw new Error('未找到可重新解析的制度版本')
    target.parseStatus = '解析中'
    await apiRequest<ApiVersion>(`/regulation-versions/${versionId}/reparse`, { method: 'POST' })
    return loadRegulation(id)
  }

  async function uploadTemporaryFile(file: File): Promise<TemporaryReviewFile> {
    const item = await apiRequest<ApiTemporaryFile>('/temporary-files', {
      method: 'POST',
      ...multipartBody({ file }),
    })
    const clauses = (await apiRequest<ApiClause[]>(`/temporary-files/${item.id}/clauses`)).map(mapClause)
    return {
      id: item.id,
      originalName: item.original_name,
      parseStatus: item.parse_status,
      parseError: item.parse_error,
      clauses,
    }
  }

  async function loadCandidates(input: ReviewCreateInput) {
    candidateClauses.value = (await apiRequest<ApiCandidate[]>('/reviews/candidates', {
      method: 'POST',
      ...jsonBody({
        source_type: input.sourceType,
        regulation_id: input.regulationId || null,
        temporary_file_id: input.temporaryFileId || null,
        clause_ids: input.clauseIds,
        comparison_regulation_ids: input.comparisonRegulationIds,
      }),
    })).map(mapCandidate)
    return candidateClauses.value
  }

  async function createReview(input: ReviewCreateInput) {
    const record = mapReviewRecord(await apiRequest<ApiReviewRecord>('/reviews', {
      method: 'POST',
      ...jsonBody({
        source_type: input.sourceType,
        regulation_id: input.regulationId || null,
        temporary_file_id: input.temporaryFileId || null,
        clause_ids: input.clauseIds,
        dimensions: input.dimensions,
        candidate_clause_ids: input.candidateClauseIds,
        comparison_regulation_ids: input.comparisonRegulationIds,
      }),
    }))
    records.value.unshift(record)
    return record
  }

  async function loadReviewRecords() {
    records.value = (await apiRequest<ApiReviewRecord[]>('/reviews')).map(mapReviewRecord)
    return records.value
  }

  async function executeReview(record: ReviewRecord, onProgress?: (message: string) => void) {
    if (!record.internalId) throw new Error('审查记录编号无效')
    let failedMessage = ''
    let problemCount = 0
    await streamApi<{ message?: string; problem_count?: number }>(`/reviews/${record.internalId}/execute`, { method: 'POST' }, ({ event, data }) => {
      if (data.message) onProgress?.(data.message)
      if (event === 'failed') failedMessage = data.message || '审查执行失败'
      if (event === 'completed') problemCount = data.problem_count || 0
    })
    if (failedMessage) throw new Error(failedMessage)
    record.problemCount = problemCount
    record.hasReport = true
    record.completedAt = new Date().toLocaleString('zh-CN', { hour12: false })
    return record
  }

  async function loadReviewReport(recordCode: string) {
    if (!records.value.length) await loadReviewRecords()
    const record = records.value.find((item) => item.id === recordCode)
    if (!record) throw new Error('审查记录不存在')
    if (!record.internalId || !record.hasReport) throw new Error('该记录尚未生成审查报告')
    const data = await apiRequest<ApiReviewIssue[]>(`/reviews/${record.internalId}/issues`)
    issues.value = data.map((item) => mapReviewIssue(item, record.regulationName))
    return record
  }

  async function processIssue(id: string, action: '采纳修改建议' | '忽略', opinion?: string) {
    const data = await apiRequest<ApiReviewIssue>(`/reviews/issues/${id}/actions`, {
      method: 'POST',
      ...jsonBody({ action, opinion: opinion || null }),
    })
    const current = records.value.find((item) => item.internalId === data.review_record_id)
    const mapped = mapReviewIssue(data, current?.regulationName)
    const index = issues.value.findIndex((item) => item.id === id)
    if (index >= 0) issues.value[index] = mapped
    else issues.value.push(mapped)
    return mapped
  }

  async function addOpinion(id: string, opinion: string) {
    const data = await apiRequest<ApiReviewIssue>(`/reviews/issues/${id}/actions`, {
      method: 'POST',
      ...jsonBody({ action: '补充处理意见', opinion }),
    })
    const current = records.value.find((item) => item.internalId === data.review_record_id)
    const mapped = mapReviewIssue(data, current?.regulationName)
    const index = issues.value.findIndex((item) => item.id === id)
    if (index >= 0) issues.value[index] = mapped
    else issues.value.push(mapped)
    return mapped
  }

  async function updateUserPermissions(id: number, permissions: PermissionSet) {
    const updated = await apiRequest<User>(`/admin/users/${id}/permissions`, { method: 'PUT', ...jsonBody(permissions) })
    const index = users.value.findIndex((item) => item.id === id)
    if (index >= 0) users.value[index] = updated
  }

  async function toggleUser(id: number) {
    const target = users.value.find((item) => item.id === id)
    if (!target) return
    const updated = await apiRequest<User>(`/admin/users/${id}`, { method: 'PATCH', ...jsonBody({ enabled: !target.enabled }) })
    Object.assign(target, updated)
  }

  async function updateUser(id: number, input: { name: string; department: string }) {
    const updated = await apiRequest<User>(`/admin/users/${id}`, { method: 'PATCH', ...jsonBody(input) })
    const index = users.value.findIndex((item) => item.id === id)
    if (index >= 0) users.value[index] = updated
  }

  async function addUser(input: Pick<User, 'name' | 'username' | 'department'>) {
    const created = await apiRequest<User>('/admin/users', { method: 'POST', ...jsonBody(input) })
    users.value.push(created)
  }

  async function resetUserPassword(id: number) {
    return apiRequest<{ temporary_password: string }>(`/admin/users/${id}/reset-password`, { method: 'POST' })
  }

  async function deleteUser(id: number) {
    await apiRequest<void>(`/admin/users/${id}`, { method: 'DELETE' })
    users.value = users.value.filter((item) => item.id !== id)
  }

  async function deleteLog(id: number, deleteReports: boolean) {
    await apiRequest<void>(`/admin/operation-logs/${id}?delete_reports=${deleteReports}`, { method: 'DELETE' })
    logs.value = logs.value.filter((item) => item.id !== id)
  }

  async function addDepartment(name: string) {
    const item = await apiRequest<{ id: number; name?: string }>('/master-data/departments', { method: 'POST', ...jsonBody({ name }) })
    departmentItems.value.push({ id: item.id, name: item.name || '' })
  }

  async function updateDepartment(id: number, name: string) {
    const item = await apiRequest<{ id: number; name?: string }>(`/master-data/departments/${id}`, { method: 'PATCH', ...jsonBody({ name }) })
    const current = departmentItems.value.find((candidate) => candidate.id === id)
    if (current) current.name = item.name || ''
  }

  async function deleteDepartment(id: number) {
    await apiRequest<void>(`/master-data/departments/${id}`, { method: 'DELETE' })
    departmentItems.value = departmentItems.value.filter((item) => item.id !== id)
    regulations.value.filter((item) => item.departmentId === id).forEach((item) => {
      item.departmentId = undefined
      item.department = ''
    })
  }

  async function addCategory(name: string) {
    const item = await apiRequest<{ id: number; name?: string }>('/master-data/categories', { method: 'POST', ...jsonBody({ name }) })
    categoryItems.value.push({ id: item.id, name: item.name || '' })
  }

  async function updateCategory(id: number, name: string) {
    const item = await apiRequest<{ id: number; name?: string }>(`/master-data/categories/${id}`, { method: 'PATCH', ...jsonBody({ name }) })
    const current = categoryItems.value.find((candidate) => candidate.id === id)
    if (current) current.name = item.name || ''
  }

  async function deleteCategory(id: number) {
    await apiRequest<void>(`/master-data/categories/${id}`, { method: 'DELETE' })
    categoryItems.value = categoryItems.value.filter((item) => item.id !== id)
    regulations.value.filter((item) => item.categoryId === id).forEach((item) => {
      item.categoryId = undefined
      item.category = ''
    })
  }

  async function addUnit(input: { name: string; level: UnitItem['level']; parentId?: number }) {
    await apiRequest('/master-data/units', { method: 'POST', ...jsonBody({ name: input.name, level: input.level, parent_id: input.parentId || null }) })
    const unitData = await apiRequest<ApiUnit[]>('/master-data/units')
    units.value = unitData.map((item) => ({ id: item.id, name: item.name || '', level: item.level, parentId: item.parent_id, parentName: item.parent_name }))
  }

  async function updateUnit(id: number, input: { name: string; level: UnitItem['level']; parentId?: number }) {
    await apiRequest(`/master-data/units/${id}`, { method: 'PATCH', ...jsonBody({ name: input.name, level: input.level, parent_id: input.parentId || null }) })
    const unitData = await apiRequest<ApiUnit[]>('/master-data/units')
    units.value = unitData.map((item) => ({ id: item.id, name: item.name || '', level: item.level, parentId: item.parent_id, parentName: item.parent_name }))
  }

  async function deleteUnit(id: number) {
    await apiRequest<void>(`/master-data/units/${id}`, { method: 'DELETE' })
    units.value = units.value.filter((item) => item.id !== id)
    regulations.value.filter((item) => item.unitId === id).forEach((item) => {
      item.unitId = undefined
      item.unit = undefined
    })
  }

  return {
    regulations,
    users,
    records,
    candidateClauses,
    issues,
    logs,
    relationSuggestions,
    departmentItems,
    categoryItems,
    departments,
    categories,
    units,
    loading,
    lastError,
    activeRegulations,
    deletedRegulations,
    loadForRole,
    loadRegulation,
    loadClauses,
    getRegulation,
    saveRegulation,
    createRegulationWithFile,
    deleteRegulation,
    restoreRegulation,
    addRelation,
    deleteRelation,
    loadRelationSuggestions,
    confirmRelationSuggestion,
    uploadRegulationVersion,
    uploadTemporaryFile,
    retryParse,
    loadCandidates,
    createReview,
    executeReview,
    loadReviewRecords,
    loadReviewReport,
    processIssue,
    addOpinion,
    updateUserPermissions,
    toggleUser,
    updateUser,
    addUser,
    resetUserPassword,
    deleteUser,
    deleteLog,
    addDepartment,
    updateDepartment,
    deleteDepartment,
    addCategory,
    updateCategory,
    deleteCategory,
    addUnit,
    updateUnit,
    deleteUnit,
  }
})
