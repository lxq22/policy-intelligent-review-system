import { createRouter, createWebHistory } from 'vue-router'
import { useSessionStore } from '../stores/session'
import LoginView from '../views/LoginView.vue'
import AppShell from '../components/AppShell.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    {
      path: '/reviewer',
      component: AppShell,
      meta: { role: 'reviewer' },
      children: [
        { path: '', redirect: '/reviewer/regulations' },
        { path: 'regulations', name: 'regulations', component: () => import('../views/reviewer/RegulationListView.vue') },
        { path: 'regulations/:id', name: 'regulation-detail', component: () => import('../views/reviewer/RegulationDetailView.vue') },
        { path: 'relations', name: 'relations', component: () => import('../views/reviewer/RelationManagementView.vue') },
        { path: 'review/new', name: 'review-new', component: () => import('../views/reviewer/ReviewStartView.vue') },
        { path: 'records', name: 'records', component: () => import('../views/reviewer/ReviewRecordsView.vue') },
        { path: 'reports/:id', name: 'report-detail', component: () => import('../views/reviewer/ReviewReportView.vue') },
      ],
    },
    {
      path: '/admin',
      component: AppShell,
      meta: { role: 'admin' },
      children: [
        { path: '', redirect: '/admin/users' },
        { path: 'users', name: 'admin-users', component: () => import('../views/admin/UserManagementView.vue') },
        { path: 'history', name: 'admin-history', component: () => import('../views/admin/AdminHistoryView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

router.beforeEach(async (to) => {
  const session = useSessionStore()
  await session.restore()
  if (to.meta.public) {
    if (session.isReviewer) return '/reviewer/regulations'
    if (session.isAdmin) return '/admin/users'
    return true
  }
  if (!session.currentUser) return '/login'
  const requiredRole = to.matched.find((record) => record.meta.role)?.meta.role
  if (requiredRole && requiredRole !== session.role) {
    return session.isAdmin ? '/admin/users' : '/reviewer/regulations'
  }
  return true
})

export default router
