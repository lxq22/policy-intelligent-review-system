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
      uploadState: string
      step: number
      selectUpload: (upload: { raw: File }) => Promise<void>
    }
    vm.sourceType = 'temporary'

    await vm.selectUpload({ raw: new File(['pdf'], '扫描制度.pdf', { type: 'application/pdf' }) })

    expect(vm.step).toBe(0)
    expect(vm.uploadState).toBe('error')
    expect(message).toHaveBeenCalledWith('扫描 PDF 不受支持')
  })

  it('uploads immediately and previews parsed clauses before the next step', async () => {
    const store = useDataStore()
    const file = new File(['正文'], '待审制度.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const upload = vi.spyOn(store, 'uploadTemporaryFile').mockResolvedValue({
      id: 12,
      originalName: file.name,
      parseStatus: '解析成功',
      clauses: [{ id: 21, originalNo: '第一条', title: '总则', content: '本制度适用于当前单位。', level: 'article', location: '第一章 > 第一条' }],
    })
    const wrapper = shallowMount(ReviewStartView, {
      global: {
        plugins: [ElementPlus],
        stubs: {
          PageHeader: { template: '<div><slot name="actions" /></div>' },
          ElUpload: { template: '<div><slot /><slot name="tip" /></div>' },
          SelectedFileCard: { props: ['file'], template: '<div>{{ file.name }}</div>' },
          ElCollapse: { template: '<div><slot /></div>' },
          ElCollapseItem: { template: '<div><slot name="title" /><slot /></div>' },
        },
      },
    })
    const vm = wrapper.vm as unknown as {
      sourceType: 'library' | 'temporary'
      selectUpload: (upload: { raw: File }) => Promise<void>
    }
    vm.sourceType = 'temporary'

    await vm.selectUpload({ raw: file })
    await wrapper.vm.$nextTick()

    expect(upload).toHaveBeenCalledWith(file)
    expect(wrapper.text()).toContain('待审制度.docx')
    expect(wrapper.text()).toContain('解析成功，共 1 条')
    expect(wrapper.text()).toContain('第一条')
    expect(wrapper.text()).toContain('本制度适用于当前单位。')
  })

  it('clears old parsed and selected data when removing a temporary file', async () => {
    const wrapper = shallowMount(ReviewStartView, { global: { plugins: [ElementPlus] } })
    const vm = wrapper.vm as unknown as {
      selectedFile?: File
      temporaryFile?: object
      selectedClauses: number[]
      selectedCandidates: number[]
      comparisonRegulationIds: number[]
      removeTemporaryFile: () => void
    }
    vm.selectedFile = new File(['正文'], '旧制度.docx')
    vm.temporaryFile = { id: 1 }
    vm.selectedClauses = [11]
    vm.selectedCandidates = [22]
    vm.comparisonRegulationIds = [3]

    vm.removeTemporaryFile()

    expect(vm.selectedFile).toBeUndefined()
    expect(vm.temporaryFile).toBeUndefined()
    expect(vm.selectedClauses).toEqual([])
    expect(vm.selectedCandidates).toEqual([])
    expect(vm.comparisonRegulationIds).toEqual([])
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
