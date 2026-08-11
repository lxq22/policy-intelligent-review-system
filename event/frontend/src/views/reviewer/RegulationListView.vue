<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, EditPen, Plus, Refresh, Search, View } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import PermissionButton from '../../components/PermissionButton.vue'
import SelectedFileCard from '../../components/SelectedFileCard.vue'
import { useDataStore } from '../../stores/data'
import type { Regulation } from '../../types'

const router = useRouter()
const store = useDataStore()
const loading = ref(true)
const dialogVisible = ref(false)
const editingId = ref<number>()
const initialFile = ref<File>()
const saving = ref(false)
const filters = reactive({ keyword: '', department: '', hierarchy: '', status: '' })
const form = reactive<Partial<Regulation>>({
  name: '',
  code: '',
  department: '',
  category: '',
  unitId: undefined,
  hierarchy: '二级单位制度',
  version: 'V1.0',
  publishDate: '',
  effectiveDate: '',
  expiryDate: '',
  status: '生效中',
  scope: '',
  fileName: '',
})

onMounted(() => window.setTimeout(() => (loading.value = false), 450))

const filtered = computed(() =>
  store.activeRegulations.filter((item) => {
    const matchesKeyword = !filters.keyword || item.name.includes(filters.keyword)
    return (
      matchesKeyword &&
      (!filters.department || item.department === filters.department) &&
      (!filters.hierarchy || item.hierarchy === filters.hierarchy) &&
      (!filters.status || item.status === filters.status)
    )
  }),
)

const effectiveCount = computed(() => store.activeRegulations.filter((item) => item.status === '生效中').length)
const parsedCount = computed(() => store.activeRegulations.filter((item) => item.parseStatus === '解析成功').length)
const relationCount = computed(() => store.activeRegulations.reduce((sum, item) => sum + item.relations.length, 0))

function resetForm() {
  editingId.value = undefined
  initialFile.value = undefined
  Object.assign(form, {
    name: '',
    code: '',
    department: '',
    category: '',
    unitId: undefined,
    hierarchy: '二级单位制度',
    version: 'V1.0',
    publishDate: '',
    effectiveDate: '',
    expiryDate: '',
    status: '生效中',
    scope: '',
    fileName: '',
  })
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(item: Regulation) {
  editingId.value = item.id
  Object.assign(form, structuredClone(item))
  dialogVisible.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('为了便于识别，请填写制度名称')
    return
  }
  if (!editingId.value && !initialFile.value) {
    ElMessage.warning('请上传制度文件')
    return
  }
  if (saving.value) return
  saving.value = true
  try {
    const created = editingId.value
      ? await store.saveRegulation({ ...form, id: editingId.value, name: form.name })
      : await store.createRegulationWithFile({ ...form, name: form.name }, initialFile.value!)
    dialogVisible.value = false
    ElMessage.success(editingId.value ? '制度信息已更新' : '制度已上传并解析成功')
    if (!editingId.value && created) router.push(`/reviewer/regulations/${created.id}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function selectInitialFile(upload: UploadFile) {
  if (upload.raw) initialFile.value = upload.raw
}

function removeInitialFile() {
  initialFile.value = undefined
}

async function remove(item: Regulation) {
  const confirmed = await ElMessageBox.confirm(
    `删除后“${item.name}”将不再出现在审查人员界面，管理员仍可恢复。`,
    '确认删除制度',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
  ).catch(() => false)
  if (!confirmed) return
  try {
    await store.deleteRegulation(item.id)
    ElMessage.success('制度已删除，可由管理员恢复')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}

function clearFilters() {
  Object.assign(filters, { keyword: '', department: '', hierarchy: '', status: '' })
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Regulation Library" title="制度库" description="按名称检索制度，并通过部门、制度层级和生效状态缩小范围。">
      <template #actions>
        <PermissionButton permission="upload" type="primary" :icon="Plus" @click="openCreate">新增制度</PermissionButton>
      </template>
    </PageHeader>

    <div class="stats-grid">
      <div class="stat-card accent"><div class="label">制度总数</div><div class="value">{{ store.activeRegulations.length }}</div><div class="hint">当前审查人员可见</div></div>
      <div class="stat-card"><div class="label">生效中</div><div class="value">{{ effectiveCount }}</div><div class="hint">可作为审查与对比来源</div></div>
      <div class="stat-card"><div class="label">解析成功</div><div class="value">{{ parsedCount }}</div><div class="hint">可选择具体条款</div></div>
      <div class="stat-card"><div class="label">已展示关系</div><div class="value">{{ relationCount }}</div><div class="hint">包含自动与已确认关系</div></div>
    </div>

    <div class="panel filter-panel">
      <div class="filter-row">
        <el-input v-model="filters.keyword" clearable placeholder="按制度名称搜索" :prefix-icon="Search" />
        <el-select v-model="filters.department" clearable placeholder="部门">
          <el-option v-for="item in store.departments" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.hierarchy" clearable placeholder="制度层级">
          <el-option label="一级单位制度" value="一级单位制度" />
          <el-option label="二级单位制度" value="二级单位制度" />
        </el-select>
        <el-select v-model="filters.status" clearable placeholder="生效状态">
          <el-option label="生效中" value="生效中" />
          <el-option label="已失效" value="已失效" />
        </el-select>
        <el-button :icon="Refresh" @click="clearFilters">重置</el-button>
        <span class="filter-spacer"></span>
        <span class="muted">共 {{ filtered.length }} 项</span>
      </div>
    </div>

    <div class="panel">
      <el-skeleton v-if="loading" :rows="7" animated style="padding: 24px" />
      <div v-else-if="filtered.length === 0" class="empty-wrap">
        <el-empty description="没有匹配的制度" />
        <h3>尝试调整搜索条件</h3>
        <p>系统只支持按制度名称搜索，以及部门、层级和生效状态筛选。</p>
      </div>
      <el-table v-else :data="filtered" style="width: 100%" row-key="id">
        <el-table-column label="制度名称" min-width="250">
          <template #default="{ row }">
            <div class="table-title">{{ row.name }}</div>
            <div class="table-sub">{{ row.code || '暂无编号' }} · {{ row.version }} · {{ row.fileName }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" width="150" />
        <el-table-column prop="hierarchy" label="制度层级" width="140" />
        <el-table-column label="生效状态" width="112">
          <template #default="{ row }"><span><i class="status-dot" :class="{ expired: row.status === '已失效' }"></i>{{ row.status }}</span></template>
        </el-table-column>
        <el-table-column label="解析" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.parseStatus === '解析成功' ? 'success' : row.parseStatus === '解析失败' ? 'danger' : 'warning'" effect="plain">{{ row.parseStatus }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="最近更新" width="150" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button link type="primary" :icon="View" @click="router.push(`/reviewer/regulations/${row.id}`)">查看</el-button>
              <el-button link :icon="EditPen" @click="openEdit(row)">编辑</el-button>
              <PermissionButton permission="delete" type="danger" :icon="Delete" @click="remove(row)">删除</PermissionButton>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑制度信息' : '新增制度'" width="760px" destroy-on-close>
      <div class="soft-note">当前字段的必填性、唯一性和长度规则尚未确认；原型只要求制度名称便于完成页面演示。</div>
      <el-form label-position="top" class="subsection">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="制度名称"><el-input v-model="form.name" placeholder="填写制度名称" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="制度编号"><el-input v-model="form.code" placeholder="如有可填写" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="部门"><el-select v-model="form.department" allow-create filterable style="width:100%"><el-option v-for="item in store.departments" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="业务分类"><el-select v-model="form.category" allow-create filterable style="width:100%"><el-option v-for="item in store.categories" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="制度层级"><el-select v-model="form.hierarchy" style="width:100%"><el-option label="一级单位制度" value="一级单位制度" /><el-option label="二级单位制度" value="二级单位制度" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="所属单位"><el-select v-model="form.unitId" clearable filterable style="width:100%"><el-option v-for="item in store.units" :key="item.id" :label="`${item.name} · ${item.level}`" :value="item.id" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="版本号"><el-input v-model="form.version" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="发布日期"><el-date-picker v-model="form.publishDate" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="生效日期"><el-date-picker v-model="form.effectiveDate" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="失效日期"><el-date-picker v-model="form.expiryDate" value-format="YYYY-MM-DD" clearable style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="生效状态"><el-select v-model="form.status" style="width:100%"><el-option label="生效中" value="生效中" /><el-option label="已失效" value="已失效" /></el-select></el-form-item></el-col>
          <el-col v-if="!editingId" :span="24">
            <el-form-item label="制度文件（必填）">
              <el-upload class="initial-file-upload" drag action="#" :auto-upload="false" :show-file-list="false" accept=".docx,.pdf" :on-change="selectInitialFile">
                <SelectedFileCard v-if="initialFile" :file="initialFile" @remove="removeInitialFile" />
                <template v-else>
                  <el-icon class="el-icon--upload"><Plus /></el-icon>
                  <div class="el-upload__text">拖放制度文件到这里，或 <em>点击选择</em></div>
                  <div class="upload-hint">支持 .docx 和普通文字 PDF</div>
                </template>
              </el-upload>
            </el-form-item>
          </el-col>
          <el-col :span="24"><el-form-item label="适用范围"><el-input v-model="form.scope" type="textarea" :rows="2" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">{{ editingId ? '保存' : '保存并解析' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.initial-file-upload { width: 100%; }
.initial-file-upload :deep(.el-upload), .initial-file-upload :deep(.el-upload-dragger) { width: 100%; }
.initial-file-upload :deep(.el-upload-dragger) { min-height: 122px; padding: 18px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.initial-file-upload :deep(.selected-file) { margin: -4px; width: calc(100% + 8px); }
.upload-hint { margin-top: 8px; color: #8a9aa3; font-size: 12px; }
</style>
