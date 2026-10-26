<script setup>
import { computed, ref } from 'vue'

import {
  saveHistoryRecord
} from '../utils/history'


/* =========================
   可选技能
========================= */

const skillOptions = [
  'Java',
  'Python',
  'SQL',
  'Linux',
  'Git',
  'Spring',
  'Spring Boot',
  'Spring Cloud',
  'MySQL',
  'Redis',
  'Kafka',
  'Docker',
  'K8s',
  'Vue',
  'React',
  'JavaScript',
  'Go',
  '数据分析',
  '数据清洗',
  '机器学习'
]


const cityOptions = [
  '',
  '北京',
  '深圳',
  '上海',
  '广州',
  '杭州',
  '合肥'
]


/* =========================
   页面状态
========================= */

const selectedSkills = ref([])

const selectedCity = ref('')

const customSkill = ref('')

const loading = ref(false)

const result = ref(null)

const errorMessage = ref('')


/* =========================
   已选技能数量
========================= */

const selectedCount = computed(() => {
  return selectedSkills.value.length
})


/* =========================
   选择 / 取消技能
========================= */

const toggleSkill = (skill) => {
  if (
    selectedSkills.value.includes(skill)
  ) {
    selectedSkills.value =
      selectedSkills.value.filter(
        item => item !== skill
      )
  } else {
    selectedSkills.value.push(skill)
  }
}


/* =========================
   自定义技能
========================= */

const addCustomSkill = () => {
  const skill =
    customSkill.value.trim()

  if (!skill) {
    return
  }

  const exists =
    selectedSkills.value.some(
      item =>
        item.toLowerCase() ===
        skill.toLowerCase()
    )

  if (!exists) {
    selectedSkills.value.push(skill)
  }

  customSkill.value = ''
}


/* =========================
   清空
========================= */

const clearSkills = () => {
  selectedSkills.value = []
  result.value = null
  errorMessage.value = ''
}


/* =========================
   历史记录数据辅助
========================= */

const getSkillNames = (
  value
) => {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .map(item => {
      if (
        typeof item === 'string'
      ) {
        return item
      }

      if (
        item &&
        typeof item === 'object'
      ) {
        return (
          item.name ||
          item.skill ||
          item.title ||
          ''
        )
      }

      return ''
    })
    .filter(Boolean)
}


/* =========================
   获取推荐岗位
========================= */

const getRecommendedJobs = (
  data
) => {
  const possibleLists = [
    data?.recommendations,
    data?.matches,
    data?.top_jobs,
    data?.jobs
  ]

  const list =
    possibleLists.find(
      item =>
        Array.isArray(item)
    ) || []

  return list
}


/* =========================
   获取优势技能
========================= */

const getStrengthSkills = (
  data
) => {
  const possibleLists = [
    data?.strengths,
    data?.strong_skills,
    data?.matched_skills
  ]

  const list =
    possibleLists.find(
      item =>
        Array.isArray(item)
    ) || []

  return getSkillNames(list)
}


/* =========================
   获取建议补充技能
========================= */

const getGapSkills = (
  data
) => {
  const possibleLists = [
    data?.gaps,
    data?.gap_skills,
    data?.missing_skills,
    data?.recommended_skills,
    data?.suggestions,
    data?.weaknesses
  ]

  const list =
    possibleLists.find(
      item =>
        Array.isArray(item)
    ) || []

  return getSkillNames(list)
}


/* =========================
   保存技能测评历史
========================= */

const saveSkillHistory = (
  data
) => {
  try {
    const strengths =
      getStrengthSkills(data)

    const gaps =
      getGapSkills(data)

    const jobs =
      getRecommendedJobs(data)

    const jobNames =
      jobs
        .map(
          job =>
            job?.job_title ||
            job?.title ||
            ''
        )
        .filter(Boolean)
        .slice(0, 5)

    const score =
      data?.overall_score ??
      data?.score ??
      data?.match_score ??
      0

    const level =
      data?.level ||
      data?.grade ||
      '暂无评级'

    const city =
      data?.target_city ||
      selectedCity.value ||
      '未指定'

    saveHistoryRecord({
      type: 'skill',

      title:
        `${city === '未指定' ? '' : city + ' '}技能测评结果`,

      summary:
        data?.summary ||
        `本次综合技能匹配度为 ${score} 分，评级：${level}。`,

      meta: {
        城市:
          city,

        综合得分:
          `${score} 分`,

        评级:
          level,

        已选技能:
          `${selectedSkills.value.length} 项`
      },

      detail: {
        目标城市:
          city,

        已选技能:
          [...selectedSkills.value],

        综合匹配分:
          `${score} 分`,

        测评等级:
          level,

        优势技能:
          strengths,

        建议补充技能:
          gaps,

        推荐岗位:
          jobNames,

        推荐岗位数量:
          jobs.length,

        测评建议:
          data?.summary ||
          '暂无更多建议',

        是否扩展检索:
          data?.fallback
            ? '是'
            : '否',

        扩展检索说明:
          data?.fallback_message ||
          '无'
      }
    })

  } catch (error) {
    /*
      历史记录失败不能影响
      技能测评本身。
    */
    console.error(
      '保存技能测评历史记录失败：',
      error
    )
  }
}


/* =========================
   开始测评
========================= */

const startTest = async () => {
  if (
    selectedSkills.value.length === 0
  ) {
    errorMessage.value =
      '请至少选择一项你已经掌握的技能'

    return
  }

  loading.value = true

  errorMessage.value = ''

  result.value = null

  try {
    const response = await fetch(
      '/api/skill-match',
      {
        method: 'POST',

        headers: {
          'Content-Type':
            'application/json'
        },

        body: JSON.stringify({
          skills:
            selectedSkills.value,

          city:
            selectedCity.value ||
            null
        })
      }
    )

    if (!response.ok) {
      let detail = ''

      try {
        const errorData =
          await response.json()

        detail =
          errorData?.detail || ''

      } catch {
        // 无法解析错误响应时忽略
      }

      throw new Error(
        detail ||
        '技能测评请求失败'
      )
    }

    const data =
      await response.json()

    /*
      先正常显示测评结果
    */
    result.value = data

    /*
      测评成功后自动保存历史记录
    */
    saveSkillHistory(data)

  } catch (error) {
    console.error(error)

    errorMessage.value =
      error?.message ||
      '技能测评服务暂时不可用，请确认后端服务是否已经启动。'

  } finally {
    loading.value = false
  }
}


/* =========================
   薪资显示
========================= */

const formatSalary = (
  min,
  max
) => {
  if (
    min === null ||
    max === null ||
    min === undefined ||
    max === undefined
  ) {
    return '薪资面议'
  }

  const minNumber =
    Number(min)

  const maxNumber =
    Number(max)

  if (
    Number.isNaN(minNumber) ||
    Number.isNaN(maxNumber)
  ) {
    return '薪资面议'
  }

  const minK =
    minNumber >= 1000
      ? minNumber / 1000
      : minNumber

  const maxK =
    maxNumber >= 1000
      ? maxNumber / 1000
      : maxNumber

  return `${minK}-${maxK}K`
}
</script>


<template>
  <div class="skill-test-page">

    <!-- 页面标题 -->

    <header class="page-header">
      <div>
        <h1>
          技能测评
        </h1>

        <p>
          根据真实岗位技能要求，分析你的岗位匹配度与技能缺口
        </p>
      </div>

      <span class="data-badge">
        岗位数据驱动
      </span>
    </header>


    <!-- 测评输入 -->

    <section class="test-card">

      <div class="section-heading">
        <div>
          <h2>
            选择你已经掌握的技能
          </h2>

          <p>
            系统将根据岗位知识库计算你的岗位技能覆盖情况
          </p>
        </div>

        <span class="selected-count">
          已选 {{ selectedCount }} 项
        </span>
      </div>


      <!-- 技能选择 -->

      <div class="skill-selector">

        <button
          v-for="skill in skillOptions"
          :key="skill"
          class="skill-option"
          :class="{
            selected:
              selectedSkills.includes(
                skill
              )
          }"
          @click="toggleSkill(skill)"
        >
          {{ skill }}
        </button>

      </div>


      <!-- 自定义技能 -->

      <div class="custom-skill-row">

        <input
          v-model="customSkill"
          type="text"
          placeholder="没有找到你的技能？可以手动输入，例如：C++"
          @keydown.enter.prevent="
            addCustomSkill
          "
        />

        <button
          class="add-button"
          @click="addCustomSkill"
        >
          添加技能
        </button>

      </div>


      <!-- 已选技能 -->

      <div
        v-if="selectedSkills.length"
        class="selected-section"
      >

        <span class="selected-label">
          我的技能
        </span>

        <div class="selected-skills">

          <button
            v-for="
              skill in selectedSkills
            "
            :key="skill"
            class="selected-skill"
            @click="toggleSkill(skill)"
          >
            {{ skill }}

            <span>
              ×
            </span>
          </button>

        </div>

      </div>


      <!-- 城市 -->

      <div class="city-row">

        <div>
          <label>
            目标城市
          </label>

          <p>
            可选；不选择则分析全部城市岗位
          </p>
        </div>


        <select
          v-model="selectedCity"
        >
          <option value="">
            全部城市
          </option>

          <option
            v-for="
              city in
              cityOptions.filter(
                item => item
              )
            "
            :key="city"
            :value="city"
          >
            {{ city }}
          </option>
        </select>

      </div>


      <!-- 操作 -->

      <div class="actions">

        <button
          class="clear-button"
          @click="clearSkills"
        >
          清空
        </button>


        <button
          class="test-button"
          :disabled="loading"
          @click="startTest"
        >
          {{
            loading
              ? '正在分析...'
              : '开始技能测评'
          }}
        </button>

      </div>

    </section>


    <!-- 错误 -->

    <div
      v-if="errorMessage"
      class="error-message"
    >
      {{ errorMessage }}
    </div>


    <!-- 加载 -->

    <div
      v-if="loading"
      class="loading-card"
    >
      <div class="loading-dot">
      </div>

      <span>
        正在分析岗位技能要求与个人技能匹配情况...
      </span>
    </div>


    <!-- =====================
         测评结果
    ====================== -->

    <template
      v-if="
        result &&
        !loading
      "
    >

      <!-- 总体结果 -->

      <section class="result-summary">

        <div class="score-area">

          <div class="score-circle">

            <strong>
              {{ result.overall_score }}
            </strong>

            <span>
              分
            </span>

          </div>

        </div>


        <div class="summary-content">

          <span class="result-label">
            综合技能匹配度
          </span>

          <h2>
            {{ result.level }}
          </h2>

          <p>
            {{ result.summary }}
          </p>


          <div
            v-if="result.target_city"
            class="target-city"
          >
            目标城市：
            <strong>
              {{ result.target_city }}
            </strong>
          </div>

        </div>

      </section>


      <!-- 城市降级 -->

      <div
        v-if="
          result.fallback &&
          result.fallback_message
        "
        class="fallback-notice"
      >

        <div class="fallback-icon">
          i
        </div>

        <div>
          <strong>
            已扩展测评范围
          </strong>

          <p>
            {{
              result.fallback_message
            }}
          </p>
        </div>

      </div>


      <!-- 能力分析 -->

      <section class="analysis-grid">

        <!-- 优势技能 -->

        <div class="analysis-card">

          <div class="analysis-title">

            <div>
              <h3>
                已掌握优势技能
              </h3>

              <p>
                你已掌握且市场存在需求的技能
              </p>
            </div>

            <span class="good-badge">
              优势
            </span>

          </div>


          <div
            v-if="
              result.strengths &&
              result.strengths.length
            "
            class="tag-list"
          >

            <div
              v-for="
                skill in
                result.strengths
              "
              :key="skill.name"
              class="strength-tag"
            >
              <span>
                {{ skill.name }}
              </span>

              <small>
                {{ skill.count }}
                个岗位
              </small>
            </div>

          </div>


          <p
            v-else
            class="empty-text"
          >
            当前岗位样本中暂未统计到明显优势技能。
          </p>

        </div>


        <!-- 缺口 -->

        <div class="analysis-card">

          <div class="analysis-title">

            <div>
              <h3>
                建议补充技能
              </h3>

              <p>
                当前岗位市场中的高频技能缺口
              </p>
            </div>

            <span class="warning-badge">
              提升
            </span>

          </div>


          <div
            v-if="
              result.missing_skills &&
              result.missing_skills.length
            "
            class="tag-list"
          >

            <div
              v-for="
                skill in
                result.missing_skills
              "
              :key="skill.name"
              class="missing-tag"
            >

              <span>
                {{ skill.name }}
              </span>

              <small>
                {{ skill.count }}
                个岗位需求
              </small>

            </div>

          </div>


          <p
            v-else
            class="empty-text"
          >
            暂未发现明显技能缺口。
          </p>

        </div>

      </section>


      <!-- 推荐岗位 -->

      <section class="recommend-section">

        <div class="recommend-header">

          <div>
            <h2>
              岗位匹配推荐
            </h2>

            <p>
              按技能覆盖率排序，为你展示当前最适合的岗位
            </p>
          </div>


          <span>
            Top
            {{
              result.recommended_jobs
                ?.length || 0
            }}
          </span>

        </div>


        <div
          v-if="
            result.recommended_jobs &&
            result.recommended_jobs.length
          "
          class="job-list"
        >

          <article
            v-for="
              job in
              result.recommended_jobs
            "
            :key="job.job_id"
            class="job-card"
          >

            <div class="job-top">

              <div>

                <h3>
                  {{ job.job_title }}
                </h3>

                <p>
                  {{
                    job.company_name
                  }}
                </p>

              </div>


              <div class="job-right">

                <strong class="salary">
                  {{
                    formatSalary(
                      job.salary_min,
                      job.salary_max
                    )
                  }}
                </strong>

                <span class="match-score">
                  {{
                    job.match_score
                  }}% 匹配
                </span>

              </div>

            </div>


            <div class="job-meta">

              <span>
                📍 {{ job.city }}
              </span>

              <span>
                🎓
                {{
                  job.education ||
                  '学历不限'
                }}
              </span>

              <span>
                💼
                {{
                  job.experience ||
                  '经验不限'
                }}
              </span>

            </div>


            <!-- 已掌握 -->

            <div
              v-if="
                job.matched_skills &&
                job.matched_skills.length
              "
              class="job-skill-group"
            >

              <span class="skill-group-title">
                已掌握
              </span>

              <div class="job-tags">

                <span
                  v-for="
                    skill in
                    job.matched_skills
                  "
                  :key="skill"
                  class="matched"
                >
                  {{ skill }}
                </span>

              </div>

            </div>


            <!-- 需要补充 -->

            <div
              v-if="
                job.missing_skills &&
                job.missing_skills.length
              "
              class="job-skill-group"
            >

              <span class="skill-group-title">
                待补充
              </span>

              <div class="job-tags">

                <span
                  v-for="
                    skill in
                    job.missing_skills
                  "
                  :key="skill"
                  class="missing"
                >
                  {{ skill }}
                </span>

              </div>

            </div>

          </article>

        </div>


        <div
          v-else
          class="empty-jobs"
        >
          当前技能暂未匹配到合适岗位，可以尝试增加技能或取消城市限制。
        </div>

      </section>

    </template>

  </div>
</template>


<style scoped>

.skill-test-page {
  width: 100%;
}


/* 页面标题 */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 26px;
}


.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  color: var(--text);
}


.page-header p {
  margin: 0;
  color: var(--text-2);
  font-size: 14px;
}


.data-badge {
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 13px;
}


/* 输入卡片 */

.test-card {
  padding: 26px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 16px;
}


.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}


.section-heading h2 {
  margin: 0 0 6px;
  font-size: 19px;
}


.section-heading p {
  margin: 0;
  color: var(--text-3);
  font-size: 13px;
}


.selected-count {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--text-2);
  font-size: 12px;
}


/* 技能选择 */

.skill-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}


.skill-option {
  padding: 10px 15px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: #ffffff;
  color: var(--text-2);
  cursor: pointer;
  transition: all 0.2s;
}


.skill-option:hover {
  border-color: #93c5fd;
  color: var(--primary);
}


.skill-option.selected {
  background: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}


/* 自定义技能 */

.custom-skill-row {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}


.custom-skill-row input {
  flex: 1;
  height: 42px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: 9px;
  outline: none;
  font-family: inherit;
}


.custom-skill-row input:focus {
  border-color: var(--brand-2);
}


.add-button {
  padding: 0 18px;
  border: 1px solid #bfdbfe;
  border-radius: 9px;
  background: var(--primary-soft);
  color: var(--primary);
  cursor: pointer;
}


/* 已选择 */

.selected-section {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-top: 20px;
  padding: 16px;
  background: var(--surface-2);
  border-radius: 10px;
}


.selected-label {
  flex-shrink: 0;
  padding-top: 6px;
  color: var(--text-2);
  font-size: 13px;
}


.selected-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}


.selected-skill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  border: none;
  border-radius: 7px;
  background: var(--primary-soft);
  color: #4338ca;
  cursor: pointer;
}


/* 城市 */

.city-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}


.city-row label {
  color: var(--text);
  font-weight: 600;
}


.city-row p {
  margin: 5px 0 0;
  color: var(--text-3);
  font-size: 12px;
}


.city-row select {
  min-width: 170px;
  height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: #ffffff;
  outline: none;
}


/* 按钮 */

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 22px;
}


.clear-button,
.test-button {
  height: 44px;
  padding: 0 22px;
  border-radius: 9px;
  cursor: pointer;
}


.clear-button {
  background: #ffffff;
  border: 1px solid var(--border);
  color: var(--text-2);
}


.test-button {
  border: none;
  background: var(--primary);
  color: #ffffff;
}


.test-button:hover {
  background: #4338ca;
}


.test-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}


/* 综合结果 */

.result-summary {
  display: flex;
  align-items: center;
  gap: 28px;
  margin-top: 20px;
  padding: 26px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 16px;
}


.score-circle {
  width: 112px;
  height: 112px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 10px solid var(--primary-soft);
  border-radius: 50%;
  background: #f8fbff;
}


.score-circle strong {
  font-size: 32px;
  color: var(--primary);
}


.score-circle span {
  color: var(--text-2);
  font-size: 12px;
}


.summary-content {
  flex: 1;
}


.result-label {
  color: var(--text-2);
  font-size: 13px;
}


.summary-content h2 {
  margin: 7px 0;
  color: var(--text);
  font-size: 24px;
}


.summary-content p {
  margin: 0;
  color: var(--text-2);
  line-height: 1.7;
}


.target-city {
  margin-top: 13px;
  color: var(--text-2);
  font-size: 13px;
}


/* 技能分析 */

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
  margin-top: 20px;
}


.analysis-card {
  padding: 22px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 14px;
}


.analysis-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}


.analysis-title h3 {
  margin: 0 0 5px;
  font-size: 17px;
}


.analysis-title p {
  margin: 0;
  color: var(--text-3);
  font-size: 12px;
}


.good-badge,
.warning-badge {
  height: fit-content;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
}


.good-badge {
  background: #ecfdf5;
  color: #059669;
}


.warning-badge {
  background: #fff7ed;
  color: #ea580c;
}


.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 18px;
}


.strength-tag,
.missing-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
}


.strength-tag {
  background: #ecfdf5;
  color: #047857;
}


.missing-tag {
  background: #fff7ed;
  color: #c2410c;
}


.strength-tag small,
.missing-tag small {
  opacity: 0.75;
}


.empty-text {
  color: var(--text-3);
  font-size: 13px;
}


/* 推荐岗位 */

.recommend-section {
  margin-top: 22px;
}


.recommend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}


.recommend-header h2 {
  margin: 0 0 5px;
  font-size: 20px;
}


.recommend-header p {
  margin: 0;
  color: var(--text-3);
  font-size: 13px;
}


.recommend-header > span {
  color: var(--text-2);
  font-size: 13px;
}


.job-list {
  display: grid;
  gap: 14px;
}


.job-card {
  padding: 20px 22px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 14px;
}


.job-top {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}


.job-top h3 {
  margin: 0 0 5px;
  font-size: 17px;
}


.job-top p {
  margin: 0;
  color: var(--text-2);
  font-size: 13px;
}


.job-right {
  text-align: right;
}


.salary {
  display: block;
  color: var(--primary);
  font-size: 18px;
}


.match-score {
  display: inline-block;
  margin-top: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 12px;
}


.job-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 14px;
  color: var(--text-2);
  font-size: 13px;
}


.job-skill-group {
  display: flex;
  gap: 12px;
  margin-top: 14px;
}


.skill-group-title {
  width: 52px;
  flex-shrink: 0;
  padding-top: 5px;
  color: var(--text-2);
  font-size: 12px;
}


.job-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}


.job-tags span {
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
}


.job-tags .matched {
  background: #ecfdf5;
  color: #047857;
}


.job-tags .missing {
  background: var(--surface-2);
  color: var(--text-2);
}


/* fallback */

.fallback-notice {
  display: flex;
  gap: 12px;
  margin-top: 18px;
  padding: 14px 16px;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  background: #fff7ed;
}


.fallback-icon {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 50%;
  background: #f97316;
  color: white;
  font-weight: 700;
}


.fallback-notice strong {
  color: #9a3412;
}


.fallback-notice p {
  margin: 5px 0 0;
  color: #7c2d12;
  font-size: 13px;
}


/* 状态 */

.error-message,
.loading-card,
.empty-jobs {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 12px;
}


.error-message {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}


.loading-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  color: var(--text-2);
}


.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand-2);
  animation: pulse 1s infinite;
}


.empty-jobs {
  background: #ffffff;
  border: 1px solid var(--border);
  color: var(--text-2);
}


@keyframes pulse {
  0% {
    opacity: 0.3;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.3;
  }
}


/* 响应式 */

@media (max-width: 900px) {

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .custom-skill-row {
    flex-direction: column;
  }

  .city-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .city-row select {
    width: 100%;
  }

}
</style>
