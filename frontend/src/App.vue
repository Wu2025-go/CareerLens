<script setup>
import {
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch
} from 'vue'

import { usePageNavigation } from './utils/navigation'

const AskPage = defineAsyncComponent(() => import('./components/AskPage.vue'))
const SkillTestPage = defineAsyncComponent(() => import('./components/SkillTestPage.vue'))
const JobRecommendPage = defineAsyncComponent(() => import('./components/JobRecommendPage.vue'))
const TrendPage = defineAsyncComponent(() => import('./components/TrendPage.vue'))
const HistoryPage = defineAsyncComponent(() => import('./components/HistoryPage.vue'))


/* =========================================================
   页面切换
========================================================= */

const { activePage, setPage, navigate } = usePageNavigation()


/* =========================================================
   首页顶部数据
========================================================= */

const overview = reactive({
  jobCount: '--',
  avgSalary: '--',
  hotIndustry: '加载中...'
})


/* =========================================================
   Dashboard 数据
========================================================= */

const cities = ref([])
const salaryDistribution = ref([])
const skills = ref([])

const trend = reactive({
  months: [],
  values: []
})


/* =========================================================
   状态
========================================================= */

const dashboardError = ref('')


/* =========================================================
   首页趋势图
========================================================= */

const trendChartRef = ref(null)

let trendChartInstance = null


const renderTrendChart = async () => {
  await nextTick()

  if (
    activePage.value !== 'dashboard' ||
    !trendChartRef.value ||
    trend.values.length === 0
  ) {
    return
  }

  const { default: echarts } = await import('./utils/charts')
  if (activePage.value !== 'dashboard' || !trendChartRef.value) return

  if (trendChartInstance) {
    trendChartInstance.dispose()
    trendChartInstance = null
  }

  trendChartInstance =
    echarts.init(
      trendChartRef.value
    )

  trendChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e8ecf3',
      borderWidth: 1,
      padding: [10, 12],
      textStyle: {
        color: '#0f172a',
        fontSize: 12
      },
      extraCssText:
        'border-radius: 10px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);'
    },

    grid: {
      left: '5%',
      right: '5%',
      top: 35,
      bottom: 35,
      containLabel: true
    },

    xAxis: {
      type: 'category',

      data:
        trend.months,

      boundaryGap: false,

      axisLine: {
        lineStyle: {
          color: '#d1d5db'
        }
      },

      axisLabel: {
        color: '#6b7280'
      }
    },

    yAxis: {
      type: 'value',

      name: '岗位热度',

      axisLabel: {
        color: '#6b7280'
      },

      splitLine: {
        lineStyle: {
          color: '#eef2f7'
        }
      }
    },

    series: [
      {
        name: '岗位数量',

        type: 'line',

        smooth: true,

        symbolSize: 7,

        data:
          trend.values,

        lineStyle: {
          width: 3,
          color: '#3b82f6'
        },

        itemStyle: {
          color: '#3b82f6'
        },

        areaStyle: {
          color: new echarts.graphic.LinearGradient(
            0,
            0,
            0,
            1,
            [
              { offset: 0, color: 'rgba(59, 130, 246, 0.30)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.02)' }
            ]
          )
        }
      }
    ]
  })
}


/* =========================================================
   获取首页数据
========================================================= */

const loadDashboard = async () => {
  dashboardError.value = ''

  try {
    const [
      overviewResponse,
      dashboardResponse
    ] = await Promise.all([
      fetch(
        '/api/overview'
      ),

      fetch(
        '/api/dashboard'
      )
    ])

    if (!overviewResponse.ok) {
      throw new Error(
        '获取首页概览数据失败'
      )
    }

    if (!dashboardResponse.ok) {
      throw new Error(
        '获取首页分析数据失败'
      )
    }

    const overviewData =
      await overviewResponse.json()

    const dashboardData =
      await dashboardResponse.json()


    /* 顶部统计 */

    overview.jobCount =
      Number(
        overviewData.job_count || 0
      ).toLocaleString()

    overview.avgSalary =
      overviewData.avg_salary ?? 0

    overview.hotIndustry =
      overviewData.hot_industry ||
      '暂无数据'


    /* Dashboard */

    cities.value =
      dashboardData.cities || []

    salaryDistribution.value =
      dashboardData.salary_distribution || []

    skills.value =
      dashboardData.skills || []

    trend.months =
      dashboardData.trend?.months || []

    trend.values =
      dashboardData.trend?.values || []


    await renderTrendChart()

  } catch (error) {
    console.error(error)

    dashboardError.value =
      error.message ||
      '首页数据加载失败'

    overview.jobCount =
      '获取失败'

    overview.avgSalary =
      '--'

    overview.hotIndustry =
      '获取失败'
  }
}


/* =========================================================
   薪资柱状图高度
========================================================= */

const getSalaryBarHeight = (value) => {
  const maxValue = Math.max(
    ...salaryDistribution.value.map(
      item =>
        Number(item.value) || 0
    ),
    1
  )

  const number =
    Number(value) || 0

  if (number === 0) {
    return '2px'
  }

  const percentage =
    number / maxValue

  return `${
    Math.max(
      percentage * 160,
      8
    )
  }px`
}


/* =========================================================
   Resize
========================================================= */

const handleResize = () => {
  trendChartInstance?.resize()
}


/* =========================================================
   切回首页重新渲染图表
========================================================= */

watch(
  activePage,
  async (page) => {
    if (page === 'dashboard') {
      await renderTrendChart()
    }
  }
)


/* =========================================================
   生命周期
========================================================= */

onMounted(() => {
  loadDashboard()

  window.addEventListener(
    'resize',
    handleResize
  )
})


onBeforeUnmount(() => {
  window.removeEventListener(
    'resize',
    handleResize
  )

  trendChartInstance?.dispose()
})
</script>


<template>
  <div class="app">

    <!-- ===================================================
         左侧导航栏
    ==================================================== -->

    <aside class="sidebar">

      <div class="brand">

        <div class="brand-logo">
          CL
        </div>

        <div class="brand-text">

          <h2>
            CareerLens
          </h2>

          <p>
            职见
          </p>

        </div>

      </div>


      <nav>

        <a href="/" :aria-current="activePage === 'dashboard' ? 'page' : undefined"
          class="nav-item"
          :class="{
            active:
              activePage === 'dashboard'
          }"
          @click="
            navigate($event, 'dashboard')
          "
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>
          <span>首页 · 总览</span>
        </a>


        <a href="/ask" :aria-current="activePage === 'ask' ? 'page' : undefined"
          class="nav-item"
          :class="{
            active:
              activePage === 'ask'
          }"
          @click="
            navigate($event, 'ask')
          "
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 9.6 9.6 0 0 1-4-1L3 20l1.5-5a8.38 8.38 0 0 1-1-4 8.5 8.5 0 0 1 17 0z"/></svg>
          <span>就业问答</span>
        </a>


        <a href="/skills" :aria-current="activePage === 'skills' ? 'page' : undefined"
          class="nav-item"
          :class="{
            active:
              activePage === 'skills'
          }"
          @click="
            navigate($event, 'skills')
          "
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>
          <span>技能测评</span>
        </a>


        <a href="/recommend" :aria-current="activePage === 'recommend' ? 'page' : undefined"
          class="nav-item"
          :class="{
            active:
              activePage === 'recommend'
          }"
          @click="
            navigate($event, 'recommend')
          "
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          <span>岗位推荐</span>
        </a>


        <a href="/trends" :aria-current="activePage === 'trends' ? 'page' : undefined"
          class="nav-item"
          :class="{
            active:
              activePage === 'trends'
          }"
          @click="
            navigate($event, 'trends')
          "
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-5"/><path d="M13 16V8"/><path d="M18 16v-9"/></svg>
          <span>趋势分析</span>
        </a>


        <a href="/history" :aria-current="activePage === 'history' ? 'page' : undefined"
          class="nav-item"
          :class="{
            active:
              activePage === 'history'
          }"
          @click="
            navigate($event, 'history')
          "
        >
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
          <span>历史记录</span>
        </a>

      </nav>

    </aside>


    <!-- ===================================================
         主内容区域
    ==================================================== -->

    <main class="main">

      <section v-if="activePage === 'not-found'" class="error-box">
        <h1>页面不存在</h1>
        <p>请通过左侧导航选择功能，或返回首页。</p>
        <button @click="setPage('dashboard')">返回首页</button>
      </section>


      <!-- =================================================
           首页
      ================================================== -->

      <template
        v-if="
          activePage === 'dashboard'
        "
      >

        <header class="page-header">

          <h1>
            就业市场总览
          </h1>

          <span>
            CareerLens · 就业数据分析平台
          </span>

        </header>


        <div
          v-if="dashboardError"
          class="error-box"
        >
          {{ dashboardError }}
        </div>


        <!-- 顶部统计 -->

        <section class="cards">

          <div class="card">

            <div class="card-top">

              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </span>

              <p>
                岗位总量
              </p>

            </div>

            <strong>
              {{ overview.jobCount }}
            </strong>

          </div>


          <div class="card">

            <div class="card-top">

              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
              </span>

              <p>
                平均薪资
              </p>

            </div>

            <strong>
              ¥{{ overview.avgSalary }}k
            </strong>

          </div>


          <div class="card">

            <div class="card-top">

              <span class="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2s4 4 4 9a4 4 0 0 1-8 0c0-5 4-9 4-9z"/></svg>
              </span>

              <p>
                热门行业
              </p>

            </div>

            <strong>
              {{ overview.hotIndustry }}
            </strong>

          </div>

        </section>


        <!-- Dashboard -->

        <section class="grid">


          <!-- 城市岗位分布 -->

          <div class="panel">

            <h3>
              城市岗位分布
            </h3>


            <template
              v-if="
                cities.length
              "
            >

              <div
                v-for="city in cities"
                :key="city.name"
                class="city-row"
              >

                <span class="city-name">
                  {{ city.name }}
                </span>


                <div class="bar-bg">

                  <div
                    class="bar"
                    :style="{
                      width:
                        city.value + '%'
                    }"
                  ></div>

                </div>


                <span
                  v-if="
                    city.count !==
                    undefined
                  "
                  class="city-count"
                >
                  {{ city.count }}
                </span>

              </div>

            </template>


            <div
              v-else
              class="empty-state"
            >
              暂无城市岗位数据
            </div>

          </div>


          <!-- 薪资区间 -->

          <div class="panel">

            <h3>
              薪资区间分布
            </h3>


            <div
              v-if="
                salaryDistribution.length
              "
              class="salary-chart"
            >

              <div
                v-for="
                  item in
                  salaryDistribution
                "
                :key="item.range"
                class="salary-item"
              >

                <div class="salary-value">
                  {{ item.value }}
                </div>


                <div
                  class="salary-bar"
                  :style="{
                    height:
                      getSalaryBarHeight(
                        item.value
                      )
                  }"
                ></div>


                <span>
                  {{ item.range }}
                </span>

              </div>

            </div>


            <div
              v-else
              class="empty-state"
            >
              暂无薪资统计数据
            </div>

          </div>


          <!-- 趋势 -->

          <div class="panel">

            <h3>
              行业热度趋势
            </h3>


            <div
              v-if="
                trend.values.length
              "
              ref="trendChartRef"
              class="trend-chart"
            ></div>


            <div
              v-else
              class="empty-state trend-empty"
            >
              暂无岗位趋势数据
            </div>

          </div>


          <!-- 高频技能 -->

          <div class="panel">

            <h3>
              高频技能
            </h3>


            <div
              v-if="
                skills.length
              "
              class="skill-list"
            >

              <span
                v-for="
                  skill in skills
                "
                :key="skill"
                class="skill"
              >
                {{ skill }}
              </span>

            </div>


            <div
              v-else
              class="empty-state"
            >
              暂无技能数据
            </div>

          </div>

        </section>

      </template>


      <!-- =================================================
           就业问答
      ================================================== -->

      <AskPage
        v-else-if="
          activePage === 'ask'
        "
      />


      <!-- =================================================
           技能测评
      ================================================== -->

      <SkillTestPage
        v-else-if="
          activePage === 'skills'
        "
      />


      <!-- =================================================
           岗位推荐
      ================================================== -->

      <JobRecommendPage
        v-else-if="
          activePage === 'recommend'
        "
      />


      <!-- =================================================
           趋势分析
      ================================================== -->

      <TrendPage
        v-else-if="
          activePage === 'trends'
        "
      />


      <!-- =================================================
           历史记录
      ================================================== -->

      <HistoryPage
        v-else-if="
          activePage === 'history'
        "
      />

    </main>

  </div>
</template>


<style scoped>

* {
  box-sizing: border-box;
}


.app {
  display: flex;
  width: 100%;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}


/* =========================================================
   左侧导航
========================================================= */

.sidebar {
  width: 244px;
  min-width: 244px;
  min-height: 100vh;
  padding: 30px 20px;
  background: var(--side-grad);
  box-shadow: 6px 0 24px rgba(30, 27, 75, 0.18);
  position: sticky;
  top: 0;
}


.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px 26px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}


.brand-logo {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  color: #ffffff;
  font-weight: 700;
  font-size: 18px;
  backdrop-filter: blur(4px);
}


.brand-text h2 {
  margin: 0;
  color: #ffffff;
  font-size: 19px;
  letter-spacing: 0.3px;
}


.brand-text p {
  margin: 2px 0 0;
  color: rgba(199, 210, 254, 0.85);
  font-size: 13px;
}


.nav-item {
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 6px;
  border-radius: 11px;
  color: rgba(226, 232, 240, 0.78);
  font-size: 14.5px;
  cursor: pointer;
  transition: all 0.2s ease;
}


.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}


.nav-item.active {
  background: rgba(255, 255, 255, 0.16);
  color: #ffffff;
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--brand-2);
}


.nav-icon {
  width: 19px;
  height: 19px;
  flex-shrink: 0;
}


/* =========================================================
   主区域
========================================================= */

.main {
  flex: 1;
  min-width: 0;
  padding: 34px;
}


/* =========================================================
   首页标题
========================================================= */

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
}


.page-header h1 {
  margin: 0;
  color: var(--text);
  font-size: 27px;
  letter-spacing: 0.2px;
}


.page-header span {
  color: var(--text-3);
  font-size: 14px;
}


/* =========================================================
   顶部统计
========================================================= */

.cards {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 20px;
}


.card {
  position: relative;
  padding: 22px 24px;
  background: var(--surface);
  border: none;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}


.card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  width: 4px;
  height: 100%;
  background: var(--brand-grad);
}


.card-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}


.card-icon {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 11px;
  background: var(--brand-grad);
  color: #ffffff;
  box-shadow: var(--shadow-sm);
}


.card-icon svg {
  width: 20px;
  height: 20px;
}


.card p {
  margin: 0;
  color: var(--text-2);
  font-size: 14px;
}


.card strong {
  color: var(--text);
  font-size: 30px;
  font-weight: 600;
}


/* =========================================================
   Dashboard
========================================================= */

.grid {
  display: grid;
  grid-template-columns:
    repeat(
      2,
      minmax(0, 1fr)
    );
  gap: 20px;
}


.panel {
  min-width: 0;
  min-height: 280px;
  padding: 22px;
  background: var(--surface);
  border: none;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}


.panel h3 {
  margin: 0 0 24px;
  color: var(--text);
  font-size: 19px;
}


/* =========================================================
   城市岗位
========================================================= */

.city-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 19px 0;
}


.city-name {
  width: 48px;
  flex-shrink: 0;
  color: var(--text-2);
}


.city-count {
  width: 30px;
  flex-shrink: 0;
  color: var(--text-3);
  font-size: 12px;
  text-align: right;
}


.bar-bg {
  flex: 1;
  height: 12px;
  overflow: hidden;
  background: var(--border);
  border-radius: 999px;
}


.bar {
  height: 100%;
  background: var(--brand-grad);
  border-radius: 999px;
  transition: width 0.4s ease;
}


/* =========================================================
   薪资
========================================================= */

.salary-chart {
  height: 205px;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 10px;
  padding-top: 15px;
}


.salary-item {
  height: 100%;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
}


.salary-value {
  margin-bottom: 5px;
  color: var(--text-3);
  font-size: 11px;
}


.salary-bar {
  width: 48px;
  max-width: 80%;
  min-height: 2px;
  background: var(--brand-grad);
  border-radius: 6px 6px 0 0;
  transition: height 0.4s ease;
}


.salary-item span {
  margin-top: 10px;
  color: var(--text-2);
  font-size: 12px;
}


/* =========================================================
   趋势
========================================================= */

.trend-chart {
  width: 100%;
  height: 210px;
}


.trend-empty {
  height: 200px;
}


/* =========================================================
   高频技能
========================================================= */

.skill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}


.skill {
  padding: 9px 14px;
  background: var(--primary-soft);
  color: var(--primary);
  border-radius: 8px;
  font-size: 13px;
}


/* =========================================================
   状态
========================================================= */

.error-box {
  margin-bottom: 18px;
  padding: 14px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #b91c1c;
}


.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  color: var(--text-3);
  font-size: 13px;
}


/* =========================================================
   响应式
========================================================= */

@media (max-width: 1050px) {

  .cards {
    grid-template-columns: 1fr;
  }


  .grid {
    grid-template-columns: 1fr;
  }

}


@media (max-width: 760px) {

  .app {
    flex-direction: column;
  }


  .sidebar {
    width: 100%;
    min-width: 0;
    min-height: auto;
    padding: 20px;
    border-right: none;
    border-bottom:
      1px solid var(--border);
  }


  .brand p {
    margin-bottom: 18px;
  }


  nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }


  .nav-item {
    margin-bottom: 0;
  }


  .main {
    padding: 20px;
  }


  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

}
</style>
