import { computed, onBeforeUnmount, ref, watch } from 'vue'

// 每次重新打开站点都回到正式实采范围，避免误将模拟结果用于招聘分析。
export const datasetScope = ref('real')
export const datasetInfo = ref(null)
export const datasetError = ref('')
export const datasetLabel = computed(() => ({ real: '实采样本', synthetic: '仿真测试样本', all: '混合测试样本' })[datasetScope.value])

export function datasetUrl(path, fields = {}) {
  const query = new URLSearchParams({ dataset_scope: datasetScope.value })
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== '' && value != null && !Array.isArray(value) && key !== 'dataset_scope' && key !== 'expand_city') query.set(key, value)
  })
  return `${path}?${query}`
}

export async function refreshDatasetInfo() {
  const scope = datasetScope.value
  datasetInfo.value = null
  datasetError.value = ''
  try {
    const response = await fetch(datasetUrl('/api/dataset'))
    if (!response.ok) throw new Error('暂时无法读取数据版本，请稍后重试。')
    const info = await response.json()
    if (scope === datasetScope.value) datasetInfo.value = info
  } catch (error) {
    if (scope === datasetScope.value) datasetError.value = error.message
  }
}

export function useSkillOptions(goal) {
  const skillOptions = ref([])
  const skillOptionError = ref('')
  let controller
  watch(() => [datasetScope.value, goal.value?.city, goal.value?.job_category, goal.value?.recruitment_type], async () => {
    controller?.abort()
    const active = new AbortController()
    controller = active
    skillOptionError.value = ''
    try {
      const { city, job_category, recruitment_type } = goal.value || {}
      const response = await fetch(datasetUrl('/api/skills', { city, job_category, recruitment_type }), { signal: active.signal })
      if (!response.ok) throw new Error('技能选项暂时不可用，仍可手动添加。')
      const data = await response.json()
      if (controller === active) skillOptions.value = data.skills.map(item => item.name)
    } catch (error) {
      if (error.name !== 'AbortError' && controller === active) { skillOptions.value = []; skillOptionError.value = error.message }
    }
  }, { immediate: true })
  onBeforeUnmount(() => controller?.abort())
  return { skillOptions, skillOptionError }
}
