<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, RefreshLeft, Search } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { useDataStore } from '../../stores/data'
import type { OperationLog } from '../../types'

const store = useDataStore()
const activeTab = ref('deleted')
const keyword = ref('')
const filteredLogs = computed(() => store.logs.filter((item) => !keyword.value || item.regulationName.includes(keyword.value) || item.operator.includes(keyword.value)))

async function restore(id: number, name: string) {
  const confirmed = await ElMessageBox.confirm(`恢复后“${name}”将重新出现在审查人员制度库。`, '确认恢复制度', {
    type: 'info',
    confirmButtonText: '确认恢复',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return
  try {
    await store.restoreRegulation(id)
    ElMessage.success('制度已恢复，并记录恢复操作')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '恢复失败')
  }
}

async function removeLog(log: OperationLog) {
  const result = await ElMessageBox.confirm(
    log.reportCount
      ? `该制度关联 ${log.reportCount} 份历史审查报告。是否在删除操作记录时一并永久删除这些报告？`
      : '删除后该条操作记录将不可恢复。',
    '删除历史操作记录',
    {
      confirmButtonText: log.reportCount ? '连同报告一起删除' : '确认删除',
      cancelButtonText: '仅取消操作',
      type: 'warning',
    },
  ).catch(() => 'cancel')
  if (result === 'cancel') return
  try {
    await store.deleteLog(log.id, Boolean(log.reportCount))
    ElMessage.success(log.reportCount ? '操作记录及关联历史报告已删除' : '操作记录已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '记录删除失败')
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Recovery & Operation History" title="删除恢复与历史" description="管理员可恢复已删除制度，并查看或删除制度新增、删除、恢复记录。"/>
    <div class="soft-note" style="margin-bottom:16px">管理员不进入审查报告内容。删除操作记录时，可以连同该制度的历史审查报告一起永久删除。</div>
    <div class="panel">
      <el-tabs v-model="activeTab" style="padding:0 20px">
        <el-tab-pane :label="`已删除制度（${store.deletedRegulations.length}）`" name="deleted">
          <div style="padding-bottom:22px">
            <el-empty v-if="!store.deletedRegulations.length" description="当前没有已删除制度" />
            <el-table v-else :data="store.deletedRegulations">
              <el-table-column label="制度名称" min-width="240"><template #default="{row}"><div class="table-title">{{ row.name }}</div><div class="table-sub">{{ row.code }} · {{ row.version }}</div></template></el-table-column>
              <el-table-column prop="department" label="部门" width="160" />
              <el-table-column prop="status" label="原生效状态" width="120" />
              <el-table-column prop="updatedAt" label="最近更新" width="170" />
              <el-table-column label="操作" width="130" fixed="right"><template #default="{row}"><el-button type="primary" plain :icon="RefreshLeft" @click="restore(row.id,row.name)">恢复制度</el-button></template></el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        <el-tab-pane :label="`操作历史（${store.logs.length}）`" name="history">
          <div style="padding-bottom:22px">
            <div class="filter-row" style="margin:12px 0 16px"><el-input v-model="keyword" clearable placeholder="按制度名称或操作人搜索" :prefix-icon="Search" /><span class="filter-spacer"></span><span class="muted">只记录新增、删除和恢复</span></div>
            <el-table :data="filteredLogs">
              <el-table-column label="操作类型" width="110"><template #default="{row}"><el-tag :type="row.type==='删除制度'?'danger':row.type==='恢复制度'?'success':'primary'" effect="plain">{{ row.type }}</el-tag></template></el-table-column>
              <el-table-column prop="regulationName" label="制度名称" min-width="230" />
              <el-table-column prop="operator" label="操作人" width="120" />
              <el-table-column prop="operatedAt" label="操作时间" width="180" />
              <el-table-column label="关联历史报告" width="130"><template #default="{row}">{{ row.reportCount }} 份</template></el-table-column>
              <el-table-column label="操作" width="130" fixed="right"><template #default="{row}"><el-button link type="danger" :icon="Delete" @click="removeLog(row)">删除记录</el-button></template></el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>
