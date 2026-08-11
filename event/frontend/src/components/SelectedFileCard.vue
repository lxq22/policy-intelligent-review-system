<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheckFilled, Delete, Document, Loading } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  file: File
  status?: 'ready' | 'parsing' | 'success' | 'error'
  message?: string
}>(), {
  status: 'ready',
  message: '',
})

defineEmits<{ remove: [] }>()

const size = computed(() => {
  if (props.file.size < 1024) return `${props.file.size} B`
  if (props.file.size < 1024 * 1024) return `${(props.file.size / 1024).toFixed(1)} KB`
  return `${(props.file.size / 1024 / 1024).toFixed(1)} MB`
})

const statusText = computed(() => ({
  ready: '已选择，点击此处可重新选择',
  parsing: '正在上传并解析条款…',
  success: props.message || '解析成功',
  error: props.message || '解析失败，请重新上传',
})[props.status])
</script>

<template>
  <div class="selected-file" :class="`is-${status}`">
    <div class="file-icon"><el-icon><Document /></el-icon></div>
    <div class="file-info">
      <strong>{{ file.name }}</strong>
      <span>{{ size }} · {{ statusText }}</span>
    </div>
    <el-icon v-if="status === 'parsing'" class="state-icon is-loading"><Loading /></el-icon>
    <el-icon v-else-if="status === 'success'" class="state-icon success"><CircleCheckFilled /></el-icon>
    <el-button class="remove-file" link type="danger" :icon="Delete" @click.stop="$emit('remove')">删除</el-button>
  </div>
</template>

<style scoped>
.selected-file { display: flex; align-items: center; gap: 14px; width: 100%; min-height: 82px; padding: 16px 18px; border-radius: 10px; text-align: left; background: #f7fbfc; box-sizing: border-box; }
.selected-file.is-success { background: #f2fbf8; }
.selected-file.is-error { background: #fff6f5; }
.file-icon { display: grid; place-items: center; width: 42px; height: 42px; flex: none; border-radius: 9px; color: #0f8b85; background: #e4f5f3; font-size: 23px; }
.file-info { min-width: 0; flex: 1; }
.file-info strong, .file-info span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-info strong { color: #17313f; font-size: 14px; }
.file-info span { margin-top: 6px; color: #71838d; font-size: 12px; }
.state-icon { flex: none; font-size: 20px; color: #83949d; }
.state-icon.success { color: #16a077; }
.remove-file { flex: none; }
@media (max-width: 640px) {
  .selected-file { align-items: flex-start; flex-wrap: wrap; }
  .file-info { width: calc(100% - 60px); }
  .remove-file { margin-left: 56px; }
}
</style>
