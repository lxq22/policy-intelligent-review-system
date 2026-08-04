<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Delete, EditPen, Plus } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import PermissionButton from '../../components/PermissionButton.vue'
import { useDataStore } from '../../stores/data'

const store = useDataStore()
const departmentDialog = ref(false)
const categoryDialog = ref(false)
const departmentName = ref('')
const categoryName = ref('')
const editingDepartmentId = ref<number>()
const editingCategoryId = ref<number>()
const unitDialog = ref(false)
const editingUnitId = ref<number>()
const unitForm = reactive<{ name: string; level: '一级单位' | '二级单位'; parentId?: number }>({ name: '', level: '二级单位' })
const primaryUnits = computed(() => store.units.filter((item) => item.level === '一级单位'))

async function addDepartment() {
  if (!departmentName.value.trim()) return ElMessage.warning('请填写部门名称')
  try {
    if (editingDepartmentId.value) await store.updateDepartment(editingDepartmentId.value, departmentName.value.trim())
    else await store.addDepartment(departmentName.value.trim())
    departmentName.value = ''
    departmentDialog.value = false
    ElMessage.success(editingDepartmentId.value ? '部门已更新' : '部门已添加')
    editingDepartmentId.value = undefined
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '部门保存失败')
  }
}

async function addCategory() {
  if (!categoryName.value.trim()) return ElMessage.warning('请填写分类名称')
  try {
    if (editingCategoryId.value) await store.updateCategory(editingCategoryId.value, categoryName.value.trim())
    else await store.addCategory(categoryName.value.trim())
    categoryName.value = ''
    categoryDialog.value = false
    ElMessage.success(editingCategoryId.value ? '分类已更新' : '分类已添加')
    editingCategoryId.value = undefined
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '分类保存失败')
  }
}

async function addUnit() {
  if (!unitForm.name.trim()) return ElMessage.warning('请填写单位名称')
  if (unitForm.level === '二级单位' && !unitForm.parentId) return ElMessage.warning('请选择所属一级单位')
  try {
    const payload = { ...unitForm, parentId: unitForm.level === '一级单位' ? undefined : unitForm.parentId }
    if (editingUnitId.value) await store.updateUnit(editingUnitId.value, payload)
    else await store.addUnit(payload)
    Object.assign(unitForm, { name: '', level: '二级单位', parentId: undefined })
    unitDialog.value = false
    ElMessage.success('单位隶属已保存，自动关系将按当前隶属实时计算')
    editingUnitId.value = undefined
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '单位保存失败')
  }
}

function openDepartment(item?: { id: number; name: string }) {
  editingDepartmentId.value = item?.id
  departmentName.value = item?.name || ''
  departmentDialog.value = true
}

function openCategory(item?: { id: number; name: string }) {
  editingCategoryId.value = item?.id
  categoryName.value = item?.name || ''
  categoryDialog.value = true
}

function openUnit(item?: (typeof store.units)[number]) {
  editingUnitId.value = item?.id
  Object.assign(unitForm, {
    name: item?.name || '',
    level: item?.level || '二级单位',
    parentId: item?.parentId,
  })
  unitDialog.value = true
}

async function removeMasterData(kind: 'department' | 'category' | 'unit', id: number, name: string) {
  const confirmed = await ElMessageBox.confirm(`确认删除“${name}”吗？已使用该数据的制度将保留，但对应字段会被清空。`, '删除基础数据', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return
  try {
    if (kind === 'department') await store.deleteDepartment(id)
    else if (kind === 'category') await store.deleteCategory(id)
    else await store.deleteUnit(id)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Relations & Master Data" title="关系与基础数据" description="维护部门、制度分类和一级—二级单位隶属；这些数据用于自动生成默认制度关系。">
      <template #actions>
        <PermissionButton permission="relation" type="primary" :icon="Connection" @click="$router.push('/reviewer/regulations')">从制度详情添加关系</PermissionButton>
      </template>
    </PageHeader>

    <el-alert title="关系建立规则" type="info" :closable="false" show-icon style="margin-bottom:18px">
      <template #default>同一部门的制度自动双向关联；一级单位制度与其所属二级单位制度自动建立上下位关系；疑似引用只作为建议，人工确认前不建立正式关系。</template>
    </el-alert>

    <div class="detail-grid">
      <div class="detail-main">
        <div class="panel">
          <div class="panel-head">
            <div><h2>单位隶属关系</h2><p class="muted">用于自动识别上位、下位制度</p></div>
            <PermissionButton permission="relation" :icon="Plus" @click="openUnit()">新增单位</PermissionButton>
          </div>
          <el-table :data="store.units">
            <el-table-column prop="name" label="单位名称" min-width="180" />
            <el-table-column prop="level" label="单位层级" width="120" />
            <el-table-column prop="parentName" label="所属一级单位" min-width="170"><template #default="{row}">{{ row.parentName || '—' }}</template></el-table-column>
            <el-table-column label="操作" width="150"><template #default="{row}"><div class="table-actions"><PermissionButton permission="relation" :icon="EditPen" @click="openUnit(row)">修改</PermissionButton><PermissionButton permission="relation" type="danger" :icon="Delete" @click="removeMasterData('unit', row.id, row.name)">删除</PermissionButton></div></template></el-table-column>
          </el-table>
        </div>

        <div class="panel">
          <div class="panel-head"><h2>已生效的自动关系</h2><span class="muted">只读预览</span></div>
          <el-table :data="store.activeRegulations.flatMap(item => item.relations.filter(r => r.source === '系统自动').map(r => ({ ...r, currentName: item.name })))">
            <el-table-column prop="currentName" label="当前制度" min-width="200" />
            <el-table-column prop="type" label="关系" width="100"><template #default="{row}"><el-tag effect="plain">{{ row.type }}</el-tag></template></el-table-column>
            <el-table-column prop="targetName" label="目标制度" min-width="200" />
            <el-table-column prop="note" label="自动建立依据" min-width="220" />
          </el-table>
        </div>
      </div>

      <div class="detail-side">
        <div class="panel">
          <div class="panel-head"><h2>部门</h2><PermissionButton permission="relation" :icon="Plus" @click="openDepartment()">新增</PermissionButton></div>
          <el-table :data="store.departmentItems" size="small"><el-table-column prop="name" label="名称" min-width="110"/><el-table-column label="操作" width="160"><template #default="{row}"><div class="table-actions"><PermissionButton permission="relation" :icon="EditPen" @click="openDepartment(row)">修改</PermissionButton><PermissionButton permission="relation" type="danger" :icon="Delete" @click="removeMasterData('department', row.id, row.name)">删除</PermissionButton></div></template></el-table-column></el-table>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>制度分类</h2><PermissionButton permission="relation" :icon="Plus" @click="openCategory()">新增</PermissionButton></div>
          <el-table :data="store.categoryItems" size="small"><el-table-column prop="name" label="名称" min-width="110"/><el-table-column label="操作" width="160"><template #default="{row}"><div class="table-actions"><PermissionButton permission="relation" :icon="EditPen" @click="openCategory(row)">修改</PermissionButton><PermissionButton permission="relation" type="danger" :icon="Delete" @click="removeMasterData('category', row.id, row.name)">删除</PermissionButton></div></template></el-table-column></el-table>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>权限边界</h2></div>
          <div class="panel-body"><p class="muted">部门、分类、单位隶属和制度关系的新增、修改、删除统一受“关系管理”权限控制。</p></div>
        </div>
      </div>
    </div>

    <el-dialog v-model="departmentDialog" :title="editingDepartmentId ? '修改部门' : '新增部门'" width="440px">
      <el-input v-model="departmentName" placeholder="部门名称" />
      <template #footer><el-button @click="departmentDialog=false">取消</el-button><el-button type="primary" @click="addDepartment">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="categoryDialog" :title="editingCategoryId ? '修改制度分类' : '新增制度分类'" width="440px">
      <el-input v-model="categoryName" placeholder="分类名称" />
      <template #footer><el-button @click="categoryDialog=false">取消</el-button><el-button type="primary" @click="addCategory">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="unitDialog" :title="editingUnitId ? '修改单位及隶属' : '新增单位及隶属'" width="500px">
      <el-form label-position="top">
        <el-form-item label="单位名称"><el-input v-model="unitForm.name" /></el-form-item>
        <el-form-item label="单位层级"><el-radio-group v-model="unitForm.level"><el-radio-button value="一级单位">一级单位</el-radio-button><el-radio-button value="二级单位">二级单位</el-radio-button></el-radio-group></el-form-item>
        <el-form-item v-if="unitForm.level === '二级单位'" label="所属一级单位"><el-select v-model="unitForm.parentId" style="width:100%"><el-option v-for="item in primaryUnits" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="unitDialog=false">取消</el-button><el-button type="primary" @click="addUnit">保存</el-button></template>
    </el-dialog>
  </div>
</template>
