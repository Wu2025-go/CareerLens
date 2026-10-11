<script setup>
import { ref } from 'vue'

const city = ref('')
const keyword = ref('')
const education = ref('')
const minSalary = ref(null)

const selectedSkills = ref([])
const customSkill = ref('')

const loading = ref(false)
const errorMessage = ref('')
const result = ref(null)

const cities = [
  '深圳',
  '广州',
  '北京',
  '上海',
  '杭州',
  '合肥'
]

const jobDirections = [
  'Java',
  'Python',
  '数据分析',
  '前端',
  '后端',
  '算法',
  '测试',
  '运维'
]

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
  'TypeScript',
  'Go',
  '数据分析',
  '机器学习'
]

const toggleSkill = (skill) => {
  if (selectedSkills.value.includes(skill)) {
    selectedSkills.value =
      selectedSkills.value.filter(
        item => item !== skill
      )
  } else {
    selectedSkills.value.push(skill)
  }
}

const addCustomSkill = () => {
  const value = customSkill.value.trim()

  if (!value) {
    return
  }

  const exists =
    selectedSkills.value.some(
      item =>
        item.toLowerCase() ===
        value.toLowerCase()
    )

  if (!exists) {
    selectedSkills.value.push(value)
  }

  customSkill.value = ''
}

const clearForm = () => {
  city.value = ''
  keyword.value = ''
  education.value = ''
  minSalary.value = null
  selectedSkills.value = []
  result.value = null
  errorMessage.value = ''
}

const recommendJobs = async () => {
  loading.value = true
  errorMessage.value = ''
  result.value = null

  try {
    const response = await fetch(
      'http://127.0.0.1:8000/api/recommend',
      {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json'
        },

        body: JSON.stringify({
          city:
            city.value || null,

          keyword:
            keyword.value || null,

          skills:
            selectedSkills.value,

          min_salary:
            minSalary.value === null ||
            minSalary.value === ''
              ? null
              : Number(minSalary.value),

          education:
            education.value || null
        })
      }
    )

    if (!response.ok) {
      const data =
        await response.json()

      throw new Error(
        data.detail ||
        '岗位推荐请求失败'
      )
    }

    result.value =
      await response.json()

  } catch (error) {
    console.error(error)

    errorMessage.value =
      error.message ||
      '岗位推荐服务暂时不可用，请确认后端已经启动。'

  } finally {
    loading.value = false
  }
}

const formatSalary = (min, max) => {
  if (
    min === null ||
    max === null ||
    min === undefined ||
    max === undefined
  ) {
    return '薪资面议'
  }

  return `${min}-${max}K`
}
</script>


<template>
  <div class="recommend-page">

    <!-- 标题 -->
    <header class="page-header">
      <div>
        <h1>岗位推荐</h1>

        <p>
          根据目标城市、岗位方向、技能与薪资要求，为你匹配更合适的岗位
        </p>
      </div>

      <span class="page-badge">
        智能岗位匹配
      </span>
    </header>


    <!-- 条件区域 -->
    <section class="filter-card">

      <div class="filter-title">
        <div>
          <h2>设置求职条件</h2>
          <p>
            条件越完整，岗位推荐结果越准确
          </p>
        </div>
      </div>


      <!-- 第一行 -->
      <div class="filter-grid">

        <div class="field">
          <label>目标城市</label>

          <select v-model="city">
            <option value="">
              全部城市
            </option>

            <option
              v-for="item in cities"
              :key="item"
              :value="item"
            >
              {{ item }}
            </option>
          </select>
        </div>


        <div class="field">
          <label>岗位方向</label>

          <select v-model="keyword">
            <option value="">
              不限岗位方向
            </option>

            <option
              v-for="item in jobDirections"
              :key="item"
              :value="item"
            >
              {{ item }}
            </option>
          </select>
        </div>


        <div class="field">
          <label>最低期望薪资</label>

          <div class="salary-input">
            <input
              v-model="minSalary"
              type="number"
              min="0"
              placeholder="例如 10"
            />

            <span>K</span>
          </div>
        </div>


        <div class="field">
          <label>学历</label>

          <select v-model="education">
            <option value="">
              不限学历
            </option>

            <option value="大专">
              大专
            </option>

            <option value="本科">
              本科
            </option>

            <option value="硕士">
              硕士
            </option>
          </select>
        </div>

      </div>


      <!-- 技能 -->
      <div class="skills-area">

        <div class="skills-heading">
          <div>
            <h3>我的技能</h3>
            <p>
              选择你已经掌握的技术技能
            </p>
          </div>

          <span>
            已选 {{ selectedSkills.length }} 项
          </span>
        </div>


        <div class="skill-options">

          <button
            v-for="skill in skillOptions"
            :key="skill"
            class="skill-option"
            :class="{
              selected:
                selectedSkills.includes(skill)
            }"
            @click="toggleSkill(skill)"
          >
            {{ skill }}
          </button>

        </div>


        <div class="custom-row">

          <input
            v-model="customSkill"
            placeholder="其他技能，例如 C++"
            @keydown.enter.prevent="
              addCustomSkill
            "
          />

          <button
            @click="addCustomSkill"
          >
            添加
          </button>

        </div>


        <div
          v-if="selectedSkills.length"
          class="selected-skills"
        >

          <span
            v-for="skill in selectedSkills"
            :key="skill"
            @click="toggleSkill(skill)"
          >
            {{ skill }} ×
          </span>

        </div>

      </div>


      <!-- 按钮 -->
      <div class="actions">

        <button
          class="clear-button"
          @click="clearForm"
        >
          重置条件
        </button>

        <button
          class="recommend-button"
          :disabled="loading"
          @click="recommendJobs"
        >
          {{
            loading
              ? '正在匹配...'
              : '开始智能推荐'
          }}
        </button>

      </div>

    </section>


    <!-- 错误 -->
    <div
      v-if="errorMessage"
      class="error-box"
    >
      {{ errorMessage }}
    </div>


    <!-- 加载 -->
    <div
      v-if="loading"
      class="loading-box"
    >
      正在分析岗位数据并计算匹配度...
    </div>


    <!-- 推荐结果 -->
    <template
      v-if="result && !loading"
    >

      <div
        v-if="
          result.fallback &&
          result.fallback_message
        "
        class="fallback-box"
      >
        <strong>
          已扩展推荐范围
        </strong>

        <p>
          {{ result.fallback_message }}
        </p>
      </div>


      <section class="result-section">

        <div class="result-header">

          <div>
            <h2>智能推荐岗位</h2>

            <p>
              {{ result.message }}
            </p>
          </div>

          <span class="total-badge">
            {{
              result.recommendations
                ?.length || 0
            }}
            个结果
          </span>

        </div>


        <div
          v-if="
            result.recommendations &&
            result.recommendations.length
          "
          class="job-list"
        >

          <article
            v-for="
              job in result.recommendations
            "
            :key="job.job_id"
            class="job-card"
          >

            <!-- 顶部 -->
            <div class="job-top">

              <div>
                <h3>
                  {{ job.job_title }}
                </h3>

                <p>
                  {{ job.company_name }}
                </p>
              </div>


              <div class="salary-area">

                <strong>
                  {{
                    formatSalary(
                      job.salary_min,
                      job.salary_max
                    )
                  }}
                </strong>

                <span>
                  {{ job.match_score }}%
                  推荐
                </span>

              </div>

            </div>


            <!-- 基本信息 -->
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


            <!-- 推荐理由 -->
            <div
              v-if="
                job.reasons &&
                job.reasons.length
              "
              class="reason-area"
            >

              <span class="row-title">
                推荐理由
              </span>

              <div class="reason-list">

                <span
                  v-for="
                    reason in job.reasons
                  "
                  :key="reason"
                >
                  ✓ {{ reason }}
                </span>

              </div>

            </div>


            <!-- 已掌握 -->
            <div
              v-if="
                job.matched_skills &&
                job.matched_skills.length
              "
              class="skill-row"
            >

              <span class="row-title">
                已掌握
              </span>

              <div class="tag-list">

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


            <!-- 待补充 -->
            <div
              v-if="
                job.missing_skills &&
                job.missing_skills.length
              "
              class="skill-row"
            >

              <span class="row-title">
                待补充
              </span>

              <div class="tag-list">

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
          class="empty-result"
        >
          当前条件暂未匹配到岗位，可以尝试降低薪资要求或取消部分筛选条件。
        </div>

      </section>

    </template>

  </div>
</template>


<style scoped>

.recommend-page {
  width: 100%;
}


/* 页面标题 */

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 26px;
}


.page-header h1 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 28px;
}


.page-header p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}


.page-badge {
  padding: 8px 14px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
}


/* 筛选 */

.filter-card {
  padding: 26px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
}


.filter-title h2 {
  margin: 0 0 6px;
  font-size: 19px;
}


.filter-title p {
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
}


.filter-grid {
  display: grid;
  grid-template-columns:
    repeat(4, 1fr);
  gap: 16px;
  margin-top: 24px;
}


.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}


.field label {
  color: #374151;
  font-size: 13px;
  font-weight: 600;
}


.field select,
.field input {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border: 1px solid #dbe1ea;
  border-radius: 9px;
  background: #ffffff;
  outline: none;
  font-family: inherit;
}


.field select:focus,
.field input:focus {
  border-color: #3b82f6;
}


.salary-input {
  position: relative;
}


.salary-input input {
  padding-right: 36px;
}


.salary-input span {
  position: absolute;
  right: 12px;
  top: 11px;
  color: #9ca3af;
}


/* 技能 */

.skills-area {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid #eef2f7;
}


.skills-heading {
  display: flex;
  justify-content: space-between;
}


.skills-heading h3 {
  margin: 0 0 5px;
  font-size: 16px;
}


.skills-heading p {
  margin: 0;
  color: #9ca3af;
  font-size: 12px;
}


.skills-heading > span {
  color: #6b7280;
  font-size: 12px;
}


.skill-options {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 16px;
}


.skill-option {
  padding: 9px 13px;
  border: 1px solid #dbe1ea;
  border-radius: 8px;
  background: white;
  color: #4b5563;
  cursor: pointer;
}


.skill-option:hover {
  color: #2563eb;
  border-color: #93c5fd;
}


.skill-option.selected {
  background: #2563eb;
  border-color: #2563eb;
  color: white;
}


.custom-row {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}


.custom-row input {
  flex: 1;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #dbe1ea;
  border-radius: 8px;
  outline: none;
}


.custom-row button {
  padding: 0 18px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
  cursor: pointer;
}


.selected-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}


.selected-skills span {
  padding: 6px 9px;
  border-radius: 7px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 12px;
  cursor: pointer;
}


/* 操作按钮 */

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}


.clear-button,
.recommend-button {
  height: 44px;
  padding: 0 22px;
  border-radius: 9px;
  cursor: pointer;
}


.clear-button {
  border: 1px solid #dbe1ea;
  background: white;
  color: #6b7280;
}


.recommend-button {
  border: none;
  background: #2563eb;
  color: white;
}


.recommend-button:hover {
  background: #1d4ed8;
}


.recommend-button:disabled {
  opacity: 0.6;
}


/* 状态 */

.error-box,
.loading-box,
.fallback-box {
  margin-top: 18px;
  padding: 15px 17px;
  border-radius: 11px;
}


.error-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}


.loading-box {
  background: white;
  border: 1px solid #e5e7eb;
  color: #6b7280;
}


.fallback-box {
  background: #fff7ed;
  border: 1px solid #fed7aa;
}


.fallback-box strong {
  color: #c2410c;
}


.fallback-box p {
  margin: 5px 0 0;
  color: #9a3412;
  font-size: 13px;
}


/* 结果 */

.result-section {
  margin-top: 24px;
}


.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}


.result-header h2 {
  margin: 0 0 5px;
  font-size: 21px;
}


.result-header p {
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
}


.total-badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
}


.job-list {
  display: grid;
  gap: 14px;
}


.job-card {
  padding: 21px 23px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.job-top {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}


.job-top h3 {
  margin: 0 0 6px;
  font-size: 18px;
}


.job-top p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}


.salary-area {
  text-align: right;
}


.salary-area strong {
  display: block;
  color: #2563eb;
  font-size: 19px;
}


.salary-area span {
  display: inline-block;
  margin-top: 7px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
}


.job-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 17px;
  margin-top: 15px;
  color: #6b7280;
  font-size: 13px;
}


.reason-area,
.skill-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-top: 15px;
}


.row-title {
  width: 58px;
  flex-shrink: 0;
  padding-top: 5px;
  color: #6b7280;
  font-size: 12px;
}


.reason-list,
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}


.reason-list span {
  padding: 5px 8px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #047857;
  font-size: 12px;
}


.tag-list span {
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
}


.tag-list .matched {
  background: #dbeafe;
  color: #1d4ed8;
}


.tag-list .missing {
  background: #f3f4f6;
  color: #6b7280;
}


.empty-result {
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: white;
  color: #6b7280;
  text-align: center;
}


/* 响应式 */

@media (max-width: 1000px) {

  .filter-grid {
    grid-template-columns:
      repeat(2, 1fr);
  }

}


@media (max-width: 700px) {

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .custom-row {
    flex-direction: column;
  }

  .job-top {
    flex-direction: column;
  }

  .salary-area {
    text-align: left;
  }

}
</style>