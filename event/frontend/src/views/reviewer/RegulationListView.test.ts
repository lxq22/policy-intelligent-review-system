// @vitest-environment jsdom

import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ElementPlus, { ElMessage } from 'element-plus'
import RegulationListView from './RegulationListView.vue'
import { useDataStore } from '../../stores/data'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

function mountView() {
  return shallowMount(RegulationListView, {
    global: {
      plugins: [ElementPlus],
      stubs: {
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        PermissionButton: { template: '<button><slot /></button>' },
        ElDialog: { template: '<div><slot /><slot name="footer" /></div>' },
        ElForm: { template: '<form><slot /></form>' },
        ElFormItem: { template: '<label><slot /></label>' },
        ElRow: { template: '<div><slot /></div>' },
        ElCol: { template: '<div><slot /></div>' },
        ElUpload: { template: '<div><slot /></div>' },
        SelectedFileCard: { props: ['file'], template: '<div>{{ file.name }}</div>' },
      },
    },
  })
}

describe('RegulationListView initial file upload', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    push.mockReset()
  })

  it('requires a real file before creating a regulation', async () => {
    const store = useDataStore()
    const create = vi.spyOn(store, 'createRegulationWithFile')
    const warning = vi.spyOn(ElMessage, 'warning').mockImplementation(() => undefined as never)
    const wrapper = mountView()
    const vm = wrapper.vm as unknown as {
      form: { name: string }
      save: () => Promise<void>
    }
    vm.form.name = '必须上传文件的制度'

    await vm.save()

    expect(warning).toHaveBeenCalledWith('请上传制度文件')
    expect(create).not.toHaveBeenCalled()
  })

  it('shows the selected file and creates the parsed regulation', async () => {
    const store = useDataStore()
    const create = vi.spyOn(store, 'createRegulationWithFile').mockResolvedValue({ id: 18 } as never)
    const wrapper = mountView()
    const file = new File(['制度正文'], '新制度.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const vm = wrapper.vm as unknown as {
      form: { name: string }
      selectInitialFile: (upload: { raw: File }) => void
      save: () => Promise<void>
    }
    vm.form.name = '新制度'

    vm.selectInitialFile({ raw: file })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('新制度.docx')
    await vm.save()
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ name: '新制度' }), file)
    expect(push).toHaveBeenCalledWith('/reviewer/regulations/18')
  })
})
