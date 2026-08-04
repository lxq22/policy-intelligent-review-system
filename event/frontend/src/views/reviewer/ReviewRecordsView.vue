<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, View } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { useDataStore } from '../../stores/data'

const router = useRouter()
const store = useDataStore()
const keyword = ref('')
const filtered = computed(() => store.records.filter((item) => !keyword.value || item.regulationName.includes(keyword.value) || item.id.includes(keyword.value)))
const labels = { semantic: '语义分歧', rule: '规则匹配', conflict: '制度冲突', consistency: '一致性' }
</script>

<template>
  <div>
    <PageHeader eyebrow="Review Records" title="审查记录" description="每次审查独立保留，以“制度名称＋日期＋当日序号”自动编号。">
      <template #actions><el-button type="primary" :icon="Plus" @click="router.push('/reviewer/review/new')">发起新审查</el-button></template>
    </PageHeader>
    <div class="soft-note" style="margin-bottom:16px">审查运行中的成功、失败只在当次页面反馈；历史记录不保存或筛选任务状态。</div>
    <div class="panel filter-panel">
      <div class="filter-row"><el-input v-model="keyword" clearable placeholder="按制度名称或自动编号搜索" :prefix-icon="Search" /><span class="filter-spacer"></span><span class="muted">共 {{ filtered.length }} 条记录</span></div>
    </div>
    <div class="panel">
      <el-table :data="filtered">
        <el-table-column label="自动编号" min-width="290">
          <template #default="{row}"><div class="table-title">{{ row.id }}</div><div class="table-sub">不可编辑</div></template>
        </el-table-column>
        <el-table-column prop="regulationName" label="待审制度" min-width="190" />
        <el-table-column label="所选范围" min-width="250">
          <template #default="{row}">
            <div>{{ row.clauseCount }} 个条款</div>
            <div class="tag-row" style="margin-top:6px"><el-tag v-for="key in row.dimensions" :key="key" size="small" effect="plain">{{ labels[key as keyof typeof labels] }}</el-tag></div>
          </template>
        </el-table-column>
        <el-table-column label="问题数" width="90"><template #default="{row}"><strong>{{ row.problemCount }}</strong></template></el-table-column>
        <el-table-column prop="createdBy" label="发起人" width="100" />
        <el-table-column prop="createdAt" label="创建时间" width="160" />
        <el-table-column label="操作" width="105" fixed="right"><template #default="{row}"><el-button link type="primary" :icon="View" @click="router.push(`/reviewer/reports/${row.id}`)">查看报告</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!filtered.length" description="没有匹配的审查记录" />
    </div>
  </div>
</template>
