<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, EditPen, Key, Plus, Setting } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { useDataStore } from '../../stores/data'
import type { PermissionSet, User } from '../../types'

const store = useDataStore()
const keyword = ref('')
const addDialog = ref(false)
const permissionDialog = ref(false)
const editDialog = ref(false)
const selectedUser = ref<User>()
const newUser = reactive({ name: '', username: '', department: '' })
const editUser = reactive({ name: '', department: '' })
const permissionForm = reactive<PermissionSet>({ upload: false, delete: false, relation: false })
const reviewers = computed(() => store.users.filter((item) => item.role === 'reviewer' && (!keyword.value || item.name.includes(keyword.value) || item.username.includes(keyword.value))))

function openPermissions(user: User) {
  selectedUser.value = user
  Object.assign(permissionForm, user.permissions)
  permissionDialog.value = true
}

function openEdit(user: User) {
  selectedUser.value = user
  Object.assign(editUser, { name: user.name, department: user.department })
  editDialog.value = true
}

async function saveUser() {
  if (!selectedUser.value || !editUser.name.trim()) return ElMessage.warning('请填写姓名')
  try {
    await store.updateUser(selectedUser.value.id, { name: editUser.name.trim(), department: editUser.department.trim() })
    editDialog.value = false
    ElMessage.success('审查人员资料已更新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '人员资料保存失败')
  }
}

async function savePermissions() {
  if (!selectedUser.value) return
  try {
    await store.updateUserPermissions(selectedUser.value.id, permissionForm)
    permissionDialog.value = false
    ElMessage.success('三项操作权限已更新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '权限保存失败')
  }
}

async function createUser() {
  if (!newUser.name || !newUser.username) return ElMessage.warning('请填写姓名和用户名')
  try {
    await store.addUser(newUser)
    Object.assign(newUser, { name: '', username: '', department: '' })
    addDialog.value = false
    ElMessage.success('审查人员账号已创建，默认未授予三项操作权限')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '账号创建失败')
  }
}

async function remove(user: User) {
  const confirmed = await ElMessageBox.confirm(`确认删除审查人员“${user.name}”吗？`, '删除人员', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return
  try {
    await store.deleteUser(user.id)
    ElMessage.success('人员账号已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '账号删除失败')
  }
}

async function resetPassword(user: User) {
  try {
    const result = await store.resetUserPassword(user.id)
    ElMessageBox.alert(`已为 ${user.name} 生成一次性显示的临时密码：${result.temporary_password}`, '密码已重置', { confirmButtonText: '知道了' })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '密码重置失败')
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="People & Permissions" title="人员与权限" description="管理员只能管理审查人员账号、状态和三项可配置权限。">
      <template #actions><el-button type="primary" :icon="Plus" @click="addDialog=true">新增审查人员</el-button></template>
    </PageHeader>
    <div class="stats-grid">
      <div class="stat-card accent"><div class="label">审查人员</div><div class="value">{{ reviewers.length }}</div><div class="hint">不包含管理员账号</div></div>
      <div class="stat-card"><div class="label">启用账号</div><div class="value">{{ reviewers.filter(i=>i.enabled).length }}</div><div class="hint">可进入制度审查区</div></div>
      <div class="stat-card"><div class="label">上传权限</div><div class="value">{{ reviewers.filter(i=>i.permissions.upload).length }}</div><div class="hint">可上传制度及新版本</div></div>
      <div class="stat-card"><div class="label">关系管理权限</div><div class="value">{{ reviewers.filter(i=>i.permissions.relation).length }}</div><div class="hint">含基础数据维护</div></div>
    </div>
    <div class="soft-note" style="margin-bottom:16px">查看检索制度、编辑制度信息、指定条款发起审查、查看报告和处理问题属于审查人员默认权限，无需逐项配置。</div>
    <div class="panel filter-panel"><div class="filter-row"><el-input v-model="keyword" clearable placeholder="按姓名或用户名搜索" style="width:320px" /><span class="filter-spacer"></span><span class="muted">共 {{ reviewers.length }} 人</span></div></div>
    <div class="panel">
      <el-table :data="reviewers">
        <el-table-column label="人员" min-width="190"><template #default="{row}"><div class="table-title">{{ row.name }}</div><div class="table-sub">{{ row.username }} · {{ row.department }}</div></template></el-table-column>
        <el-table-column label="账号状态" width="110"><template #default="{row}"><el-switch :model-value="row.enabled" inline-prompt active-text="启用" inactive-text="停用" @change="store.toggleUser(row.id).catch((error) => ElMessage.error(error.message))" /></template></el-table-column>
        <el-table-column label="上传制度" width="105"><template #default="{row}"><el-tag :type="row.permissions.upload?'success':'info'" effect="plain">{{ row.permissions.upload?'允许':'未授权' }}</el-tag></template></el-table-column>
        <el-table-column label="删除制度" width="105"><template #default="{row}"><el-tag :type="row.permissions.delete?'success':'info'" effect="plain">{{ row.permissions.delete?'允许':'未授权' }}</el-tag></template></el-table-column>
        <el-table-column label="关系管理" width="105"><template #default="{row}"><el-tag :type="row.permissions.relation?'success':'info'" effect="plain">{{ row.permissions.relation?'允许':'未授权' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{row}">
            <el-button link :icon="EditPen" @click="openEdit(row)">修改资料</el-button>
            <el-button link type="primary" :icon="Setting" @click="openPermissions(row)">配置权限</el-button>
            <el-button link :icon="Key" @click="resetPassword(row)">重置密码</el-button>
            <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="addDialog" title="新增审查人员" width="560px">
      <el-form label-position="top">
        <el-form-item label="姓名"><el-input v-model="newUser.name" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="newUser.username" /></el-form-item>
        <el-form-item label="所属部门"><el-input v-model="newUser.department" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="addDialog=false">取消</el-button><el-button type="primary" @click="createUser">创建账号</el-button></template>
    </el-dialog>

    <el-dialog v-model="editDialog" :title="`修改审查人员 · ${selectedUser?.username || ''}`" width="520px">
      <el-form label-position="top">
        <el-form-item label="姓名"><el-input v-model="editUser.name" /></el-form-item>
        <el-form-item label="所属部门"><el-input v-model="editUser.department" /></el-form-item>
        <el-form-item label="用户名"><el-input :model-value="selectedUser?.username" disabled /><div class="muted">用户名用于登录，当前需求未确认修改规则。</div></el-form-item>
      </el-form>
      <template #footer><el-button @click="editDialog=false">取消</el-button><el-button type="primary" @click="saveUser">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="permissionDialog" :title="`配置权限 · ${selectedUser?.name || ''}`" width="580px">
      <div class="soft-note">只有上传制度、删除制度和维护关系需要配置；其他审查功能均为默认权限。</div>
      <div class="subsection">
        <div class="choice-card" :class="{selected:permissionForm.upload}" @click="permissionForm.upload=!permissionForm.upload"><h3>上传制度</h3><p>上传制度、新版本和待审文件。</p><el-switch v-model="permissionForm.upload" class="check" @click.stop /></div>
        <div class="choice-card" :class="{selected:permissionForm.delete}" style="margin-top:10px" @click="permissionForm.delete=!permissionForm.delete"><h3>删除制度</h3><p>从审查人员界面业务删除制度，管理员仍可恢复。</p><el-switch v-model="permissionForm.delete" class="check" @click.stop /></div>
        <div class="choice-card" :class="{selected:permissionForm.relation}" style="margin-top:10px" @click="permissionForm.relation=!permissionForm.relation"><h3>关系管理</h3><p>维护制度关系、部门、分类和单位隶属。</p><el-switch v-model="permissionForm.relation" class="check" @click.stop /></div>
      </div>
      <template #footer><el-button @click="permissionDialog=false">取消</el-button><el-button type="primary" @click="savePermissions">保存权限</el-button></template>
    </el-dialog>
  </div>
</template>
