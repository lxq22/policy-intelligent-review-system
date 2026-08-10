export type Role = 'reviewer' | 'admin'
export type PermissionKey = 'upload' | 'delete' | 'relation'
export type RegulationStatus = '生效中' | '已失效'
export type ParseStatus = '待解析' | '解析中' | '解析成功' | '解析失败'
export type DimensionKey = 'semantic' | 'rule' | 'conflict' | 'consistency'

export interface PermissionSet {
  upload: boolean
  delete: boolean
  relation: boolean
}

export interface User {
  id: number
  username: string
  name: string
  role: Role
  enabled: boolean
  department: string
  permissions: PermissionSet
}

export interface Clause {
  id: number | string
  originalNo: string
  title: string
  content: string
  level: string
  location: string
}

export interface RegulationVersion {
  id?: number
  version: string
  effectiveDate: string
  fileName: string
  note: string
  parseStatus?: ParseStatus
}

export interface Relation {
  id: string
  type: '上位' | '下位' | '关联' | '引用' | '被引用' | '版本替代'
  targetId: number
  targetName: string
  source: '系统自动' | '人工确认' | '手工添加'
  note: string
}

export interface RelationSuggestion {
  id: number
  targetId?: number
  targetName?: string
  type: Relation['type']
  evidence?: string
  status: '待确认' | '已确认'
}

export interface Regulation {
  id: number
  name: string
  code: string
  departmentId?: number
  department: string
  categoryId?: number
  category: string
  unitId?: number
  unit?: string
  hierarchy: '一级单位制度' | '二级单位制度'
  version: string
  publishDate: string
  effectiveDate: string
  expiryDate?: string
  status: RegulationStatus
  scope: string
  fileName: string
  parseStatus: ParseStatus
  clauses: Clause[]
  versions: RegulationVersion[]
  relations: Relation[]
  deleted: boolean
  updatedAt: string
}

export interface ReviewRecord {
  id: string
  internalId?: number
  regulationId: number
  regulationName: string
  clauseCount: number
  dimensions: DimensionKey[]
  createdBy: string
  createdAt: string
  completedAt: string
  problemCount: number
}

export interface TemporaryReviewFile {
  id: number
  originalName: string
  parseStatus: ParseStatus
  parseError?: string
  clauses: Clause[]
}

export interface CandidateClause {
  id: number
  regulationId: number
  regulationName: string
  version: string
  originalNo: string
  content: string
  location: string
  score: number
  evidence: string[]
}

export interface ReviewCreateInput {
  sourceType: 'regulation' | 'temporary'
  regulationId?: number
  temporaryFileId?: number
  clauseIds: number[]
  dimensions: DimensionKey[]
  candidateClauseIds: number[]
  comparisonRegulationIds: number[]
}

export interface BaseIssue {
  id: string
  dimension: DimensionKey
  original: string
  location: string
  explanation: string
  consequence: string
  suggestion: string
  insufficientEvidence?: boolean
  status: '待处理' | '已采纳' | '已忽略'
  opinion?: string
  histories: Array<{
    actor: string
    time: string
    action: string
    opinion?: string
  }>
}

export interface SemanticIssue extends BaseIssue {
  dimension: 'semantic'
  ambiguousExpression: string
}

export interface RuleIssue extends BaseIssue {
  dimension: 'rule'
  issueType: string
  matchedRule: string
}

export interface ConflictIssue extends BaseIssue {
  dimension: 'conflict'
  currentRegulationName: string
  comparisonRegulationName: string
  comparisonOriginal: string
  comparisonLocation: string
  conflictPoint: string
}

export interface ConsistencyIssue extends BaseIssue {
  dimension: 'consistency'
  relatedOriginal: string
  relatedLocation: string
  inconsistentItem: string
}

export type ReviewIssue = SemanticIssue | RuleIssue | ConflictIssue | ConsistencyIssue

export interface OperationLog {
  id: number
  type: '新增制度' | '删除制度' | '恢复制度'
  regulationId: number
  regulationName: string
  operator: string
  operatedAt: string
  reportCount: number
}

export interface MasterDataItem {
  id: number
  name: string
}

export interface UnitItem {
  id: number
  name: string
  level: '一级单位' | '二级单位'
  parentId?: number
  parentName?: string
}
