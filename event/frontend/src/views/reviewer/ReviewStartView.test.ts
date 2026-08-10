// @vitest-environment jsdom

import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import ReviewStartView from './ReviewStartView.vue'
import { useDataStore } from '../../stores/data'


vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))


describe('ReviewStartView M4 flow', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('offers real temporary upload comparison selection without the old mock notice', async () => {
    const wrapper = shallowMount(ReviewStartView, {
      global: {
        plugins: [ElementPlus],
        stubs: {
          PageHeader: { template: '<div><slot name="actions" /></div>' },
          ElIcon: { template: '<i><slot /></i>' },
        },
      },
    })

    await wrapper.findAll('.choice-card')[1].trigger('click')

    expect(wrapper.text()).toContain('选择对比制度')
    expect(wrapper.text()).not.toContain('真实上传与解析将在 M4 接入')
  })

  it('keeps the user on source selection when temporary parsing fails', async () => {
    const store = useDataStore()
    vi.spyOn(store, 'uploadTemporaryFile').mockRejectedValue(new Error('扫描 PDF 不受支持'))
    const message = vi.spyOn(ElMessage, 'error').mockImplementation(() => undefined as never)
    const wrapper = shallowMount(ReviewStartView, { global: { plugins: [ElementPlus] } })
    const vm = wrapper.vm as unknown as {
      sourceType: 'library' | 'temporary'
      selectedFile?: File
      step: number
      next: () => Promise<void>
    }
    vm.sourceType = 'temporary'
    vm.selectedFile = new File(['pdf'], '扫描制度.pdf', { type: 'application/pdf' })

    await vm.next()

    expect(vm.step).toBe(0)
    expect(message).toHaveBeenCalledWith('扫描 PDF 不受支持')
  })

  it('does not advance without clauses, dimensions, or conflict candidates', async () => {
    const wrapper = shallowMount(ReviewStartView, { global: { plugins: [ElementPlus] } })
    const vm = wrapper.vm as unknown as {
      step: number
      selectedClauses: Array<number>
      selectedDimensions: Array<string>
      selectedCandidates: Array<number>
      next: () => Promise<void>
    }

    vm.step = 1
    vm.selectedClauses = []
    await vm.next()
    expect(vm.step).toBe(1)

    vm.step = 2
    vm.selectedClauses = [1]
    vm.selectedDimensions = []
    await vm.next()
    expect(vm.step).toBe(2)

    vm.step = 3
    vm.selectedDimensions = ['conflict']
    vm.selectedCandidates = []
    await vm.next()
    expect(vm.step).toBe(3)
  })
})
