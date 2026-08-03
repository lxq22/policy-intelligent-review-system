<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { PermissionKey } from '../types'
import { useSessionStore } from '../stores/session'

const props = withDefaults(
  defineProps<{
    permission: PermissionKey
    type?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default'
    plain?: boolean
    icon?: object
  }>(),
  { type: 'default', plain: false },
)
const emit = defineEmits<{ click: [] }>()
const session = useSessionStore()

function handleClick() {
  if (!session.hasPermission(props.permission)) {
    ElMessage.warning('当前账号没有此项权限，请联系系统管理员配置')
    return
  }
  emit('click')
}
</script>

<template>
  <el-button :type="type" :plain="plain" :icon="icon" :class="{ 'permission-disabled': !session.hasPermission(permission) }" @click="handleClick">
    <slot />
  </el-button>
</template>
