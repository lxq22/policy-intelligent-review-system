<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { Check, Document, UploadFilled } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { useDataStore } from '../../stores/data'
import type { DimensionKey, ReviewCreateInput, TemporaryReviewFile } from '../../types'

const route = useRoute()
const router = useRouter()
const store = useDataStore()
const step = ref(0)
const sourceType = ref<'library' | 'temporary'>('library')
const regulationId = ref<number>(Number(route.query.regulation) || store.activeRegulations.find((item) => item.parseStatus === '解析成功')?.id || 1)
const selectedClauses = ref<Array<number | string>>([])
const selectedDimensions = ref<DimensionKey[]>(['semantic', 'rule', 'conflict', 'consistency'])
const selectedCandidates = ref<number[]>([])
const comparisonRegulationIds = ref<number[]>([])
const selectedFile = ref<File>()
const temporaryFile = ref<TemporaryReviewFile>()
const runState = ref<'idle' | 'running' | 'success' | 'failed'>('idle')
const resultId = ref('')
const busy = ref(false)

const currentRegulation = computed(() => store.getRegulation(regulationId.value))
const currentClauses = computed(() => sourceType.value === 'temporary' ? temporaryFile.value?.clauses || [] : currentRegulation.value?.clauses || [])
const currentSourceName = computed(() => sourceType.value === 'temporary' ? temporaryFile.value?.originalName || selectedFile.value?.name : currentRegulation.value?.name)
const candidates = computed(() => store.candidateClauses)
const needCandidates = computed(() => selectedDimensions.value.includes('conflict'))
const steps = computed(() => (needCandidates.value ? ['审查来源', '指定条款', '审查维度', '候选条款', '运行反馈'] : ['审查来源', '指定条款', '审查维度', '运行反馈']))
const finalStep = computed(() => steps.value.length - 1)
const dimensionMeta: Array<{ key: DimensionKey; title: string; description: string }> = [
  { key: 'semantic', title: '语义分歧', description: '识别“及时、适当、原则上”等含义不明确的表达。' },
  { key: 'rule', title: '规则匹配', description: '检查文本结构、编号和行文规范等传统文字校对规则。' },
  { key: 'conflict', title: '制度冲突', description: '与用户选定的候选条款比较引用、效力和规定冲突。' },
  { key: 'consistency', title: '一致性', description: '检查同一制度内术语、主体、数值及制度信息是否一致。' },
]

function selectRegulation(id: number) {
  regulationId.value = id
  selectedClauses.value = []
  selectedCandidates.value = []
}

function selectUpload(upload: UploadFile) {
  selectedFile.value = upload.raw
  temporaryFile.value = undefined
  selectedClauses.value = []
  selectedCandidates.value = []
}

function toggleDimension(key: DimensionKey) {
  selectedDimensions.value = selectedDimensions.value.includes(key)
    ? selectedDimensions.value.filter((item) => item !== key)
    : [...selectedDimensions.value, key]
}

function reviewInput(): ReviewCreateInput {
  return {
    sourceType: sourceType.value === 'library' ? 'regulation' : 'temporary',
    regulationId: sourceType.value === 'library' ? regulationId.value : undefined,
    temporaryFileId: sourceType.value === 'temporary' ? temporaryFile.value?.id : undefined,
    clauseIds: selectedClauses.value.filter((id): id is number => typeof id === 'number'),
    dimensions: selectedDimensions.value,
    candidateClauseIds: selectedCandidates.value,
    comparisonRegulationIds: comparisonRegulationIds.value,
  }
}

async function next() {
  if (busy.value) return
  if (step.value === 0) {
    busy.value = true
    try {
      if (sourceType.value === 'library') {
        if (!currentRegulation.value) return ElMessage.warning('请选择待审制度')
        await store.loadClauses(regulationId.value)
      } else {
        if (!selectedFile.value) return ElMessage.warning('请选择待审文件')
        temporaryFile.value = await store.uploadTemporaryFile(selectedFile.value)
      }
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '文件解析失败')
      return
    } finally {
      busy.value = false
    }
  }
  if (step.value === 1 && !selectedClauses.value.length) return ElMessage.warning('请至少选择一个待审条款')
  if (step.value === 2 && !selectedDimensions.value.length) return ElMessage.warning('请至少选择一个审查维度')
  if (needCandidates.value && step.value === 3 && !selectedCandidates.value.length) return ElMessage.warning('制度冲突维度需要至少选择一个候选条款')
  if (step.value < finalStep.value) {
    if (needCandidates.value && step.value === 2) {
      busy.value = true
      try {
        await store.loadCandidates(reviewInput())
      } catch (error) {
        ElMessage.error(error instanceof Error ? error.message : '候选条款加载失败')
        return
      } finally {
        busy.value = false
      }
    }
    step.value += 1
    if (step.value === finalStep.value) runReview()
  }
}

function previous() {
  if (runState.value === 'running') return
  step.value = Math.max(0, step.value - 1)
}

async function runReview() {
  runState.value = 'running'
  try {
    const record = await store.createReview(reviewInput())
    resultId.value = record.id
    runState.value = 'success'
  } catch (error) {
    runState.value = 'failed'
    ElMessage.error(error instanceof Error ? error.message : '审查输入保存失败')
  }
}

onMounted(async () => {
  if (currentRegulation.value?.parseStatus === '解析成功') {
    await store.loadClauses(regulationId.value).catch(() => undefined)
  }
})
</script>

<template>
  <div class="step-page">
    <PageHeader eyebrow="New Review" title="发起制度审查" description="一次审查只处理你选定的条款、维度和冲突候选条款。">
      <template #actions><el-button @click="router.push('/reviewer/records')">查看审查记录</el-button></template>
    </PageHeader>

    <div class="step-strip">
      <el-steps :active="step" finish-status="success" align-center>
        <el-step v-for="item in steps" :key="item" :title="item" />
      </el-steps>
    </div>

    <div class="wizard-grid">
      <div class="panel wizard-main">
        <div class="panel-head"><h2>{{ steps[step] }}</h2><span class="muted">步骤 {{ step + 1 }} / {{ steps.length }}</span></div>
        <div class="panel-body">
          <template v-if="step === 0">
            <div class="choice-grid">
              <div class="choice-card" :class="{selected: sourceType==='library'}" @click="sourceType='library'">
                <el-icon size="22" color="#0f8b85"><Document /></el-icon><h3>从制度库选择</h3><p>使用已保存且解析成功的制度，历史审查会回到该制度详情。</p><el-icon v-if="sourceType==='library'" class="check"><Check /></el-icon>
              </div>
              <div class="choice-card" :class="{selected: sourceType==='temporary'}" @click="sourceType='temporary'">
                <el-icon size="22" color="#0f8b85"><UploadFilled /></el-icon><h3>临时上传待审文件</h3><p>支持 .docx 和普通文字 PDF，文件不会进入正式制度库。</p><el-icon v-if="sourceType==='temporary'" class="check"><Check /></el-icon>
              </div>
            </div>
            <div v-if="sourceType==='library'" class="subsection">
              <h3 class="section-title">选择制度</h3>
              <el-select :model-value="regulationId" filterable style="width:100%; margin-top:12px" @change="selectRegulation">
                <el-option v-for="item in store.activeRegulations.filter(i => i.parseStatus === '解析成功')" :key="item.id" :label="`${item.name} · ${item.version}`" :value="item.id" />
              </el-select>
              <div v-if="currentRegulation" class="source-box" style="margin-top:12px">
                <div class="location">{{ currentRegulation.department }} · {{ currentRegulation.hierarchy }}</div>
                <strong>{{ currentRegulation.name }} {{ currentRegulation.version }}</strong>
                <p>{{ currentRegulation.scope }}</p>
              </div>
            </div>
            <div v-else class="subsection">
              <el-upload drag action="#" :auto-upload="false" :limit="1" accept=".docx,.pdf" :on-change="selectUpload">
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖放文件到这里，或 <em>点击选择</em></div>
                <template #tip><div class="el-upload__tip">不接受 .doc、扫描 PDF、图片或包含 OCR 需求的文件。</div></template>
              </el-upload>
              <h3 class="section-title" style="margin-top:22px">选择对比制度</h3>
              <p class="muted">仅在制度冲突维度中，从这里选定的制度内筛查候选条款。</p>
              <el-select v-model="comparisonRegulationIds" multiple filterable placeholder="可选择一个或多个制度" style="width:100%; margin-top:10px">
                <el-option v-for="item in store.activeRegulations.filter(i => i.parseStatus === '解析成功')" :key="item.id" :label="`${item.name} · ${item.version}`" :value="item.id" />
              </el-select>
            </div>
          </template>

          <template v-else-if="step === 1">
            <div class="soft-note">可选择一个或多个条款，系统不会默认进行整份制度审查。</div>
            <el-checkbox-group v-model="selectedClauses" class="subsection">
              <div v-for="clause in currentClauses" :key="clause.id" class="candidate-card" :class="{selected:selectedClauses.includes(clause.id)}">
                <el-checkbox :value="clause.id"><strong>{{ clause.originalNo }} {{ clause.title }}</strong></el-checkbox>
                <div class="table-sub">{{ clause.location }}</div>
                <p>{{ clause.content }}</p>
              </div>
            </el-checkbox-group>
          </template>

          <template v-else-if="step === 2">
            <div class="choice-grid">
              <div v-for="dimension in dimensionMeta" :key="dimension.key" class="choice-card" :class="{selected:selectedDimensions.includes(dimension.key)}" @click="toggleDimension(dimension.key)">
                <h3>{{ dimension.title }}</h3><p>{{ dimension.description }}</p><el-icon v-if="selectedDimensions.includes(dimension.key)" class="check"><Check /></el-icon>
              </div>
            </div>
          </template>

          <template v-else-if="needCandidates && step === 3">
            <div class="soft-note">候选条款由已建立关系的制度中筛出。只有你最终勾选的条款才会进入制度冲突审查。</div>
            <el-checkbox-group v-model="selectedCandidates" class="subsection">
              <div v-for="item in candidates" :key="item.id" class="candidate-card" :class="{selected:selectedCandidates.includes(item.id)}">
                <div class="candidate-top"><el-checkbox :value="item.id"><strong>{{ item.regulationName }} {{ item.version }}</strong></el-checkbox><el-tag size="small" effect="plain">{{ item.evidence.join('＋') }}</el-tag></div>
                <div class="table-sub">{{ item.location }}</div><p>{{ item.content }}</p>
              </div>
            </el-checkbox-group>
            <el-empty v-if="!candidates.length" description="暂无可用候选条款，请先维护制度关系" />
          </template>

          <template v-else>
            <div class="running-wrap">
              <template v-if="runState === 'running'"><div><div class="running-orbit"></div><h2>正在保存审查输入</h2><p class="muted">正在固定所选条款、维度和候选条款快照。</p></div></template>
              <template v-else-if="runState === 'success'"><el-result icon="success" title="审查输入已保存" :sub-title="`已生成审查记录 ${resultId}`"><template #extra><el-button type="primary" @click="router.push('/reviewer/records')">查看审查记录</el-button></template></el-result></template>
              <template v-else-if="runState === 'failed'"><el-result icon="error" title="保存失败" sub-title="未能保存本次审查输入，请重新提交。"><template #extra><el-button type="primary" @click="runReview">重新提交</el-button></template></el-result></template>
            </div>
          </template>

          <div v-if="step < finalStep" class="wizard-footer">
            <el-button :disabled="step===0" @click="previous">上一步</el-button>
            <el-button type="primary" :loading="busy" @click="next">{{ step === finalStep - 1 ? '保存审查输入' : '下一步' }}</el-button>
          </div>
        </div>
      </div>

      <aside class="panel wizard-side">
        <div class="panel-head"><h2>本次选择</h2></div>
        <div class="panel-body summary-list">
          <div><label>待审制度</label><div>{{ currentSourceName || '未选择' }}</div></div>
          <div><label>待审条款</label><div>{{ selectedClauses.length ? `${selectedClauses.length} 个条款` : '尚未选择' }}</div></div>
          <div><label>审查维度</label><div class="tag-row"><el-tag v-for="key in selectedDimensions" :key="key" size="small" effect="plain">{{ dimensionMeta.find(i=>i.key===key)?.title }}</el-tag></div></div>
          <div v-if="needCandidates"><label>冲突候选</label><div>{{ selectedCandidates.length ? `${selectedCandidates.length} 个条款` : '尚未选择' }}</div></div>
        </div>
      </aside>
    </div>
  </div>
</template>
