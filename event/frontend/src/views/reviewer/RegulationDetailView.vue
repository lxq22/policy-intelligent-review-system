<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, Connection, Delete, DocumentChecked, Plus, Refresh, Upload } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import PermissionButton from '../../components/PermissionButton.vue'
import { useDataStore } from '../../stores/data'
import type { Regulation } from '../../types'

const route = useRoute()
const router = useRouter()
const store = useDataStore()
const activeTab = ref('overview')
const relationDialog = ref(false)
const versionDialog = ref(false)
const relationForm = reactive<{ targetId?: number; type: Regulation['relations'][number]['type'] }>({ type: '关联' })
const versionForm = reactive({ version: '', effectiveDate: '', fileName: '' })
const regulation = computed(() => store.getRegulation(Number(route.params.id)))
const relatedRecords = computed(() => store.records.filter((item) => item.regulationId === regulation.value?.id))
const suggestions = computed(() => store.relationSuggestions[Number(route.params.id)] || [])

async function addRelation() {
  if (!regulation.value || !relationForm.targetId) {
    ElMessage.warning('请选择目标制度')
    return
  }
  try {
    await store.addRelation(regulation.value.id, relationForm.targetId, relationForm.type)
    relationDialog.value = false
    ElMessage.success('关系已保存，目标制度会展示对应的反向关系')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '关系保存失败')
  }
}

async function addVersion() {
  if (!regulation.value || !versionForm.version) {
    ElMessage.warning('请填写版本号')
    return
  }
  try {
    await store.addVersion(regulation.value.id, versionForm)
    versionDialog.value = false
    ElMessage.success('新版本已保存，旧版本继续保留')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '版本保存失败')
  }
}

async function removeRelation(relationId: string, targetName: string) {
  if (!regulation.value) return
  const confirmed = await ElMessageBox.confirm(`确认删除与“${targetName}”的这条人工关系吗？`, '删除制度关系', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return
  try {
    await store.deleteRelation(regulation.value.id, relationId)
    ElMessage.success('人工关系已删除，目标制度的反向展示也已同步移除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '关系删除失败')
  }
}

async function confirmSuggestion(suggestionId: number) {
  if (!regulation.value) return
  try {
    await store.confirmRelationSuggestion(regulation.value.id, suggestionId)
    ElMessage.success('关系建议已确认并建立正式关系')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '关系建议确认失败')
  }
}

function retry() {
  if (!regulation.value) return
  store.retryParse(regulation.value.id)
  ElMessage.info('已重新开始解析，请稍候')
}

onMounted(async () => {
  try {
    await Promise.all([
      store.loadRegulation(Number(route.params.id)),
      store.loadRelationSuggestions(Number(route.params.id)),
    ])
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '制度详情加载失败')
  }
})
</script>

<template>
  <div v-if="regulation">
    <PageHeader eyebrow="Regulation Detail" :title="regulation.name" :description="`${regulation.code || '暂无编号'} · ${regulation.version} · 最近更新 ${regulation.updatedAt}`">
      <template #actions>
        <el-button :icon="ArrowLeft" @click="router.push('/reviewer/regulations')">返回制度库</el-button>
        <el-button type="primary" :icon="DocumentChecked" :disabled="regulation.parseStatus !== '解析成功'" @click="router.push(`/reviewer/review/new?regulation=${regulation.id}`)">选择条款审查</el-button>
      </template>
    </PageHeader>

    <div class="detail-grid">
      <div class="detail-main">
        <div class="panel">
          <el-tabs v-model="activeTab" style="padding: 0 20px">
            <el-tab-pane label="基本信息" name="overview">
              <div class="meta-grid" style="padding: 10px 0 24px">
                <div class="meta-item"><label>部门</label><div>{{ regulation.department || '待补充' }}</div></div>
                <div class="meta-item"><label>业务分类</label><div>{{ regulation.category || '待补充' }}</div></div>
                <div class="meta-item"><label>制度层级</label><div>{{ regulation.hierarchy }}</div></div>
                <div class="meta-item"><label>所属单位</label><div>{{ regulation.unit || '待补充' }}</div></div>
                <div class="meta-item"><label>发布日期</label><div>{{ regulation.publishDate || '待补充' }}</div></div>
                <div class="meta-item"><label>生效日期</label><div>{{ regulation.effectiveDate || '待补充' }}</div></div>
                <div class="meta-item"><label>失效日期</label><div>{{ regulation.expiryDate || '—' }}</div></div>
                <div class="meta-item wide"><label>适用范围</label><div>{{ regulation.scope || '待补充' }}</div></div>
              </div>
            </el-tab-pane>
            <el-tab-pane :label="`解析条款（${regulation.clauses.length}）`" name="clauses">
              <div style="padding-bottom: 22px">
                <div class="subsection-head">
                  <div>
                    <h3>条款解析结果</h3>
                    <p class="muted">位置由文件名、标题层级和段落序号组成，不使用页码。</p>
                  </div>
                  <el-button v-if="regulation.parseStatus === '解析失败'" type="primary" :icon="Refresh" @click="retry">重新解析</el-button>
                </div>
                <el-alert v-if="regulation.parseStatus === '解析中'" title="正在重新解析文件，本页状态仅用于本次反馈。" type="info" show-icon :closable="false" />
                <el-empty v-else-if="!regulation.clauses.length" :description="regulation.parseStatus === '解析失败' ? '解析失败，可重新解析' : '暂无条款'" />
                <div v-for="clause in regulation.clauses" :key="clause.id" class="source-box" style="margin-top: 10px">
                  <div class="location">{{ clause.location }}</div>
                  <strong>{{ clause.originalNo }} {{ clause.title }}</strong>
                  <p>{{ clause.content }}</p>
                </div>
              </div>
            </el-tab-pane>
            <el-tab-pane :label="`版本（${regulation.versions.length}）`" name="versions">
              <div style="padding-bottom: 22px">
                <div class="subsection-head">
                  <div><h3>制度版本历史</h3><p class="muted">旧版本和原始文件继续保留。</p></div>
                  <PermissionButton permission="upload" :icon="Upload" @click="versionDialog=true">上传新版本</PermissionButton>
                </div>
                <el-table :data="regulation.versions">
                  <el-table-column prop="version" label="版本号" width="100" />
                  <el-table-column prop="effectiveDate" label="生效日期" width="130" />
                  <el-table-column prop="fileName" label="原始文件" min-width="220" />
                  <el-table-column prop="note" label="版本说明" min-width="180" />
                </el-table>
              </div>
            </el-tab-pane>
            <el-tab-pane :label="`制度关系（${regulation.relations.length}）`" name="relations">
              <div style="padding-bottom: 22px">
                <div class="subsection-head">
                  <div><h3>已建立的制度关系</h3><p class="muted">自动关系与人工关系分别标明来源。</p></div>
                  <PermissionButton permission="relation" :icon="Plus" @click="relationDialog=true">添加关系</PermissionButton>
                </div>
                <el-table :data="regulation.relations">
                  <el-table-column prop="type" label="关系类型" width="100"><template #default="{row}"><el-tag effect="plain">{{ row.type }}</el-tag></template></el-table-column>
                  <el-table-column prop="targetName" label="目标制度" min-width="210" />
                  <el-table-column prop="source" label="来源" width="110" />
                  <el-table-column prop="note" label="说明" min-width="220" />
                  <el-table-column label="操作" width="110"><template #default="{row}"><PermissionButton v-if="row.source !== '系统自动'" permission="relation" type="danger" :icon="Delete" @click="removeRelation(row.id, row.targetName)">删除</PermissionButton><span v-else class="muted">自动维护</span></template></el-table-column>
                </el-table>
                <div class="subsection">
                  <h3 class="section-title">待确认的关系建议</h3>
                  <el-empty v-if="!suggestions.length" description="当前没有待确认的关系建议" />
                  <el-table v-else :data="suggestions" style="margin-top:12px">
                    <el-table-column prop="type" label="建议关系" width="100" />
                    <el-table-column prop="targetName" label="识别到的制度" min-width="190" />
                    <el-table-column prop="evidence" label="识别依据" min-width="220" />
                    <el-table-column label="操作" width="120"><template #default="{row}"><PermissionButton v-if="row.targetId" permission="relation" type="primary" :icon="Check" @click="confirmSuggestion(row.id)">确认</PermissionButton><el-tag v-else type="warning" effect="plain">待匹配</el-tag></template></el-table-column>
                  </el-table>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <div class="detail-side">
        <div class="panel">
          <div class="panel-head"><h2>当前状态</h2><el-tag :type="regulation.status === '生效中' ? 'success' : 'info'">{{ regulation.status }}</el-tag></div>
          <div class="panel-body summary-list">
            <div><label>文件</label><div>{{ regulation.fileName }}</div></div>
            <div><label>解析状态</label><div><el-tag size="small" effect="plain" :type="regulation.parseStatus === '解析成功' ? 'success' : regulation.parseStatus === '解析失败' ? 'danger' : 'warning'">{{ regulation.parseStatus }}</el-tag></div></div>
            <div><label>关系</label><div>{{ regulation.relations.length }} 条正式关系</div></div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>历史审查</h2><span class="muted">{{ relatedRecords.length }} 次</span></div>
          <div v-if="relatedRecords.length" class="panel-body">
            <div v-for="item in relatedRecords" :key="item.id" style="padding: 10px 0; border-bottom: 1px solid #edf1f3">
              <el-link type="primary" @click="router.push(`/reviewer/reports/${item.id}`)">{{ item.id }}</el-link>
              <div class="table-sub">{{ item.createdAt }} · {{ item.problemCount }} 个问题</div>
            </div>
          </div>
          <div v-else class="empty-wrap" style="padding: 24px"><p>暂无历史审查</p></div>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>关系提示</h2><el-icon color="#0f8b85"><Connection /></el-icon></div>
          <div class="panel-body"><p class="muted">同部门制度会自动建立双向关联；一级单位与所属二级单位制度会自动建立上下位关系。</p></div>
        </div>
      </div>
    </div>

    <el-dialog v-model="relationDialog" title="添加制度关系" width="520px">
      <el-form label-position="top">
        <el-form-item label="关系类型"><el-select v-model="relationForm.type" style="width:100%"><el-option v-for="type in ['上位','下位','关联','引用','被引用','版本替代']" :key="type" :label="type" :value="type" /></el-select></el-form-item>
        <el-form-item label="目标制度"><el-select v-model="relationForm.targetId" filterable style="width:100%"><el-option v-for="item in store.activeRegulations.filter(i => i.id !== regulation?.id)" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="relationDialog=false">取消</el-button><el-button type="primary" @click="addRelation">保存关系</el-button></template>
    </el-dialog>

    <el-dialog v-model="versionDialog" title="上传新版本" width="560px">
      <div class="soft-note">原型保留旧版本及替代说明；实际文件上传与解析将在后续里程碑接入。</div>
      <el-form label-position="top" class="subsection">
        <el-form-item label="版本号"><el-input v-model="versionForm.version" /></el-form-item>
        <el-form-item label="生效日期"><el-date-picker v-model="versionForm.effectiveDate" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="文件名"><el-input v-model="versionForm.fileName" placeholder=".docx 或普通文字 PDF" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="versionDialog=false">取消</el-button><el-button type="primary" @click="addVersion">保存版本</el-button></template>
    </el-dialog>
  </div>
  <el-result v-else icon="warning" title="制度不存在或已不可见"><template #extra><el-button type="primary" @click="router.push('/reviewer/regulations')">返回制度库</el-button></template></el-result>
</template>
