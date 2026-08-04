import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiRequest, jsonBody } from '../api/client'
import { initialIssues, initialRecords, initialRegulations } from '../data/mock'
import type {
  DimensionKey,
  MasterDataItem,
  OperationLog,
  PermissionSet,
  Regulation,
  RelationSuggestion,
  ReviewIssue,
  ReviewRecord,
  Role,
  UnitItem,
  User,
} from '../types'

interface ApiVersion {
  id: number
  version?: string
  effective_date?: string
  file_name?: string
  note?: string
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
  const prototype = initialRegulations.find((candidate) => candidate.id === item.id)
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
    clauses: structuredClone(prototype?.clauses || []),
    versions: (item.versions || []).map((version) => ({
      version: version.version || '',
      effectiveDate: version.effective_date || '',
      fileName: version.file_name || '',
      note: version.note || '',
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
  const records = ref<ReviewRecord[]>(structuredClone(initialRecords))
  const issues = ref<ReviewIssue[]>(structuredClone(initialIssues))
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
    return item
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

  async function addVersion(regulationId: number, input: { version: string; effectiveDate: string; fileName: string }) {
    await apiRequest<ApiVersion>(`/regulations/${regulationId}/versions`, {
      method: 'POST',
      ...jsonBody({ version: input.version || null, effective_date: input.effectiveDate || null, file_name: input.fileName || null }),
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

  function retryParse(id: number) {
    const target = getRegulation(id)
    if (!target) return
    target.parseStatus = '解析中'
    window.setTimeout(() => {
      target.parseStatus = '解析成功'
      if (!target.clauses.length) target.clauses = structuredClone(initialRegulations[0].clauses.slice(0, 2))
    }, 1200)
  }

  function createReview(regulationId: number, clauseCount: number, dimensions: DimensionKey[]) {
    const regulation = getRegulation(regulationId)!
    const date = new Date()
    const ymd = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`
    const sequence = String(records.value.filter((item) => item.id.startsWith(`${regulation.name}-${ymd}`)).length + 1).padStart(2, '0')
    const id = `${regulation.name}-${ymd}-${sequence}`
    const formatted = date.toLocaleString('zh-CN', { hour12: false })
    records.value.unshift({ id, regulationId, regulationName: regulation.name, clauseCount, dimensions, createdBy: '李明', createdAt: formatted, completedAt: formatted, problemCount: dimensions.length })
    return id
  }

  function processIssue(id: string, action: '采纳修改建议' | '忽略', opinion: string, actor: string) {
    const issue = issues.value.find((item) => item.id === id)
    if (!issue) return
    issue.status = action === '采纳修改建议' ? '已采纳' : '已忽略'
    issue.opinion = opinion || issue.opinion
    issue.histories.push({ actor, time: new Date().toLocaleString('zh-CN', { hour12: false }), action, opinion: opinion || undefined })
  }

  function addOpinion(id: string, opinion: string, actor: string) {
    const issue = issues.value.find((item) => item.id === id)
    if (!issue || !opinion) return
    issue.opinion = opinion
    issue.histories.push({ actor, time: new Date().toLocaleString('zh-CN', { hour12: false }), action: '补充处理意见', opinion })
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
    getRegulation,
    saveRegulation,
    deleteRegulation,
    restoreRegulation,
    addRelation,
    deleteRelation,
    loadRelationSuggestions,
    confirmRelationSuggestion,
    addVersion,
    retryParse,
    createReview,
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
