<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, EditPen, Warning } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { useDataStore } from '../../stores/data'
import type { DimensionKey, ReviewIssue } from '../../types'

const route = useRoute()
const router = useRouter()
const store = useDataStore()
const activeDimension = ref<DimensionKey>('semantic')
const opinionDialog = ref(false)
const currentIssueId = ref('')
const opinion = ref('')
const loading = ref(true)
const loadError = ref('')
const actionBusy = ref('')
const record = computed(() => store.records.find((item) => item.id === String(route.params.id)))
const dimensionMeta: Array<{ key: DimensionKey; label: string; description: string }> = [
  { key: 'semantic', label: '语义分歧', description: '模糊表达与执行边界' },
  { key: 'rule', label: '规则匹配', description: '结构、编号与行文规范' },
  { key: 'conflict', label: '制度冲突', description: '引用、效力与规定冲突' },
  { key: 'consistency', label: '一致性', description: '制度内部信息一致性' },
]
const visibleIssues = computed(() => store.issues.filter((item) => item.dimension === activeDimension.value))
const counts = computed(() => Object.fromEntries(dimensionMeta.map((item) => [item.key, store.issues.filter((issue) => issue.dimension === item.key).length])))

async function process(issue: ReviewIssue, action: '采纳修改建议' | '忽略') {
  actionBusy.value = issue.id
  try {
    await store.processIssue(issue.id, action)
    ElMessage.success(`已${action === '采纳修改建议' ? '采纳修改建议' : '忽略该问题'}，处理动作已留痕`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '处理失败')
  } finally {
    actionBusy.value = ''
  }
}

function openOpinion(issue: ReviewIssue) {
  currentIssueId.value = issue.id
  opinion.value = issue.opinion || ''
  opinionDialog.value = true
}

async function saveOpinion() {
  if (!opinion.value.trim()) return ElMessage.warning('请填写处理意见')
  actionBusy.value = currentIssueId.value
  try {
    await store.addOpinion(currentIssueId.value, opinion.value.trim())
    opinionDialog.value = false
    ElMessage.success('处理意见已保存并留痕')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '处理意见保存失败')
  } finally {
    actionBusy.value = ''
  }
}

onMounted(async () => {
  try {
    const loaded = await store.loadReviewReport(String(route.params.id))
    activeDimension.value = loaded.dimensions[0] || 'semantic'
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '审查报告加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader eyebrow="Review Report" title="四维审查报告" :description="record ? `${record.id} · ${record.regulationName} · ${record.problemCount} 个问题` : '正在读取指定审查报告'">
      <template #actions><el-button :icon="ArrowLeft" @click="router.push('/reviewer/records')">返回审查记录</el-button></template>
    </PageHeader>

    <el-skeleton v-if="loading" :rows="8" animated />
    <el-result v-else-if="loadError" icon="error" title="无法打开报告" :sub-title="loadError"><template #extra><el-button type="primary" @click="router.push('/reviewer/records')">返回审查记录</el-button></template></el-result>
    <div v-else-if="record" class="report-layout">
      <aside class="panel dimension-nav">
        <button v-for="item in dimensionMeta" :key="item.key" class="dimension-button" :class="{active:activeDimension===item.key}" @click="activeDimension=item.key">
          <span><strong>{{ item.label }}</strong><small style="display:block;margin-top:3px;font-weight:400">{{ item.description }}</small></span>
          <el-tag size="small" round>{{ counts[item.key] }}</el-tag>
        </button>
      </aside>

      <section>
        <div class="soft-note" style="margin-bottom:14px">
          四个维度使用各自字段展示；仅“制度冲突”显示对比制度原文。证据充分的问题不额外显示证据标签。
        </div>

        <div v-for="issue in visibleIssues" :key="issue.id" class="panel issue-card">
          <div class="issue-head">
            <div class="issue-head-left">
              <span class="dimension-badge">{{ dimensionMeta.find(i=>i.key===issue.dimension)?.label }}</span>
              <span v-if="issue.insufficientEvidence" class="dimension-badge evidence-warning"><el-icon><Warning /></el-icon> 证据不足，请人工判断</span>
            </div>
            <el-tag :type="issue.status === '已采纳' ? 'success' : issue.status === '已忽略' ? 'info' : 'warning'" effect="plain">{{ issue.status }}</el-tag>
          </div>

          <div class="issue-grid">
            <template v-if="issue.dimension === 'semantic'">
              <div class="issue-field full"><label>待审制度原文</label><p>{{ issue.original }}</p><div class="table-sub">{{ issue.location }}</div></div>
              <div class="issue-field"><label>歧义表达</label><p>{{ issue.ambiguousExpression }}</p></div>
              <div class="issue-field"><label>判断说明</label><p>{{ issue.explanation }}</p></div>
              <div class="issue-field"><label>可能造成的后果</label><p>{{ issue.consequence }}</p></div>
              <div class="issue-field"><label>修改建议</label><p>{{ issue.suggestion }}</p></div>
            </template>

            <template v-else-if="issue.dimension === 'rule'">
              <div class="issue-field full"><label>待审制度原文</label><p>{{ issue.original }}</p><div class="table-sub">{{ issue.location }}</div></div>
              <div class="issue-field"><label>规则问题类型</label><p>{{ issue.issueType }}</p></div>
              <div class="issue-field"><label>判断说明</label><p>{{ issue.explanation }}</p></div>
              <div class="issue-field"><label>可能造成的后果</label><p>{{ issue.consequence }}</p></div>
              <div class="issue-field full"><label>修改建议</label><p>{{ issue.suggestion }}</p></div>
            </template>

            <template v-else-if="issue.dimension === 'conflict'">
              <div v-if="issue.comparisonOriginal" class="comparison-pair">
                <div class="comparison-box"><label>待审制度原文 · {{ issue.currentRegulationName }}</label><p>{{ issue.original }}</p><div class="table-sub">{{ issue.location }}</div></div>
                <div class="comparison-box compare"><label>对比制度原文 · {{ issue.comparisonRegulationName }}</label><p>{{ issue.comparisonOriginal }}</p><div class="table-sub">{{ issue.comparisonLocation }}</div></div>
              </div>
              <div v-else class="issue-field full"><label>待审制度原文</label><p>{{ issue.original }}</p><div class="table-sub">{{ issue.location }}</div></div>
              <div class="issue-field"><label>冲突点</label><p>{{ issue.conflictPoint }}</p></div>
              <div class="issue-field"><label>判断说明</label><p>{{ issue.explanation }}</p></div>
              <div class="issue-field"><label>可能造成的后果</label><p>{{ issue.consequence }}</p></div>
              <div class="issue-field"><label>修改建议</label><p>{{ issue.suggestion }}</p></div>
            </template>

            <template v-else>
              <div v-if="issue.relatedOriginal" class="comparison-pair">
                <div class="comparison-box"><label>当前原文</label><p>{{ issue.original }}</p><div class="table-sub">{{ issue.location }}</div></div>
                <div class="comparison-box"><label>同一制度内相关原文</label><p>{{ issue.relatedOriginal }}</p><div class="table-sub">{{ issue.relatedLocation }}</div></div>
              </div>
              <div v-else class="issue-field full"><label>待审制度原文</label><p>{{ issue.original }}</p><div class="table-sub">{{ issue.location }}</div></div>
              <div class="issue-field"><label>不一致项</label><p>{{ issue.inconsistentItem }}</p></div>
              <div class="issue-field"><label>判断说明</label><p>{{ issue.explanation }}</p></div>
              <div class="issue-field"><label>可能造成的后果</label><p>{{ issue.consequence }}</p></div>
              <div class="issue-field"><label>修改建议</label><p>{{ issue.suggestion }}</p></div>
            </template>

            <div v-if="issue.opinion || issue.histories.length" class="issue-field full">
              <label>人工处理留痕</label>
              <p v-if="issue.opinion">处理意见：{{ issue.opinion }}</p>
              <ul class="history-list"><li v-for="(history,index) in issue.histories" :key="index">{{ history.time }} · {{ history.actor }} · {{ history.action }}<span v-if="history.opinion"> · {{ history.opinion }}</span></li></ul>
            </div>
          </div>

          <div class="issue-actions">
            <span class="muted">所有人工动作均记录操作人、时间、动作与意见</span>
            <div>
              <el-button :icon="EditPen" :loading="actionBusy===issue.id" @click="openOpinion(issue)">补充处理意见</el-button>
              <el-button :loading="actionBusy===issue.id" @click="process(issue,'忽略')">忽略</el-button>
              <el-button type="primary" :icon="Check" :loading="actionBusy===issue.id" @click="process(issue,'采纳修改建议')">采纳修改建议</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="!visibleIssues.length" description="本维度没有发现问题" />
      </section>
    </div>

    <el-dialog v-model="opinionDialog" title="补充处理意见" width="560px">
      <el-input v-model="opinion" type="textarea" :rows="5" placeholder="填写人工判断、处理依据或后续安排" />
      <template #footer><el-button @click="opinionDialog=false">取消</el-button><el-button type="primary" :loading="Boolean(actionBusy)" @click="saveOpinion">保存并留痕</el-button></template>
    </el-dialog>
  </div>
</template>
