<script setup>
import {
  onMounted,
  onBeforeUnmount,
  ref,
  reactive,
  computed
} from 'vue'

import * as echarts from 'echarts'


/* =========================
   顶部总览数据
========================= */

const overview = reactive({
  jobCount: '--',
  avgSalary: '--',
  hotIndustry: '加载中...'
})


/* =========================
   Dashboard 数据
========================= */

const cities = ref([])

const salaryDistribution = ref([])

const skills = ref([])

const trend = reactive({
  months: [],
  values: []
})


/* =========================
   薪资柱状图高度计算
========================= */

const maxSalaryValue = computed(() => {
  if (salaryDistribution.value.length === 0) {
    return 1
  }

  return Math.max(
    ...salaryDistribution.value.map(item => item.value)
  )
})

const getSalaryHeight = (value) => {
  return `${(value / maxSalaryValue.value) * 150}px`
}


/* =========================
   ECharts 趋势图
========================= */

const trendChart = ref(null)

let chartInstance = null


const handleResize = () => {
  chartInstance?.resize()
}


const renderTrendChart = () => {
  if (!trendChart.value) {
    return
  }

  if (!chartInstance) {
    chartInstance = echarts.init(trendChart.value)
  }

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis'
    },

    grid: {
      left: '8%',
      right: '5%',
      top: '12%',
      bottom: '15%',
      containLabel: true
    },

    xAxis: {
      type: 'category',

      data: trend.months,

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

      axisLine: {
        show: false
      },

      axisTick: {
        show: false
      },

      splitLine: {
        lineStyle: {
          color: '#eef2f7'
        }
      }
    },

    series: [
      {
        name: '岗位热度',

        type: 'line',

        smooth: true,

        data: trend.values,

        symbol: 'circle',

        symbolSize: 8,

        lineStyle: {
          width: 3,
          color: '#3b82f6'
        },

        itemStyle: {
          color: '#3b82f6',
          borderColor: '#ffffff',
          borderWidth: 2
        },

        areaStyle: {
          color: '#bfdbfe',
          opacity: 0.28
        }
      }
    ]
  })
}


/* =========================
   页面加载
========================= */

onMounted(async () => {
  try {
    /* 同时请求两个接口 */

    const [
      overviewResponse,
      dashboardResponse
    ] = await Promise.all([
      fetch('http://127.0.0.1:8000/api/overview'),

      fetch('http://127.0.0.1:8000/api/dashboard')
    ])


    if (!overviewResponse.ok) {
      throw new Error('获取 overview 数据失败')
    }

    if (!dashboardResponse.ok) {
      throw new Error('获取 dashboard 数据失败')
    }


    /* 顶部数据 */

    const overviewData =
      await overviewResponse.json()

    overview.jobCount =
      overviewData.job_count.toLocaleString()

    overview.avgSalary =
      `${overviewData.avg_salary}k`

    overview.hotIndustry =
      overviewData.hot_industry


    /* Dashboard 数据 */

    const dashboardData =
      await dashboardResponse.json()


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


    /* 渲染趋势图 */

    renderTrendChart()

  } catch (error) {

    console.error(
      '首页数据加载失败：',
      error
    )

    overview.jobCount = '获取失败'

    overview.avgSalary = '--'

    overview.hotIndustry = '获取失败'
  }


  window.addEventListener(
    'resize',
    handleResize
  )
})


/* =========================
   页面卸载
========================= */

onBeforeUnmount(() => {

  window.removeEventListener(
    'resize',
    handleResize
  )

  if (chartInstance) {

    chartInstance.dispose()

    chartInstance = null
  }
})
</script>


<template>

  <div class="app">

    <!-- 左侧导航 -->

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

        <div class="nav-item active">
          首页 · 总览
        </div>

        <div class="nav-item">
          AI 问答
        </div>

        <div class="nav-item">
          技能测评
        </div>

        <div class="nav-item">
          岗位推荐
        </div>

        <div class="nav-item">
          趋势分析
        </div>

        <div class="nav-item">
          历史记录
        </div>

      </nav>

    </aside>


    <!-- 主内容 -->

    <main class="main">


      <!-- 标题 -->

      <header class="page-header">

        <h1>
          就业市场总览
        </h1>

        <span>
          CareerLens · 就业数据分析平台
        </span>

      </header>


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
            ¥{{ overview.avgSalary }}
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


      <!-- 四个分析模块 -->

      <section class="grid">


        <!-- 城市岗位 -->

        <div class="panel">

          <h3>
            城市岗位分布
          </h3>


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
              >
              </div>

            </div>

          </div>

        </div>


        <!-- 薪资 -->

        <div class="panel">

          <h3>
            薪资区间分布
          </h3>


          <div class="salary-chart">


            <div
              v-for="item in salaryDistribution"
              :key="item.range"
              class="salary-item"
            >

              <div
                class="salary-bar"
                :style="{
                  height:
                    getSalaryHeight(item.value)
                }"
              >
              </div>

              <span>
                {{ item.range }}
              </span>

            </div>


          </div>

        </div>


        <!-- 趋势 -->

        <div class="panel">

          <h3>
            行业热度趋势
          </h3>


          <div
            ref="trendChart"
            class="trend-chart"
          >
          </div>

        </div>


        <!-- 技能 -->

        <div class="panel">

          <h3>
            高频技能
          </h3>


          <div class="skill-list">


            <span
              v-for="skill in skills"
              :key="skill"
              class="skill"
            >

              {{ skill }}

            </span>


          </div>

        </div>


      </section>

    </main>

  </div>

</template>


<style scoped>

* {
  box-sizing: border-box;
}


.app {

  display: flex;

  min-height: 100vh;

  background: #f6f8fb;

  color: #1f2937;
}


/* =========================
   左侧导航
========================= */

.sidebar {

  width: 220px;

  min-height: 100vh;

  padding: 30px 22px;

  background: #ffffff;

  border-right: 1px solid #e5e7eb;
}


.brand h2 {

  margin: 0;

  font-size: 22px;

  color: #111827;
}


.brand p {

  margin: 6px 0 30px;

  font-size: 18px;

  color: #2563eb;
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

  color: #2563eb;
}


.nav-item.active {

  background: #eff6ff;

  color: #2563eb;

  font-weight: 600;
}


/* =========================
   主内容
========================= */

.main {

  flex: 1;

  padding: 34px;
}


.page-header {

  display: flex;

  align-items: center;

  justify-content: space-between;

  margin-bottom: 28px;
}


.page-header h1 {

  margin: 0;

  font-size: 28px;

  color: #111827;
}


.page-header span {

  color: #9ca3af;

  font-size: 14px;
}


/* =========================
   顶部卡片
========================= */

.cards {

  display: grid;

  grid-template-columns:
    repeat(3, 1fr);

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

  font-size: 16px;
}


.card strong {

  font-size: 30px;

  font-weight: 600;

  color: #111827;
}


/* =========================
   四宫格
========================= */

.grid {

  display: grid;

  grid-template-columns:
    repeat(2, 1fr);

  gap: 20px;
}


.panel {

  min-height: 280px;

  padding: 22px;

  background: #ffffff;

  border: 1px solid #e5e7eb;

  border-radius: 14px;
}


.panel h3 {

  margin: 0 0 24px;

  font-size: 19px;

  color: #111827;
}


/* =========================
   城市岗位
========================= */

.city-row {

  display: flex;

  align-items: center;

  gap: 14px;

  margin: 22px 0;
}


.city-name {

  width: 44px;

  flex-shrink: 0;
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
}


/* =========================
   薪资分布
========================= */

.salary-chart {

  height: 190px;

  display: flex;

  align-items: flex-end;

  justify-content: space-around;

  padding-top: 20px;
}


.salary-item {

  height: 100%;

  display: flex;

  flex-direction: column;

  justify-content: flex-end;

  align-items: center;

  gap: 10px;

  color: #6b7280;

  font-size: 13px;
}


.salary-bar {

  width: 48px;

  background: #60a5fa;

  border-radius: 6px 6px 0 0;

  transition: height 0.3s ease;
}


/* =========================
   趋势图
========================= */

.trend-chart {

  width: 100%;

  height: 190px;
}


/* =========================
   高频技能
========================= */

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


/* =========================
   响应式
========================= */

@media (max-width: 1000px) {

  .cards {

    grid-template-columns: 1fr;
  }


  .grid {

    grid-template-columns: 1fr;
  }

}

</style>