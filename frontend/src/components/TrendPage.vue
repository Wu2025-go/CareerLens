<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref
} from 'vue'

import * as echarts from 'echarts'


/* =========================================================
   页面数据
========================================================= */

const summary = reactive({
  jobCount: 0,
  cityCount: 0,
  skillCount: 0,
  avgSalary: 0
})

const loading = ref(true)
const errorMessage = ref('')

const monthlyTrend = ref([])
const topSkills = ref([])
const cityJobs = ref([])
const citySalary = ref([])


/* =========================================================
   图表 DOM
========================================================= */

const trendChartRef = ref(null)
const skillChartRef = ref(null)
const cityChartRef = ref(null)
const salaryChartRef = ref(null)


/* =========================================================
   ECharts 实例
========================================================= */

let trendChart = null
let skillChart = null
let cityChart = null
let salaryChart = null


/* =========================================================
   销毁全部图表
========================================================= */

const disposeCharts = () => {
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }

  if (skillChart) {
    skillChart.dispose()
    skillChart = null
  }

  if (cityChart) {
    cityChart.dispose()
    cityChart = null
  }

  if (salaryChart) {
    salaryChart.dispose()
    salaryChart = null
  }
}


/* =========================================================
   1. 岗位发布趋势图
========================================================= */

const renderTrendChart = () => {
  if (
    !trendChartRef.value ||
    monthlyTrend.value.length === 0
  ) {
    return
  }

  if (trendChart) {
    trendChart.dispose()
  }

  trendChart =
    echarts.init(
      trendChartRef.value
    )

  trendChart.setOption({
    tooltip: {
      trigger: 'axis'
    },

    grid: {
      left: 40,
      right: 25,
      top: 40,
      bottom: 35,
      containLabel: true
    },

    xAxis: {
      type: 'category',

      data:
        monthlyTrend.value.map(
          item =>
            item.label ||
            item.month
        ),

      boundaryGap: false,

      axisLine: {
        lineStyle: {
          color: '#d1d5db'
        }
      },

      axisTick: {
        show: false
      },

      axisLabel: {
        color: '#6b7280'
      }
    },

    yAxis: {
      type: 'value',

      name: '岗位数',

      minInterval: 1,

      nameTextStyle: {
        color: '#9ca3af'
      },

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

        symbol: 'circle',

        symbolSize: 8,

        data:
          monthlyTrend.value.map(
            item =>
              Number(item.count) || 0
          ),

        lineStyle: {
          width: 3,
          color: '#2563eb'
        },

        itemStyle: {
          color: '#2563eb',
          borderColor: '#ffffff',
          borderWidth: 2
        },

        areaStyle: {
          color: '#bfdbfe',
          opacity: 0.35
        }
      }
    ]
  })
}


/* =========================================================
   2. 热门技能 Top 10
========================================================= */

const renderSkillChart = () => {
  if (
    !skillChartRef.value ||
    topSkills.value.length === 0
  ) {
    return
  }

  if (skillChart) {
    skillChart.dispose()
  }

  skillChart =
    echarts.init(
      skillChartRef.value
    )

  const skillData =
    [...topSkills.value]
      .reverse()

  skillChart.setOption({
    tooltip: {
      trigger: 'axis',

      axisPointer: {
        type: 'shadow'
      }
    },

    grid: {
      left: 30,
      right: 40,
      top: 20,
      bottom: 20,
      containLabel: true
    },

    xAxis: {
      type: 'value',

      minInterval: 1,

      axisLabel: {
        color: '#6b7280'
      },

      splitLine: {
        lineStyle: {
          color: '#eef2f7'
        }
      }
    },

    yAxis: {
      type: 'category',

      data:
        skillData.map(
          item => item.name
        ),

      axisLine: {
        show: false
      },

      axisTick: {
        show: false
      },

      axisLabel: {
        color: '#374151'
      }
    },

    series: [
      {
        name: '岗位需求',

        type: 'bar',

        data:
          skillData.map(
            item =>
              Number(item.count) || 0
          ),

        barWidth: 14,

        itemStyle: {
          color: '#3b82f6',

          borderRadius: [
            0,
            7,
            7,
            0
          ]
        },

        label: {
          show: true,
          position: 'right',
          color: '#6b7280'
        }
      }
    ]
  })
}


/* =========================================================
   3. 城市岗位数量
========================================================= */

const renderCityChart = () => {
  if (
    !cityChartRef.value ||
    cityJobs.value.length === 0
  ) {
    return
  }

  if (cityChart) {
    cityChart.dispose()
  }

  cityChart =
    echarts.init(
      cityChartRef.value
    )

  cityChart.setOption({
    tooltip: {
      trigger: 'axis',

      axisPointer: {
        type: 'shadow'
      }
    },

    grid: {
      left: 40,
      right: 20,
      top: 35,
      bottom: 45,
      containLabel: true
    },

    xAxis: {
      type: 'category',

      data:
        cityJobs.value.map(
          item => item.city
        ),

      axisLine: {
        lineStyle: {
          color: '#d1d5db'
        }
      },

      axisTick: {
        show: false
      },

      axisLabel: {
        color: '#6b7280',
        interval: 0
      }
    },

    yAxis: {
      type: 'value',

      name: '岗位数',

      minInterval: 1,

      nameTextStyle: {
        color: '#9ca3af'
      },

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

        type: 'bar',

        data:
          cityJobs.value.map(
            item =>
              Number(item.count) || 0
          ),

        barMaxWidth: 48,

        itemStyle: {
          color: '#60a5fa',

          borderRadius: [
            6,
            6,
            0,
            0
          ]
        },

        label: {
          show: true,
          position: 'top',
          color: '#6b7280'
        }
      }
    ]
  })
}


/* =========================================================
   4. 城市平均薪资
========================================================= */

const renderSalaryChart = () => {
  if (
    !salaryChartRef.value ||
    citySalary.value.length === 0
  ) {
    return
  }

  if (salaryChart) {
    salaryChart.dispose()
  }

  salaryChart =
    echarts.init(
      salaryChartRef.value
    )

  salaryChart.setOption({
    tooltip: {
      trigger: 'axis',

      axisPointer: {
        type: 'shadow'
      },

      formatter(params) {
        const item =
          params?.[0]

        if (!item) {
          return ''
        }

        return (
          `${item.name}<br/>` +
          `平均薪资：${item.value}K/月`
        )
      }
    },

    grid: {
      left: 40,
      right: 20,
      top: 35,
      bottom: 45,
      containLabel: true
    },

    xAxis: {
      type: 'category',

      data:
        citySalary.value.map(
          item => item.city
        ),

      axisLine: {
        lineStyle: {
          color: '#d1d5db'
        }
      },

      axisTick: {
        show: false
      },

      axisLabel: {
        color: '#6b7280',
        interval: 0
      }
    },

    yAxis: {
      type: 'value',

      name: 'K/月',

      nameTextStyle: {
        color: '#9ca3af'
      },

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
        name: '平均薪资',

        type: 'bar',

        data:
          citySalary.value.map(
            item =>
              Number(
                item.avg_salary
              ) || 0
          ),

        barMaxWidth: 48,

        itemStyle: {
          color: '#2563eb',

          borderRadius: [
            6,
            6,
            0,
            0
          ]
        },

        label: {
          show: true,

          position: 'top',

          formatter(params) {
            return `${params.value}K`
          },

          color: '#2563eb'
        }
      }
    ]
  })
}


/* =========================================================
   初始化所有可以显示的图表
========================================================= */

const initCharts = () => {
  renderTrendChart()
  renderSkillChart()
  renderCityChart()
  renderSalaryChart()
}


/* =========================================================
   获取趋势数据
========================================================= */

const loadTrendData = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const response =
      await fetch(
        '/api/trends'
      )

    if (!response.ok) {
      throw new Error(
        '获取趋势分析数据失败'
      )
    }

    const data =
      await response.json()


    /* =========================
       顶部概览
    ========================= */

    summary.jobCount =
      Number(
        data.summary?.job_count
      ) || 0

    summary.cityCount =
      Number(
        data.summary?.city_count
      ) || 0

    summary.skillCount =
      Number(
        data.summary?.skill_count
      ) || 0

    summary.avgSalary =
      Number(
        data.summary?.avg_salary
      ) || 0


    /* =========================
       图表数据
    ========================= */

    monthlyTrend.value =
      Array.isArray(
        data.monthly_trend
      )
        ? data.monthly_trend
        : []

    topSkills.value =
      Array.isArray(
        data.top_skills
      )
        ? data.top_skills
        : []

    cityJobs.value =
      Array.isArray(
        data.city_jobs
      )
        ? data.city_jobs
        : []

    citySalary.value =
      Array.isArray(
        data.city_salary
      )
        ? data.city_salary
        : []


  } catch (error) {
    console.error(error)

    errorMessage.value =
      error.message ||
      '趋势分析服务暂时不可用'

  } finally {

    /*
      关键修复：
      先结束 loading，
      让模板里的图表 div 真正渲染出来。
    */

    loading.value = false
  }


  /*
    loading 结束以后，
    等 Vue 更新 DOM，
    再初始化 ECharts。
  */

  if (!errorMessage.value) {
    await nextTick()

    /*
      再等一个浏览器渲染周期，
      确保图表容器已经有真实宽高。
    */

    requestAnimationFrame(() => {
      initCharts()
    })
  }
}


/* =========================================================
   浏览器尺寸变化
========================================================= */

const handleResize = () => {
  trendChart?.resize()
  skillChart?.resize()
  cityChart?.resize()
  salaryChart?.resize()
}


/* =========================================================
   生命周期
========================================================= */

onMounted(() => {
  loadTrendData()

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

  disposeCharts()
})
</script>


<template>
  <div class="trend-page">

    <!-- ===================================================
         页面标题
    ==================================================== -->

    <header class="page-header">

      <div>

        <h1>
          趋势分析
        </h1>

        <p>
          从岗位数量、热门技能、城市分布和薪资水平洞察就业市场变化
        </p>

      </div>


      <span class="page-badge">
        数据洞察
      </span>

    </header>


    <!-- ===================================================
         加载状态
    ==================================================== -->

    <div
      v-if="loading"
      class="status-card"
    >
      正在加载就业市场趋势数据...
    </div>


    <!-- ===================================================
         错误状态
    ==================================================== -->

    <div
      v-else-if="errorMessage"
      class="error-card"
    >

      <strong>
        数据加载失败
      </strong>

      <p>
        {{ errorMessage }}
      </p>

    </div>


    <!-- ===================================================
         正常页面
    ==================================================== -->

    <template v-else>

      <!-- =================================================
           顶部统计卡
      ================================================== -->

      <section class="summary-grid">

        <div class="summary-card">

          <p>
            岗位样本
          </p>

          <strong>
            {{
              summary.jobCount
                .toLocaleString()
            }}
          </strong>

          <span>
            当前知识库岗位数据
          </span>

        </div>


        <div class="summary-card">

          <p>
            覆盖城市
          </p>

          <strong>
            {{ summary.cityCount }}
          </strong>

          <span>
            招聘岗位城市覆盖
          </span>

        </div>


        <div class="summary-card">

          <p>
            技能标签
          </p>

          <strong>
            {{ summary.skillCount }}
          </strong>

          <span>
            已识别岗位技能种类
          </span>

        </div>


        <div class="summary-card">

          <p>
            平均薪资
          </p>

          <strong>
            ¥{{ summary.avgSalary }}K
          </strong>

          <span>
            岗位月薪平均水平
          </span>

        </div>

      </section>


      <!-- =================================================
           第一行图表
      ================================================== -->

      <section class="chart-grid">

        <!-- 岗位趋势 -->

        <div class="chart-card">

          <div class="chart-header">

            <div>

              <h2>
                岗位发布趋势
              </h2>

              <p>
                根据岗位发布日期统计月度岗位数量变化
              </p>

            </div>


            <span>
              月度趋势
            </span>

          </div>


          <div
            v-if="monthlyTrend.length"
            ref="trendChartRef"
            class="chart"
          ></div>


          <div
            v-else
            class="empty-chart"
          >
            当前数据暂无可用的岗位发布时间信息
          </div>

        </div>


        <!-- 技能排行 -->

        <div class="chart-card">

          <div class="chart-header">

            <div>

              <h2>
                热门技能 Top 10
              </h2>

              <p>
                当前岗位中出现频率最高的技术技能
              </p>

            </div>


            <span>
              技能需求
            </span>

          </div>


          <div
            v-if="topSkills.length"
            ref="skillChartRef"
            class="chart"
          ></div>


          <div
            v-else
            class="empty-chart"
          >
            当前暂无技能统计数据
          </div>

        </div>

      </section>


      <!-- =================================================
           第二行图表
      ================================================== -->

      <section class="chart-grid">

        <!-- 城市岗位数量 -->

        <div class="chart-card">

          <div class="chart-header">

            <div>

              <h2>
                城市岗位数量
              </h2>

              <p>
                对比主要城市的岗位供给规模
              </p>

            </div>


            <span>
              城市对比
            </span>

          </div>


          <div
            v-if="cityJobs.length"
            ref="cityChartRef"
            class="chart"
          ></div>


          <div
            v-else
            class="empty-chart"
          >
            当前暂无城市岗位数据
          </div>

        </div>


        <!-- 城市平均薪资 -->

        <div class="chart-card">

          <div class="chart-header">

            <div>

              <h2>
                城市平均薪资
              </h2>

              <p>
                对比主要城市岗位的平均薪资水平
              </p>

            </div>


            <span>
              K / 月
            </span>

          </div>


          <div
            v-if="citySalary.length"
            ref="salaryChartRef"
            class="chart"
          ></div>


          <div
            v-else
            class="empty-chart"
          >
            当前暂无城市薪资数据
          </div>

        </div>

      </section>


      <!-- =================================================
           技能需求排行榜
      ================================================== -->

      <section class="ranking-card">

        <div class="ranking-header">

          <div>

            <h2>
              技能需求排行榜
            </h2>

            <p>
              根据当前岗位知识库技能字段统计
            </p>

          </div>


          <span>
            Top {{ topSkills.length }}
          </span>

        </div>


        <div
          v-if="topSkills.length"
          class="ranking-list"
        >

          <div
            v-for="
              (skill, index)
              in topSkills
            "
            :key="skill.name"
            class="ranking-item"
          >

            <div
              class="rank-number"
              :class="{
                top:
                  index < 3
              }"
            >
              {{ index + 1 }}
            </div>


            <div class="skill-name">
              {{ skill.name }}
            </div>


            <div class="rank-bar-bg">

              <div
                class="rank-bar"
                :style="{
                  width:
                    (
                      topSkills[0]?.count
                        ? (
                            skill.count /
                            topSkills[0].count *
                            100
                          )
                        : 0
                    ) + '%'
                }"
              ></div>

            </div>


            <strong>
              {{ skill.count }}
            </strong>

            <span>
              个岗位
            </span>

          </div>

        </div>


        <div
          v-else
          class="ranking-empty"
        >
          当前暂无技能排行数据
        </div>

      </section>

    </template>

  </div>
</template>


<style scoped>

/* =========================================================
   基础
========================================================= */

* {
  box-sizing: border-box;
}


.trend-page {
  width: 100%;
}


/* =========================================================
   页面标题
========================================================= */

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
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
  line-height: 1.6;
}


.page-badge {
  flex-shrink: 0;
  padding: 8px 14px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
}


/* =========================================================
   顶部统计
========================================================= */

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}


.summary-card {
  min-width: 0;
  padding: 22px 24px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.summary-card p {
  margin: 0 0 10px;
  color: #6b7280;
  font-size: 14px;
}


.summary-card strong {
  display: block;
  color: #111827;
  font-size: 29px;
  font-weight: 650;
}


.summary-card span {
  display: block;
  margin-top: 8px;
  color: #9ca3af;
  font-size: 12px;
}


/* =========================================================
   图表 Grid
========================================================= */

.chart-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}


.chart-card {
  min-width: 0;
  padding: 22px;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.chart-header {
  min-height: 48px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}


.chart-header h2 {
  margin: 0 0 6px;
  color: #111827;
  font-size: 18px;
}


.chart-header p {
  margin: 0;
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.5;
}


.chart-header > span {
  flex-shrink: 0;
  padding: 5px 9px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
}


.chart {
  width: 100%;
  height: 310px;
}


.empty-chart {
  height: 310px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 13px;
}


/* =========================================================
   排行榜
========================================================= */

.ranking-card {
  padding: 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.ranking-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}


.ranking-header h2 {
  margin: 0 0 5px;
  color: #111827;
  font-size: 18px;
}


.ranking-header p {
  margin: 0;
  color: #9ca3af;
  font-size: 12px;
}


.ranking-header > span {
  padding: 5px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
}


.ranking-list {
  margin-top: 20px;
}


.ranking-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 14px 0;
}


.rank-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 7px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}


.rank-number.top {
  background: #eff6ff;
  color: #2563eb;
}


.skill-name {
  width: 120px;
  flex-shrink: 0;
  overflow: hidden;
  color: #374151;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}


.rank-bar-bg {
  flex: 1;
  height: 10px;
  overflow: hidden;
  background: #eef2f7;
  border-radius: 999px;
}


.rank-bar {
  height: 100%;
  background: #3b82f6;
  border-radius: 999px;
  transition: width 0.4s ease;
}


.ranking-item strong {
  min-width: 32px;
  color: #111827;
  text-align: right;
}


.ranking-item > span {
  width: 46px;
  flex-shrink: 0;
  color: #9ca3af;
  font-size: 11px;
}


.ranking-empty {
  padding: 40px;
  color: #9ca3af;
  text-align: center;
}


/* =========================================================
   加载 / 错误
========================================================= */

.status-card,
.error-card {
  padding: 20px;
  background: #ffffff;
  border-radius: 12px;
}


.status-card {
  border: 1px solid #e5e7eb;
  color: #6b7280;
}


.error-card {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}


.error-card strong {
  display: block;
  margin-bottom: 6px;
}


.error-card p {
  margin: 0;
}


/* =========================================================
   响应式
========================================================= */

@media (max-width: 1200px) {

  .summary-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

}


@media (max-width: 900px) {

  .chart-grid {
    grid-template-columns: 1fr;
  }

}


@media (max-width: 650px) {

  .summary-grid {
    grid-template-columns: 1fr;
  }


  .page-header {
    flex-direction: column;
  }


  .ranking-item {
    gap: 8px;
  }


  .skill-name {
    width: 80px;
  }


  .ranking-item > span {
    display: none;
  }

}
</style>