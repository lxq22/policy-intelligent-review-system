<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Connection,
  DocumentChecked,
  DocumentCopy,
  Fold,
  List,
  Management,
  Menu,
  Plus,
  SwitchButton,
  User,
} from '@element-plus/icons-vue'
import { useSessionStore } from '../stores/session'
import { useDataStore } from '../stores/data'
import { ElMessage } from 'element-plus'

const session = useSessionStore()
const data = useDataStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const reviewerNav = [
  { path: '/reviewer/regulations', label: '制度库', icon: DocumentCopy },
  { path: '/reviewer/review/new', label: '发起审查', icon: Plus },
  { path: '/reviewer/records', label: '审查记录', icon: DocumentChecked },
  { path: '/reviewer/relations', label: '关系与基础数据', icon: Connection },
]
const adminNav = [
  { path: '/admin/users', label: '人员与权限', icon: User },
  { path: '/admin/history', label: '删除恢复与历史', icon: Management },
]
const navItems = computed(() => (session.isAdmin ? adminNav : reviewerNav))
const areaName = computed(() => (session.isAdmin ? '系统管理区' : '制度审查区'))

async function logout() {
  try {
    await session.logout()
  } finally {
    await router.replace('/login')
  }
}

onMounted(async () => {
  try {
    await data.loadForRole(session.role)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '基础数据加载失败')
  }
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="brand">
        <div class="brand-mark">审</div>
        <div v-if="!collapsed" class="brand-copy">
          <strong>制度智能审查</strong>
          <span>Policy Review</span>
        </div>
      </div>

      <div v-if="!collapsed" class="area-pill">{{ areaName }}</div>

      <nav class="main-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path.startsWith(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="!collapsed">{{ item.label }}</span>
        </router-link>
      </nav>

      <div v-if="session.isReviewer && !collapsed" class="permission-card">
        <div class="permission-title">当前操作权限</div>
        <div class="permission-list">
          <span :class="{ on: session.hasPermission('upload') }">上传</span>
          <span :class="{ on: session.hasPermission('delete') }">删除</span>
          <span :class="{ on: session.hasPermission('relation') }">关系维护</span>
        </div>
      </div>

      <button class="collapse-button" @click="collapsed = !collapsed">
        <el-icon><Fold v-if="!collapsed" /><Menu v-else /></el-icon>
        <span v-if="!collapsed">收起菜单</span>
      </button>
    </aside>

    <main class="main-area">
      <header class="topbar">
        <div>
          <span class="system-context">当前项目单位</span>
          <span class="topbar-divider"></span>
          <span class="prototype-tag">M3 基础业务版</span>
        </div>
        <el-dropdown trigger="click">
          <button class="user-trigger">
            <span class="avatar">{{ session.currentUser?.name.slice(0, 1) }}</span>
            <span class="user-copy">
              <strong>{{ session.currentUser?.name }}</strong>
              <small>{{ session.isAdmin ? '系统管理员' : '审查人员' }}</small>
            </span>
            <el-icon><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                <el-icon><List /></el-icon>{{ session.currentUser?.username }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <section class="page-body">
        <router-view />
      </section>
    </main>
  </div>
</template>
