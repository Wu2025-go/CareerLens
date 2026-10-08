<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'

const overview = {
  jobCount: '1,000',
  avgSalary: '13.6k',
  hotIndustry: '软件开发'
}

const cities = [
  { name: '广州', value: 88 },
  { name: '深圳', value: 82 },
  { name: '北京', value: 76 },
  { name: '上海', value: 70 }
]

const skills = [
  'Java',
  'Python',
  'SQL',
  'Spring',
  '数据清洗',
  'Linux',
  '机器学习',
  'Git'
]

const trendChart = ref(null)
let chartInstance = null

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  chartInstance = echarts.init(trendChart.value)

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: '8%',
      right: '5%',
      top: '10%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['4月', '5月', '6月', '7月', '8月', '9月'],
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
        name: '岗位热度',
        type: 'line',
        smooth: true,
        data: [420, 510, 480, 620, 670, 760],
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: '#3b82f6'
        },
        itemStyle: {
          color: '#3b82f6'
        },
        areaStyle: {
          color: '#bfdbfe',
          opacity: 0.25
        }
      }
    ]
  })

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<template>
  <div class="app">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="brand">
        <h2>CareerLens</h2>
        <p>职见</p>
      </div>

      <nav>
        <div class="nav-item active">首页 · 总览</div>
        <div class="nav-item">AI 问答</div>
        <div class="nav-item">技能测评</div>
        <div class="nav-item">岗位推荐</div>
        <div class="nav-item">趋势分析</div>
        <div class="nav-item">历史记录</div>
      </nav>
    </aside>

    <!-- 主内容 -->
    <main class="main">
      <header class="page-header">
        <h1>就业市场总览</h1>
        <span>CareerLens · 就业数据分析平台</span>
      </header>

      <!-- 顶部统计卡片 -->
      <section class="cards">
        <div class="card">
          <p>岗位总量</p>
          <strong>{{ overview.jobCount }}</strong>
        </div>

        <div class="card">
          <p>平均薪资</p>
          <strong>¥{{ overview.avgSalary }}</strong>
        </div>

        <div class="card">
          <p>热门行业</p>
          <strong>{{ overview.hotIndustry }}</strong>
        </div>
      </section>

      <!-- 数据分析区域 -->
      <section class="grid">
        <!-- 城市岗位分布 -->
        <div class="panel">
          <h3>城市岗位分布</h3>

          <div
            v-for="city in cities"
            :key="city.name"
            class="city-row"
          >
            <span>{{ city.name }}</span>

            <div class="bar-bg">
              <div
                class="bar"
                :style="{ width: city.value + '%' }"
              ></div>
            </div>
          </div>
        </div>

        <!-- 薪资区间 -->
        <div class="panel">
          <h3>薪资区间分布</h3>

          <div class="salary-chart">
            <div class="salary-item">
              <div class="salary-bar h1"></div>
              <span>5k以下</span>
            </div>

            <div class="salary-item">
              <div class="salary-bar h2"></div>
              <span>5-10k</span>
            </div>

            <div class="salary-item">
              <div class="salary-bar h3"></div>
              <span>10-15k</span>
            </div>

            <div class="salary-item">
              <div class="salary-bar h4"></div>
              <span>15-25k</span>
            </div>

            <div class="salary-item">
              <div class="salary-bar h5"></div>
              <span>25k+</span>
            </div>
          </div>
        </div>

        <!-- 行业热度趋势 -->
        <div class="panel">
          <h3>行业热度趋势</h3>
          <div ref="trendChart" class="trend-chart"></div>
        </div>

        <!-- 高频技能 -->
        <div class="panel">
          <h3>高频技能</h3>

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
}

.nav-item:hover {
  background: #f3f4f6;
}

.nav-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

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
}

.page-header span {
  color: #9ca3af;
  font-size: 14px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  font-size: 30px;
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
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
}

.city-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 22px 0;
}

.city-row span {
  width: 44px;
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
}

.h1 {
  height: 60px;
}

.h2 {
  height: 115px;
}

.h3 {
  height: 155px;
}

.h4 {
  height: 95px;
}

.h5 {
  height: 45px;
}

.trend-chart {
  width: 100%;
  height: 190px;
}

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
</style>