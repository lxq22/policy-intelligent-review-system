<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Key, Lock, User } from '@element-plus/icons-vue'
import { useSessionStore } from '../stores/session'

const router = useRouter()
const session = useSessionStore()
const loading = ref(false)
const form = reactive({ username: 'reviewer', password: 'demo123' })

async function enter(role?: 'reviewer' | 'admin' | 'limited') {
  loading.value = true
  try {
    const user = await (role ? session.useDemo(role) : session.login(form.username, form.password))
    await new Promise((resolve) => window.setTimeout(resolve, 420))
    router.push(user.role === 'admin' ? '/admin/users' : '/reviewer/regulations')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-story">
      <div class="login-brand">
        <div class="brand-mark large">审</div>
        <span>制度智能审查系统</span>
      </div>
      <div class="story-content">
        <p class="eyebrow light">面向当前项目单位的论文演示原型</p>
        <h1>让制度审查有依据，<br />也有清晰的处理路径。</h1>
        <p class="story-lead">
          集中管理制度、关系与版本，选择具体条款发起四维审查，
          并将每个问题的证据、说明和人工处理完整留痕。
        </p>
        <div class="feature-row">
          <span><el-icon><Check /></el-icon>指定条款审查</span>
          <span><el-icon><Check /></el-icon>四维独立报告</span>
          <span><el-icon><Check /></el-icon>人工处理留痕</span>
        </div>
      </div>
      <div class="story-foot">M5 · 四维智能审查</div>
    </section>

    <section class="login-panel">
      <div class="login-card">
        <p class="eyebrow">欢迎回来</p>
        <h2>登录系统</h2>
        <p class="muted">系统不提供公开注册，请使用管理员创建的账号。</p>

        <el-form label-position="top" class="login-form" @submit.prevent="enter()">
          <el-form-item label="用户名">
            <el-input v-model="form.username" size="large" :prefix-icon="User" autocomplete="username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password size="large" :prefix-icon="Lock" autocomplete="current-password" @keyup.enter="enter()" />
          </el-form-item>
          <el-button type="primary" size="large" class="full-button" :loading="loading" @click="enter()">
            登录
          </el-button>
        </el-form>

        <div class="demo-divider"><span>演示入口</span></div>
        <div class="demo-grid">
          <button @click="enter('reviewer')">
            <el-icon><User /></el-icon>
            <span><strong>审查人员</strong><small>完整三项权限</small></span>
          </button>
          <button @click="enter('limited')">
            <el-icon><Key /></el-icon>
            <span><strong>受限人员</strong><small>验证权限边界</small></span>
          </button>
          <button @click="enter('admin')">
            <el-icon><Lock /></el-icon>
            <span><strong>系统管理员</strong><small>人员与历史管理</small></span>
          </button>
        </div>
        <p class="demo-tip">演示账号统一密码：demo123</p>
      </div>
    </section>
  </div>
</template>
