<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['patch'])
const options = ref({ cities: [], categories: [] })
const optionError = ref(false)
let controller

const update = (key, value) => emit('patch', { [key]: value })
const cities = computed(() => [...new Set([...options.value.cities, props.modelValue.city].filter(Boolean))])
const categories = computed(() => [...new Set([...options.value.categories, props.modelValue.job_category].filter(Boolean))])

const loadOptions = async () => {
  controller?.abort()
  controller = new AbortController()
  optionError.value = false
  try {
    const response = await fetch('/api/job-goal/options', { signal: controller.signal })
    if (!response.ok) throw new Error('options unavailable')
    options.value = await response.json()
  } catch (error) {
    if (error.name !== 'AbortError') optionError.value = true
  }
}
onMounted(loadOptions)
onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <fieldset class="goal-fields" :disabled="disabled">
    <legend class="sr-only">求职筛选条件</legend>
    <label>
      <span>目标城市</span>
      <select :value="modelValue.city" @change="update('city', $event.target.value)">
        <option value="">全部城市</option>
        <option v-for="city in cities" :key="city" :value="city">{{ city }}</option>
      </select>
    </label>
    <label>
      <span>岗位类别</span>
      <select :value="modelValue.job_category" @change="update('job_category', $event.target.value)">
        <option value="">不限类别</option>
        <option v-for="category in categories" :key="category" :value="category">{{ category }}</option>
      </select>
    </label>
    <label>
      <span>招聘类型</span>
      <select :value="modelValue.recruitment_type" @change="update('recruitment_type', $event.target.value)">
        <option value="">不限类型</option>
        <option value="实习">实习</option>
        <option value="校招">校招</option>
      </select>
    </label>
    <label>
      <span>技术关键词</span>
      <input :value="modelValue.keyword" maxlength="120" placeholder="例如 Java 或 Python"
        @input="update('keyword', $event.target.value)" />
    </label>
    <label>
      <span>我的学历</span>
      <select :value="modelValue.education" @change="update('education', $event.target.value)">
        <option value="">不限学历</option>
        <option v-for="degree in ['高中', '中专', '大专', '本科', '硕士', '博士']" :key="degree">{{ degree }}</option>
      </select>
    </label>
    <label>
      <span>最低期望月薪（K）</span>
      <input :value="modelValue.min_salary" type="number" min="0" step="any" placeholder="例如 5"
        @input="update('min_salary', $event.target.value)" />
    </label>
    <label v-if="modelValue.city" class="expand-option">
      <input :checked="modelValue.expand_city" type="checkbox" @change="update('expand_city', $event.target.checked)" />
      <span>目标城市没有符合条件的岗位时，查看其他城市</span>
    </label>
    <p v-if="optionError" class="option-error" role="status">
      暂时无法加载城市和类别。<button type="button" @click="loadOptions">重试</button>
    </p>
  </fieldset>
</template>

<style scoped>
.goal-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px 16px; padding: 0; margin: 0; min-width: 0; border: 0; }
.goal-fields label { display: grid; align-content: start; gap: 6px; color: #263550; font-size: 13px; }
.goal-fields label > span { font-weight: 600; }
.goal-fields select, .goal-fields input:not([type=checkbox]) {
  box-sizing: border-box; width: 100%; min-width: 0; height: 42px; padding: 0 10px;
  border: 1px solid #dbe4f1; border-radius: 8px; color: #17243e; background: #fff; font: inherit;
}
.goal-fields :is(select, input, button):focus-visible { outline: 2px solid #4f46e5; outline-offset: 2px; }
.goal-fields .expand-option { grid-column: 1 / -1; display: flex; align-items: flex-start; gap: 7px; line-height: 1.5; }
.expand-option input { margin: 3px 0 0; accent-color: #4f46e5; }
.goal-fields .option-error { grid-column: 1 / -1; margin: 0; color: #9a3412; font-size: 13px; }
.option-error button { margin-left: 5px; cursor: pointer; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
@media (max-width: 860px) { .goal-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 520px) { .goal-fields { grid-template-columns: 1fr; } }
</style>
