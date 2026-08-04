import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { PermissionKey, User } from '../types'
import { apiRequest, jsonBody } from '../api/client'

export const useSessionStore = defineStore('session', () => {
  const currentUser = ref<User | null>(null)
  const initialized = ref(false)

  const role = computed(() => currentUser.value?.role)
  const isReviewer = computed(() => role.value === 'reviewer')
  const isAdmin = computed(() => role.value === 'admin')

  async function login(username: string, password: string) {
    const user = await apiRequest<User>('/auth/login', {
      method: 'POST',
      ...jsonBody({ username, password }),
    })
    currentUser.value = user
    initialized.value = true
    return user
  }

  async function useDemo(roleToUse: 'reviewer' | 'admin' | 'limited') {
    const username = roleToUse === 'admin' ? 'admin' : roleToUse === 'limited' ? 'reviewer_limited' : 'reviewer'
    return login(username, 'demo123')
  }

  async function logout() {
    try {
      await apiRequest<void>('/auth/logout', { method: 'POST' })
    } finally {
      currentUser.value = null
      initialized.value = true
    }
  }

  async function restore() {
    if (initialized.value) return currentUser.value
    try {
      currentUser.value = await apiRequest<User>('/auth/me')
    } catch {
      currentUser.value = null
    } finally {
      initialized.value = true
    }
    return currentUser.value
  }

  function clearLocal() {
    currentUser.value = null
  }

  function hasPermission(permission: PermissionKey) {
    return Boolean(currentUser.value?.permissions[permission])
  }

  return { currentUser, initialized, role, isReviewer, isAdmin, login, useDemo, logout, restore, clearLocal, hasPermission }
})
