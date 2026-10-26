<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { saveHistoryRecord } from '../utils/history'


/* =========================
   页面状态
========================= */

const question = ref('')

const loading = ref(false)

const result = ref(null)

const errorMessage = ref('')
let activeController = null
onBeforeUnmount(() => activeController?.abort())

const isModelAnswer = (data) => data?.answer_mode === 'rag' && data?.reference_integrity_checked === true
const answerModeLabel = (data) => isModelAnswer(data)
  ? '岗位检索 + 大模型生成'
  : '岗位检索与规则统计'


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
   历史记录辅助
========================= */

const getTopSkillNames = (data) => {
  if (
    !data?.top_skills ||
    !Array.isArray(data.top_skills)
  ) {
    return []
  }

  return data.top_skills
    .map(item => item?.name)
    .filter(Boolean)
}


const saveAskHistory = (
  text,
  data
) => {
  try {
    const skillNames =
      getTopSkillNames(data)

    const matchCount =
      Number.isFinite(data?.matched_count)
        ? data.matched_count
        : (Array.isArray(data?.matches) ? data.matches.length : 0)

    saveHistoryRecord({
      type: 'ask',

      title:
        text.length > 36
          ? `${text.slice(0, 36)}...`
          : text,

      summary:
        data?.answer ||
        '已完成岗位知识库检索。',

      meta: {
        回答方式: answerModeLabel(data),
        城市:
          data?.target_city ||
          '未指定',

        匹配岗位:
          `${matchCount} 条`,

        高频技能:
          skillNames.length
            ? skillNames
                .slice(0, 5)
                .join('、')
            : '暂无'
      },

      detail: {
        回答方式: answerModeLabel(data),
        使用模型: isModelAnswer(data) ? (data.model_reported || data.model || '未提供') : '未使用模型生成',
        生成状态: data?.ai_notice || '规则检索',
        引用摘录: Array.isArray(data?.citations)
          ? data.citations.map(item => `${item.job_id}：${item.quote}`)
          : [],
        问题:
          text,

        回答:
          data?.answer ||
          '暂无回答',

        识别城市:
          data?.target_city ||
          '未识别',

        高频技能:
          skillNames,

        匹配岗位数量:
          matchCount,

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
      历史记录保存失败不应该影响
      就业问答本身正常使用。
    */
    console.error(
      '保存 就业问答历史记录失败：',
      error
    )
  }
}


/* =========================
   提问
========================= */

const askQuestion = async () => {
  if (loading.value) return
  const text = question.value.trim()

  if (!text) {
    errorMessage.value =
      '请输入你想了解的问题'

    return
  }

  loading.value = true

  errorMessage.value = ''

  result.value = null

  const controller = new AbortController()
  activeController = controller
  const waitTimer = setTimeout(() => controller.abort(), 60000)

  try {
    const response = await fetch(
      '/api/ask',
      {
        method: 'POST',
        signal: controller.signal,

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
      let detail = ''

      try {
        const errorData =
          await response.json()

        detail = typeof errorData?.detail === 'string'
          ? errorData.detail
          : '问题格式不正确，请输入 1～2000 字的问题。'

      } catch {
        // 无法解析错误响应时忽略
      }

      throw new Error(
        detail ||
        '就业问答请求失败'
      )
    }

    const data =
      await response.json()

    /*
      先正常展示问答结果
    */
    result.value = data

    /*
      问答成功之后，
      自动写入历史记录
    */
    saveAskHistory(
      text,
      data
    )

  } catch (error) {
    errorMessage.value =
      (error?.name === 'AbortError' ? '请求等待超时或已取消，请稍后重试。' : error?.message) ||
      '就业问答服务暂时不可用，请确认后端服务是否已经启动。'

  } finally {
    clearTimeout(waitTimer)
    if (activeController === controller) activeController = null
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
  <div class="ask-page">

    <!-- =====================
         页面标题
    ====================== -->

    <header class="page-header">

      <div>
        <h1>
          就业知识问答
        </h1>

        <p>
          基于当前岗位样本，为你检索岗位、技能和就业信息
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
          问答
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
          maxlength="2000"
          aria-label="就业问题"
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
              ? '处理中...'
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
        正在检索岗位并整理回答，请稍候...
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
            {{ isModelAnswer(result) ? 'RAG' : '检索' }}
          </span>


          <div>
            <strong>
              CareerLens 回答
            </strong>

            <p class="answer-source">
              回答方式：{{ answerModeLabel(result) }}
            </p>
          </div>

        </div>


        <!-- 回答正文 -->

        <div v-if="isModelAnswer(result) && result.answer_blocks?.length" class="answer-text">
          <p v-for="(block, index) in result.answer_blocks" :key="index">
            {{ block.text }}
            <a
              v-for="citation in block.citations"
              :key="`${citation.job_id}-${citation.quote}`"
              class="citation-link"
              :href="`#evidence-${citation.job_id}`"
              :title="citation.quote"
              :aria-label="`查看 ${citation.job_id} 岗位原文`"
            >[{{ citation.job_id }}]</a>
          </p>
        </div>
        <p v-else class="answer-text">
          {{ result.answer }}
        </p>

        <p v-if="result.ai_notice" class="mode-notice" role="status">{{ result.ai_notice }}</p>
        <p class="generation-meta">
          检索命中 {{ result.matched_count || 0 }} 条 · 展示 {{ result.matches?.length || 0 }} 条
          <template v-if="isModelAnswer(result)">
            · 模型参考 {{ result.evidence_count }} 条
            · {{ result.model_reported || result.model }}
          </template>
        </p>

        <section v-if="isModelAnswer(result) && result.citations?.length" class="citation-excerpts">
          <h3>本次引用摘录</h3>
          <ul>
            <li v-for="(citation, index) in result.citations" :key="index">
              <a class="citation-link" :href="`#evidence-${citation.job_id}`">{{ citation.job_id }}</a>
              <span> · {{ citation.field === 'skills' ? '岗位技能标签' : '岗位描述' }}</span>
              <blockquote>{{ citation.quote }}</blockquote>
            </li>
          </ul>
        </section>


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
            全部命中岗位高频技能
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
                  ? '当前城市暂无严格匹配岗位，以下为其他城市的相近岗位样本'
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

            <details :id="`evidence-${job.job_id}`" class="job-source" open>
              <summary>溯源原文 · {{ job.job_id || '岗位记录' }}</summary>
              <p class="source-meta">
                数据集：{{ job.dataset || 'jobs_sample.csv' }}
                · 来源标记：{{ job.source || '未提供' }}
                · 发布日期：{{ job.publish_date || '未提供' }}
              </p>
              <blockquote v-if="job.job_description">{{ job.job_description }}</blockquote>
              <p v-else class="source-meta">此条样本未提供岗位描述原文。</p>
            </details>

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

.answer-text { white-space: pre-wrap; overflow-wrap: anywhere; }
.answer-text > p { margin: 0 0 14px; }
.answer-text > p:last-child { margin-bottom: 0; }
.citation-link { color: var(--primary); font-weight: 600; margin-left: 5px; overflow-wrap: anywhere; }
.mode-notice { color: var(--text-2); font-size: 13px; line-height: 1.8; }
.generation-meta { color: var(--text-3); font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.citation-excerpts { margin-top: 20px; }
.citation-excerpts h3 { font-size: 15px; margin-bottom: 12px; }
.citation-excerpts ul { padding: 0; list-style: none; }
.citation-excerpts li { margin: 12px 0; font-size: 13px; color: var(--text-2); }
.citation-excerpts blockquote { margin: 6px 0 0; padding-left: 12px; border-left: 2px solid var(--border); white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.8; }
.job-source { scroll-margin-top: 20px; }

.job-source {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--surface-2);
  border-left: 3px solid var(--brand-2);
}
.job-source summary { cursor: pointer; color: var(--text); font-weight: 600; }
.source-meta { color: var(--text-2); font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; }
.job-source blockquote { margin: 10px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--text-2); line-height: 1.8; }



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
  color: var(--text);
}


.page-header p {
  margin: 0;
  color: var(--text-2);
  font-size: 14px;
}


.knowledge-badge {
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 13px;
}


/* =========================
   输入卡片
========================= */

.ask-card {
  padding: 26px;
  background: var(--surface);
  border: none;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
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
  background: var(--brand-grad);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
}


.ask-title h2 {
  margin: 0 0 5px;
  font-size: 19px;
}


.ask-title p {
  margin: 0;
  color: var(--text-3);
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
  border: 1px solid var(--border);
  border-radius: 12px;
  outline: none;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-2);
  background: #fafbfc;
}


textarea:focus {
  border-color: var(--brand-2);
  background: #ffffff;
}


.send-button {
  height: 46px;
  padding: 0 24px;
  border: none;
  border-radius: 11px;
  background: var(--brand-grad);
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.32);
  transition: filter 0.2s ease;
}


.send-button:hover {
  filter: brightness(1.06);
}


.send-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}


.shortcut-tip {
  margin-top: 8px;
  color: var(--text-3);
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
  color: var(--text-2);
  font-size: 13px;
}


.example-button {
  padding: 8px 12px;
  border: 1px solid var(--primary-soft);
  border-radius: 8px;
  background: var(--primary-soft);
  color: var(--primary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}


.example-button:hover {
  background: #e0e7ff;
}


/* =========================
   回答卡片
========================= */

.answer-card {
  margin-top: 20px;
  padding: 24px;
  background: var(--surface);
  border: none;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}


.answer-header {
  display: flex;
  align-items: center;
  gap: 12px;
}


.answer-header strong {
  color: var(--text);
}


.answer-source {
  margin: 4px 0 0;
  color: var(--text-3);
  font-size: 12px;
}


.answer-text {
  margin: 20px 0;
  padding: 16px 18px;
  border-radius: 12px;
  background: var(--surface-2);
  color: var(--text-2);
  line-height: 1.8;
  border-left: 3px solid var(--brand-2);
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
  color: var(--text-2);
  font-size: 13px;
}


.condition-value {
  padding: 5px 10px;
  border-radius: 6px;
  background: var(--primary-soft);
  color: var(--primary);
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
  background: var(--primary-soft);
  color: var(--primary);
}


.skill-tag small {
  color: var(--text-2);
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
  color: var(--text-3);
  font-size: 13px;
}


.section-title > span {
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
  transition: all 0.2s ease;
}


.job-card:hover {
  transform: translateY(-3px);
  border-color: #c7d2fe;
  box-shadow: var(--shadow-lg);
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
  color: var(--text-2);
  font-size: 13px;
}


.salary {
  color: var(--primary);
  font-size: 18px;
  font-weight: 600;
}


.job-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 15px;
  color: var(--text-2);
  font-size: 13px;
}


.score-tag {
  color: var(--primary);
}


.job-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 15px;
}


.job-skills span {
  padding: 5px 9px;
  background: var(--surface-2);
  border-radius: 6px;
  color: var(--text-2);
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
  border: 1px solid var(--border);
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
  background: var(--surface-2);
  color: var(--text-2);
  font-weight: 700;
}


.empty-card h3 {
  margin: 0 0 6px;
  font-size: 16px;
}


.empty-card p {
  margin: 0;
  color: var(--text-2);
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
  background: var(--surface);
  border: none;
  box-shadow: var(--shadow-sm);
  color: var(--text-2);
}


.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand-2);
  animation: pulse 1s infinite;
}


.error-message {
  background: var(--red-soft);
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
