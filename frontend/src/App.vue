<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch
} from 'vue'

import * as echarts from 'echarts'

import AskPage from './components/AskPage.vue'
import SkillTestPage from './components/SkillTestPage.vue'
import JobRecommendPage from './components/JobRecommendPage.vue'
import TrendPage from './components/TrendPage.vue'
import HistoryPage from './components/HistoryPage.vue'


/* =========================================================
   页面切换
========================================================= */

const activePage = ref('dashboard')

const setPage = (page) => {
  activePage.value = page
}


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
      trigger: 'axis'
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
          color: '#bfdbfe',
          opacity: 0.3
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

        <h2>
          CareerLens
        </h2>

        <p>
          职见
        </p>

      </div>


      <nav>

        <div
          class="nav-item"
          :class="{
            active:
              activePage === 'dashboard'
          }"
          @click="
            setPage('dashboard')
          "
        >
          首页 · 总览
        </div>


        <div
          class="nav-item"
          :class="{
            active:
              activePage === 'ask'
          }"
          @click="
            setPage('ask')
          "
        >
          AI 问答
        </div>


        <div
          class="nav-item"
          :class="{
            active:
              activePage === 'skills'
          }"
          @click="
            setPage('skills')
          "
        >
          技能测评
        </div>


        <div
          class="nav-item"
          :class="{
            active:
              activePage === 'recommend'
          }"
          @click="
            setPage('recommend')
          "
        >
          岗位推荐
        </div>


        <div
          class="nav-item"
          :class="{
            active:
              activePage === 'trends'
          }"
          @click="
            setPage('trends')
          "
        >
          趋势分析
        </div>


        <div
          class="nav-item"
          :class="{
            active:
              activePage === 'history'
          }"
          @click="
            setPage('history')
          "
        >
          历史记录
        </div>

      </nav>

    </aside>


    <!-- ===================================================
         主内容区域
    ==================================================== -->

    <main class="main">


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

            <p>
              岗位总量
            </p>

            <strong>
              {{ overview.jobCount }}
            </strong>

          </div>


          <div class="card">

            <p>
              平均薪资
            </p>

            <strong>
              ¥{{ overview.avgSalary }}k
            </strong>

          </div>


          <div class="card">

            <p>
              热门行业
            </p>

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
           AI 问答
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
  background: #f6f8fb;
  color: #111827;
}


/* =========================================================
   左侧导航
========================================================= */

.sidebar {
  width: 220px;
  min-width: 220px;
  min-height: 100vh;
  padding: 30px 22px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
}


.brand h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}


.brand p {
  margin: 6px 0 30px;
  color: #2563eb;
  font-size: 18px;
}


.nav-item {
  padding: 13px 16px;
  margin-bottom: 8px;
  border-radius: 10px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s ease;
}


.nav-item:hover {
  background: #f3f4f6;
  color: #374151;
}


.nav-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
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
  color: #111827;
  font-size: 28px;
}


.page-header span {
  color: #9ca3af;
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
  padding: 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.card p {
  margin: 0 0 12px;
  color: #6b7280;
}


.card strong {
  color: #111827;
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
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.panel h3 {
  margin: 0 0 24px;
  color: #111827;
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
  color: #374151;
}


.city-count {
  width: 30px;
  flex-shrink: 0;
  color: #9ca3af;
  font-size: 12px;
  text-align: right;
}


.bar-bg {
  flex: 1;
  height: 12px;
  overflow: hidden;
  background: #eef2f7;
  border-radius: 999px;
}


.bar {
  height: 100%;
  background: #3b82f6;
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
  color: #9ca3af;
  font-size: 11px;
}


.salary-bar {
  width: 48px;
  max-width: 80%;
  min-height: 2px;
  background: #60a5fa;
  border-radius: 6px 6px 0 0;
  transition: height 0.4s ease;
}


.salary-item span {
  margin-top: 10px;
  color: #6b7280;
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
  background: #eff6ff;
  color: #2563eb;
  border-radius: 8px;
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
  color: #9ca3af;
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
      1px solid #e5e7eb;
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