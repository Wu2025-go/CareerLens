<script setup>
import { ref } from 'vue'


/* =========================
   页面状态
========================= */

const question = ref('')

const loading = ref(false)

const result = ref(null)

const errorMessage = ref('')


/* =========================
   推荐问题
========================= */

const examples = [
  '广州 Python 数据分析岗位需要哪些技能？',
  '深圳 Java 后端开发岗位需要哪些技能？',
  '北京 Python 岗位有哪些？',
  '数据分析岗位常见技能有哪些？'
]


const fillQuestion = (text) => {
  question.value = text
}


/* =========================
   技能字符串拆分
========================= */

const parseSkills = (value) => {
  return String(value || '')
    .split(/[|,，、;/；]+/)
    .map(skill => skill.trim())
    .filter(Boolean)
}


/* =========================
   提问
========================= */

const askQuestion = async () => {
  const text = question.value.trim()

  if (!text) {
    errorMessage.value =
      '请输入你想了解的问题'

    return
  }


  loading.value = true

  errorMessage.value = ''

  result.value = null


  try {
    const response = await fetch(
      'http://127.0.0.1:8000/api/ask',
      {
        method: 'POST',

        headers: {
          'Content-Type':
            'application/json'
        },

        body: JSON.stringify({
          question: text
        })
      }
    )


    if (!response.ok) {
      throw new Error(
        'AI 问答请求失败'
      )
    }


    result.value =
      await response.json()

  } catch (error) {
    console.error(error)

    errorMessage.value =
      'AI 问答服务暂时不可用，请确认后端服务是否已经启动。'

  } finally {
    loading.value = false
  }
}


/* =========================
   薪资格式化
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


  const minNumber = Number(min)

  const maxNumber = Number(max)


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
  <div class="ask-page">

    <!-- =====================
         页面标题
    ====================== -->

    <header class="page-header">

      <div>
        <h1>
          AI 就业问答
        </h1>

        <p>
          基于真实招聘岗位数据，为你检索岗位、技能和就业信息
        </p>
      </div>


      <span class="knowledge-badge">
        岗位知识库
      </span>

    </header>


    <!-- =====================
         问答输入区域
    ====================== -->

    <section class="ask-card">

      <div class="ask-title">

        <span class="ai-icon">
          AI
        </span>


        <div>
          <h2>
            CareerLens 职业助手
          </h2>

          <p>
            你可以询问岗位技能、城市就业机会、技术方向等问题
          </p>
        </div>

      </div>


      <div class="input-area">

        <textarea
          v-model="question"
          placeholder="例如：深圳 Java 后端开发岗位需要哪些技能？"
          @keydown.ctrl.enter.prevent="askQuestion"
        >
        </textarea>


        <button
          class="send-button"
          :disabled="loading"
          @click="askQuestion"
        >
          {{
            loading
              ? '检索中...'
              : '发送问题'
          }}
        </button>

      </div>


      <div class="shortcut-tip">
        Ctrl + Enter 快速发送
      </div>


      <!-- 推荐问题 -->

      <div class="examples">

        <span class="examples-title">
          试试这些问题：
        </span>


        <button
          v-for="item in examples"
          :key="item"
          class="example-button"
          @click="fillQuestion(item)"
        >
          {{ item }}
        </button>

      </div>

    </section>


    <!-- =====================
         错误提示
    ====================== -->

    <div
      v-if="errorMessage"
      class="error-message"
    >
      {{ errorMessage }}
    </div>


    <!-- =====================
         加载状态
    ====================== -->

    <section
      v-if="loading"
      class="loading-card"
    >

      <div class="loading-dot">
      </div>


      <span>
        正在从岗位知识库中检索相关信息...
      </span>

    </section>


    <!-- =====================
         回答区域
    ====================== -->

    <template
      v-if="
        result &&
        !loading
      "
    >

      <section class="answer-card">

        <!-- 回答标题 -->

        <div class="answer-header">

          <span class="ai-icon">
            AI
          </span>


          <div>
            <strong>
              CareerLens 回答
            </strong>

            <p class="answer-source">
              基于当前岗位知识库检索结果
            </p>
          </div>

        </div>


        <!-- 回答正文 -->

        <p class="answer-text">
          {{ result.answer }}
        </p>


        <!-- =====================
             智能降级提示
        ====================== -->

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


          <div class="fallback-content">

            <strong>
              已扩展检索范围
            </strong>

            <p>
              {{
                result.fallback_message
              }}
            </p>

          </div>

        </div>


        <!-- =====================
             已识别城市
        ====================== -->

        <div
          v-if="result.target_city"
          class="condition-row"
        >

          <span class="condition-label">
            已识别城市
          </span>


          <span class="condition-value">
            {{ result.target_city }}
          </span>

        </div>


        <!-- =====================
             高频技能
        ====================== -->

        <div
          v-if="
            result.top_skills &&
            result.top_skills.length
          "
          class="skill-section"
        >

          <h3>
            相关岗位高频技能
          </h3>


          <div class="skill-list">

            <div
              v-for="
                skill in
                result.top_skills
              "
              :key="skill.name"
              class="skill-tag"
            >

              <span>
                {{ skill.name }}
              </span>


              <small>
                {{ skill.count }} 次
              </small>

            </div>

          </div>

        </div>

      </section>


      <!-- =====================
           命中岗位
      ====================== -->

      <section
        v-if="
          result.matches &&
          result.matches.length
        "
        class="matches-section"
      >

        <div class="section-title">

          <div>

            <h2>
              {{
                result.fallback
                  ? '扩展推荐岗位'
                  : '相关岗位'
              }}
            </h2>


            <p>
              {{
                result.fallback
                  ? '当前城市暂无严格匹配岗位，以下为其他城市的真实相近岗位'
                  : '根据岗位名称、城市、技能和职位描述综合匹配'
              }}
            </p>

          </div>


          <span>
            Top
            {{ result.matches.length }}
          </span>

        </div>


        <div class="job-list">

          <article
            v-for="
              job in
              result.matches
            "
            :key="job.job_id"
            class="job-card"
          >

            <!-- 岗位标题 -->

            <div class="job-top">

              <div>

                <h3>
                  {{ job.job_title }}
                </h3>


                <p class="company">
                  {{
                    job.company_name
                  }}
                </p>

              </div>


              <div class="salary">
                {{
                  formatSalary(
                    job.salary_min,
                    job.salary_max
                  )
                }}
              </div>

            </div>


            <!-- 岗位信息 -->

            <div class="job-info">

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


              <span class="score-tag">
                匹配度
                {{ job.score }}
              </span>

            </div>


            <!-- 技能标签 -->

            <div
              v-if="
                parseSkills(
                  job.skills
                ).length
              "
              class="job-skills"
            >

              <span
                v-for="
                  skill in
                  parseSkills(
                    job.skills
                  )
                "
                :key="skill"
              >
                {{ skill }}
              </span>

            </div>

          </article>

        </div>

      </section>


      <!-- =====================
           无任何结果
      ====================== -->

      <section
        v-else
        class="empty-card"
      >

        <div class="empty-icon">
          ?
        </div>


        <div>

          <h3>
            暂无匹配岗位
          </h3>

          <p>
            当前岗位知识库暂时没有足够的数据回答这个问题，你可以尝试更换城市、岗位方向或技能关键词。
          </p>

        </div>

      </section>

    </template>

  </div>
</template>


<style scoped>

/* =========================
   页面
========================= */

.ask-page {
  width: 100%;
}


/* =========================
   页面标题
========================= */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 26px;
}


.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #111827;
}


.page-header p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}


.knowledge-badge {
  padding: 8px 14px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
}


/* =========================
   输入卡片
========================= */

.ask-card {
  padding: 26px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
}


.ask-title {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 22px;
}


.ai-icon {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 12px;
  background: #2563eb;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
}


.ask-title h2 {
  margin: 0 0 5px;
  font-size: 19px;
}


.ask-title p {
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
}


/* =========================
   输入框
========================= */

.input-area {
  display: flex;
  gap: 14px;
  align-items: flex-end;
}


textarea {
  flex: 1;
  min-height: 112px;
  resize: vertical;
  padding: 16px 18px;
  border: 1px solid #dbe1ea;
  border-radius: 12px;
  outline: none;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.7;
  color: #1f2937;
  background: #fafbfc;
}


textarea:focus {
  border-color: #3b82f6;
  background: #ffffff;
}


.send-button {
  height: 46px;
  padding: 0 24px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
}


.send-button:hover {
  background: #1d4ed8;
}


.send-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}


.shortcut-tip {
  margin-top: 8px;
  color: #9ca3af;
  font-size: 12px;
}


/* =========================
   推荐问题
========================= */

.examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  margin-top: 22px;
}


.examples-title {
  margin-right: 4px;
  color: #6b7280;
  font-size: 13px;
}


.example-button {
  padding: 8px 12px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
  color: #2563eb;
  cursor: pointer;
  font-size: 13px;
}


.example-button:hover {
  background: #eff6ff;
}


/* =========================
   回答卡片
========================= */

.answer-card {
  margin-top: 20px;
  padding: 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
}


.answer-header {
  display: flex;
  align-items: center;
  gap: 12px;
}


.answer-header strong {
  color: #111827;
}


.answer-source {
  margin: 4px 0 0;
  color: #9ca3af;
  font-size: 12px;
}


.answer-text {
  margin: 20px 0;
  padding: 16px 18px;
  border-radius: 12px;
  background: #f8fafc;
  color: #374151;
  line-height: 1.8;
}


/* =========================
   智能降级提示
========================= */

.fallback-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin: 16px 0 20px;
  padding: 14px 16px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
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
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
}


.fallback-content strong {
  color: #9a3412;
  font-size: 14px;
}


.fallback-content p {
  margin: 5px 0 0;
  color: #7c2d12;
  font-size: 13px;
  line-height: 1.6;
}


/* =========================
   识别条件
========================= */

.condition-row {
  display: flex;
  align-items: center;
  gap: 12px;
}


.condition-label {
  color: #6b7280;
  font-size: 13px;
}


.condition-value {
  padding: 5px 10px;
  border-radius: 6px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
}


/* =========================
   高频技能
========================= */

.skill-section {
  margin-top: 22px;
}


.skill-section h3 {
  margin: 0 0 14px;
  font-size: 16px;
}


.skill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}


.skill-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
}


.skill-tag small {
  color: #6b7280;
}


/* =========================
   岗位列表
========================= */

.matches-section {
  margin-top: 22px;
}


.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}


.section-title h2 {
  margin: 0 0 4px;
  font-size: 20px;
}


.section-title p {
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
}


.section-title > span {
  color: #6b7280;
  font-size: 13px;
}


.job-list {
  display: grid;
  gap: 14px;
}


.job-card {
  padding: 20px 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  transition: all 0.2s ease;
}


.job-card:hover {
  transform: translateY(-2px);
  border-color: #bfdbfe;
  box-shadow:
    0 8px 24px
    rgba(15, 23, 42, 0.06);
}


.job-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}


.job-top h3 {
  margin: 0 0 5px;
  font-size: 17px;
}


.company {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}


.salary {
  color: #2563eb;
  font-size: 18px;
  font-weight: 600;
}


.job-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 15px;
  color: #6b7280;
  font-size: 13px;
}


.score-tag {
  color: #2563eb;
}


.job-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 15px;
}


.job-skills span {
  padding: 5px 9px;
  background: #f3f4f6;
  border-radius: 6px;
  color: #4b5563;
  font-size: 12px;
}


/* =========================
   无结果状态
========================= */

.empty-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-top: 20px;
  padding: 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.empty-icon {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 10px;
  background: #f3f4f6;
  color: #6b7280;
  font-weight: 700;
}


.empty-card h3 {
  margin: 0 0 6px;
  font-size: 16px;
}


.empty-card p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}


/* =========================
   加载与错误
========================= */

.loading-card,
.error-message {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 12px;
}


.loading-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  color: #6b7280;
}


.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #3b82f6;
  animation: pulse 1s infinite;
}


.error-message {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}


@keyframes pulse {

  0% {
    opacity: 0.35;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.35;
  }

}


/* =========================
   响应式
========================= */

@media (max-width: 900px) {

  .input-area {
    flex-direction: column;
    align-items: stretch;
  }


  .send-button {
    width: 100%;
  }


  .page-header {
    gap: 14px;
  }


  .job-top {
    gap: 16px;
  }

}
</style>