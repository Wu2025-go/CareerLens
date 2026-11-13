<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { postJobGoal } from '../utils/jobGoal'

const props = defineProps({ analysis: { type: Object, required: true } })
const plan = ref(null)
const busy = ref(false)
const error = ref('')
let controller
onBeforeUnmount(() => controller?.abort())

const buildPlan = async () => {
  if (busy.value) return
  busy.value = true
  error.value = ''
  plan.value = null
  controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 50000)
  try {
    plan.value = await postJobGoal('/api/job-goal/plan', props.analysis.conditions, controller.signal)
  } catch (cause) {
    error.value = cause.name === 'AbortError' ? '等待超时，可稍后再试。' : cause.message
  } finally {
    clearTimeout(timer)
    busy.value = false
  }
}
</script>

<template>
  <section class="gap-panel" aria-label="待补技能优先级">
    <h3>待补技能优先级</h3>
    <p v-if="!analysis.target_sample_count">当前条件下没有岗位样本，无法判断技能缺口。</p>
    <p v-else-if="!analysis.skill_sample_count">目标岗位没有技能标签，暂时无法判断缺口。</p>
    <p v-else-if="!analysis.conditions.skills?.length">填写已掌握的技能后，即可查看待补技能。</p>
    <template v-else>
      <p>按需求频次排序。共 {{ analysis.target_sample_count }} 条目标岗位，其中 {{ analysis.skill_sample_count }} 条有技能标签。</p>
      <p v-if="!analysis.missing_skills.length">已覆盖这组样本中记录的技能。</p>
      <details v-for="skill in analysis.missing_skills" :key="skill.name" class="gap-evidence">
        <summary><strong>{{ skill.name }}</strong><span>{{ skill.count }}/{{ analysis.skill_sample_count }} 条样本有此技能</span></summary>
        <ul v-if="skill.evidence?.length">
          <li v-for="job in skill.evidence" :key="job.job_id">
            <strong>{{ job.job_title }}</strong> · {{ job.city }} · {{ job.job_id }}
            <small>技能标签：{{ job.skill }} · 来源标记：{{ job.source || '未提供' }}<template v-if="job.publish_date"> · {{ job.publish_date }}</template></small>
          </li>
        </ul>
        <p v-if="skill.count > (skill.evidence?.length || 0)">此处仅展示部分样本。</p>
      </details>
      <button v-if="analysis.missing_skills.length" class="plan-button" type="button" :disabled="busy" @click="buildPlan">
        {{ busy ? '正在整理练习…' : '生成补技能练习清单' }}
      </button>
      <p v-if="error" class="plan-error" role="alert">{{ error }}</p>
      <section v-if="plan" class="practice" aria-label="补技能练习清单" aria-live="polite">
        <h4>{{ plan.plan_mode === 'ai' ? 'AI 练习建议' : '规则练习建议' }}</h4>
        <p v-if="plan.plan_mode !== 'ai'">本次未使用模型生成练习，以下为可执行的参考模板。</p>
        <ol>
          <li v-for="step in plan.steps" :key="step.name">
            <strong>{{ step.name }}</strong> · {{ step.count }}/{{ plan.skill_sample_count }} 条样本
            <p>{{ step.exercise }}</p>
            <p>验收产出：{{ step.deliverable }}</p>
          </li>
        </ol>
      </section>
    </template>
  </section>
</template>

<style scoped>
.gap-panel { min-width: 0; background: #fff; border: 1px solid #e1e9f4; border-radius: 14px; padding: 18px; }
.gap-panel h3 { margin: 0 0 6px; font-size: 17px; color: #17243e; }
.gap-panel p { margin: 0 0 10px; color: #51617c; font-size: 13px; line-height: 1.65; }
.gap-evidence { margin-top: 6px; padding: 7px 9px; border-radius: 7px; background: #f4f5ff; color: #243055; }
.gap-evidence summary { cursor: pointer; line-height: 1.55; overflow-wrap: anywhere; }
.gap-evidence summary span { margin-left: 8px; color: #545988; font-size: 12px; }
.gap-evidence ul, .practice ol { padding-left: 20px; margin: 8px 0; }
.gap-evidence li, .practice li { margin-bottom: 7px; font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }
.gap-evidence small { display: block; color: #51617c; }
.plan-button { margin-top: 12px; padding: 8px 12px; border: 0; border-radius: 8px; color: white; background: #4f46e5; cursor: pointer; }
.plan-button:disabled { opacity: 0.65; cursor: wait; }
.practice { margin-top: 12px; border-top: 1px solid #e1e9f4; }
.practice h4 { margin: 10px 0 6px; }
.practice li p { margin: 2px 0; }
.gap-panel .plan-error { margin-top: 6px; color: #9a3412; }
</style>
