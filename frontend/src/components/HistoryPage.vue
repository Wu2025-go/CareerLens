<script setup>
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref
} from 'vue'

import {
  clearHistoryRecords,
  deleteHistoryRecord,
  getHistoryRecords,
  HISTORY_TYPE_ICONS,
  HISTORY_TYPE_LABELS
} from '../utils/history'


/* =========================================================
   数据
========================================================= */

const records = ref([])

const activeFilter =
  ref('all')

const keyword =
  ref('')

const expandedId =
  ref(null)


/* =========================================================
   筛选项
========================================================= */

const filters = [
  {
    value: 'all',
    label: '全部记录'
  },
  {
    value: 'ask',
    label: 'AI 问答'
  },
  {
    value: 'skill',
    label: '技能测评'
  },
  {
    value: 'recommend',
    label: '岗位推荐'
  }
]


/* =========================================================
   加载
========================================================= */

const loadRecords = () => {
  records.value =
    getHistoryRecords()
}


/* =========================================================
   筛选
========================================================= */

const filteredRecords =
  computed(() => {

    let result =
      records.value

    if (
      activeFilter.value !==
      'all'
    ) {
      result =
        result.filter(
          item =>
            item.type ===
            activeFilter.value
        )
    }

    const searchKeyword =
      keyword.value
        .trim()
        .toLowerCase()

    if (searchKeyword) {
      result =
        result.filter(
          item => {

            const searchable =
              [
                item.title,
                item.summary,
                JSON.stringify(
                  item.detail || {}
                )
              ]
                .join(' ')
                .toLowerCase()

            return searchable.includes(
              searchKeyword
            )
          }
        )
    }

    return result
  })


/* =========================================================
   数量统计
========================================================= */

const askCount =
  computed(
    () =>
      records.value.filter(
        item =>
          item.type === 'ask'
      ).length
  )


const skillCount =
  computed(
    () =>
      records.value.filter(
        item =>
          item.type === 'skill'
      ).length
  )


const recommendCount =
  computed(
    () =>
      records.value.filter(
        item =>
          item.type ===
          'recommend'
      ).length
  )


/* =========================================================
   展开详情
========================================================= */

const toggleDetail = (
  id
) => {
  expandedId.value =
    expandedId.value === id
      ? null
      : id
}


/* =========================================================
   删除
========================================================= */

const removeRecord = (
  id
) => {
  const confirmed =
    window.confirm(
      '确定删除这条历史记录吗？'
    )

  if (!confirmed) {
    return
  }

  deleteHistoryRecord(id)

  loadRecords()

  if (
    expandedId.value === id
  ) {
    expandedId.value = null
  }
}


/* =========================================================
   清空
========================================================= */

const clearAll = () => {
  if (!records.value.length) {
    return
  }

  const confirmed =
    window.confirm(
      '确定清空全部历史记录吗？此操作无法恢复。'
    )

  if (!confirmed) {
    return
  }

  clearHistoryRecords()

  loadRecords()

  expandedId.value = null
}


/* =========================================================
   类型
========================================================= */

const getTypeLabel = (
  type
) => {
  return (
    HISTORY_TYPE_LABELS[type] ||
    '操作记录'
  )
}


const getTypeIcon = (
  type
) => {
  return (
    HISTORY_TYPE_ICONS[type] ||
    '记'
  )
}


/* =========================================================
   时间
========================================================= */

const formatTime = (
  record
) => {
  if (record.createdTime) {
    return record.createdTime
  }

  if (!record.createdAt) {
    return '--'
  }

  return new Date(
    record.createdAt
  ).toLocaleString(
    'zh-CN',
    {
      hour12: false
    }
  )
}


/* =========================================================
   详情展示辅助
========================================================= */

const formatValue = (
  value
) => {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return '暂无'
  }

  if (Array.isArray(value)) {
    return value.length
      ? value.join('、')
      : '暂无'
  }

  if (
    typeof value ===
    'object'
  ) {
    return JSON.stringify(
      value,
      null,
      2
    )
  }

  return String(value)
}


/* =========================================================
   生命周期
========================================================= */

onMounted(() => {
  loadRecords()

  window.addEventListener(
    'careerlens-history-change',
    loadRecords
  )

  window.addEventListener(
    'storage',
    loadRecords
  )
})


onBeforeUnmount(() => {
  window.removeEventListener(
    'careerlens-history-change',
    loadRecords
  )

  window.removeEventListener(
    'storage',
    loadRecords
  )
})
</script>


<template>
  <div class="history-page">

    <!-- ===================================================
         标题
    ==================================================== -->

    <header class="page-header">

      <div>

        <h1>
          历史记录
        </h1>

        <p>
          统一查看 AI 问答、技能测评和岗位推荐的使用记录
        </p>

      </div>


      <span class="page-badge">
        我的记录
      </span>

    </header>


    <!-- ===================================================
         概览
    ==================================================== -->

    <section class="summary-grid">

      <div class="summary-card">

        <p>
          全部记录
        </p>

        <strong>
          {{ records.length }}
        </strong>

        <span>
          当前浏览器已保存记录
        </span>

      </div>


      <div class="summary-card">

        <p>
          AI 问答
        </p>

        <strong>
          {{ askCount }}
        </strong>

        <span>
          就业知识问答记录
        </span>

      </div>


      <div class="summary-card">

        <p>
          技能测评
        </p>

        <strong>
          {{ skillCount }}
        </strong>

        <span>
          个人技能匹配记录
        </span>

      </div>


      <div class="summary-card">

        <p>
          岗位推荐
        </p>

        <strong>
          {{ recommendCount }}
        </strong>

        <span>
          智能岗位推荐记录
        </span>

      </div>

    </section>


    <!-- ===================================================
         工具栏
    ==================================================== -->

    <section class="toolbar">

      <div class="filter-list">

        <button
          v-for="filter in filters"
          :key="filter.value"
          class="filter-button"
          :class="{
            active:
              activeFilter ===
              filter.value
          }"
          @click="
            activeFilter =
              filter.value
          "
        >
          {{ filter.label }}
        </button>

      </div>


      <div class="toolbar-right">

        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索历史记录..."
        />


        <button
          class="clear-button"
          :disabled="
            records.length === 0
          "
          @click="clearAll"
        >
          清空全部
        </button>

      </div>

    </section>


    <!-- ===================================================
         无历史记录
    ==================================================== -->

    <section
      v-if="
        filteredRecords.length === 0
      "
      class="empty-card"
    >

      <div class="empty-icon">
        ⏱
      </div>

      <h2>
        {{
          records.length
            ? '没有找到符合条件的记录'
            : '暂时还没有历史记录'
        }}
      </h2>

      <p>
        {{
          records.length
            ? '可以尝试更换筛选类型或搜索关键词。'
            : '完成 AI 问答、技能测评或岗位推荐后，记录会显示在这里。'
        }}
      </p>

    </section>


    <!-- ===================================================
         历史记录
    ==================================================== -->

    <section
      v-else
      class="history-list"
    >

      <article
        v-for="
          record in
          filteredRecords
        "
        :key="record.id"
        class="history-card"
      >

        <!-- 顶部 -->

        <div class="record-main">

          <div
            class="record-icon"
            :class="
              `type-${record.type}`
            "
          >
            {{
              getTypeIcon(
                record.type
              )
            }}
          </div>


          <div class="record-content">

            <div class="record-heading">

              <div>

                <div class="record-type">
                  {{
                    getTypeLabel(
                      record.type
                    )
                  }}
                </div>

                <h3>
                  {{ record.title }}
                </h3>

              </div>


              <span class="record-time">
                {{
                  formatTime(
                    record
                  )
                }}
              </span>

            </div>


            <p
              v-if="record.summary"
              class="record-summary"
            >
              {{ record.summary }}
            </p>


            <!-- 元数据 -->

            <div
              v-if="
                record.meta &&
                Object.keys(
                  record.meta
                ).length
              "
              class="meta-list"
            >

              <span
                v-for="
                  (
                    value,
                    key
                  ) in record.meta
                "
                :key="key"
              >
                {{ key }}：
                {{
                  formatValue(
                    value
                  )
                }}
              </span>

            </div>

          </div>

        </div>


        <!-- 操作 -->

        <div class="record-actions">

          <button
            class="detail-button"
            @click="
              toggleDetail(
                record.id
              )
            "
          >
            {{
              expandedId ===
              record.id
                ? '收起详情'
                : '查看详情'
            }}
          </button>


          <button
            class="delete-button"
            @click="
              removeRecord(
                record.id
              )
            "
          >
            删除
          </button>

        </div>


        <!-- 详情 -->

        <div
          v-if="
            expandedId ===
            record.id
          "
          class="detail-panel"
        >

          <div
            v-if="
              record.detail &&
              Object.keys(
                record.detail
              ).length
            "
            class="detail-grid"
          >

            <div
              v-for="
                (
                  value,
                  key
                ) in record.detail
              "
              :key="key"
              class="detail-item"
            >

              <span>
                {{ key }}
              </span>

              <strong>
                {{
                  formatValue(
                    value
                  )
                }}
              </strong>

            </div>

          </div>


          <div
            v-else
            class="no-detail"
          >
            暂无更多详情
          </div>

        </div>

      </article>

    </section>

  </div>
</template>


<style scoped>

* {
  box-sizing: border-box;
}


.history-page {
  width: 100%;
}


/* =========================================================
   标题
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
}


.page-badge {
  padding: 8px 14px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
}


/* =========================================================
   概览
========================================================= */

.summary-grid {
  display: grid;
  grid-template-columns:
    repeat(
      4,
      minmax(0, 1fr)
    );
  gap: 16px;
  margin-bottom: 20px;
}


.summary-card {
  padding: 21px 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.summary-card p {
  margin: 0 0 10px;
  color: #6b7280;
  font-size: 13px;
}


.summary-card strong {
  display: block;
  color: #111827;
  font-size: 28px;
}


.summary-card span {
  display: block;
  margin-top: 7px;
  color: #9ca3af;
  font-size: 11px;
}


/* =========================================================
   工具栏
========================================================= */

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding: 15px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 13px;
}


.filter-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}


.filter-button {
  padding: 8px 13px;
  border: none;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
  cursor: pointer;
}


.filter-button:hover {
  color: #2563eb;
}


.filter-button.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}


.toolbar-right {
  display: flex;
  gap: 10px;
}


.search-input {
  width: 220px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #dbe1ea;
  border-radius: 8px;
  outline: none;
}


.search-input:focus {
  border-color: #60a5fa;
}


.clear-button {
  height: 38px;
  padding: 0 14px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff;
  color: #dc2626;
  cursor: pointer;
}


.clear-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}


/* =========================================================
   历史列表
========================================================= */

.history-list {
  display: grid;
  gap: 13px;
}


.history-card {
  padding: 20px 22px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
}


.record-main {
  display: flex;
  align-items: flex-start;
  gap: 15px;
}


.record-icon {
  width: 45px;
  height: 45px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
}


.record-icon.type-ask {
  background: #eff6ff;
  color: #2563eb;
}


.record-icon.type-skill {
  background: #ecfdf5;
  color: #059669;
}


.record-icon.type-recommend {
  background: #fff7ed;
  color: #ea580c;
}


.record-content {
  flex: 1;
  min-width: 0;
}


.record-heading {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}


.record-type {
  margin-bottom: 5px;
  color: #9ca3af;
  font-size: 11px;
}


.record-heading h3 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}


.record-time {
  flex-shrink: 0;
  color: #9ca3af;
  font-size: 12px;
}


.record-summary {
  margin: 10px 0 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}


.meta-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}


.meta-list span {
  padding: 5px 8px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
}


/* =========================================================
   操作
========================================================= */

.record-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}


.detail-button,
.delete-button {
  padding: 7px 11px;
  border-radius: 7px;
  background: white;
  cursor: pointer;
}


.detail-button {
  border: 1px solid #bfdbfe;
  color: #2563eb;
}


.delete-button {
  border: 1px solid #e5e7eb;
  color: #9ca3af;
}


.delete-button:hover {
  border-color: #fecaca;
  color: #dc2626;
}


/* =========================================================
   详情
========================================================= */

.detail-panel {
  margin-top: 16px;
  padding: 16px;
  border-radius: 10px;
  background: #f8fafc;
}


.detail-grid {
  display: grid;
  grid-template-columns:
    repeat(
      2,
      minmax(0, 1fr)
    );
  gap: 12px;
}


.detail-item {
  min-width: 0;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #eef2f7;
  border-radius: 8px;
}


.detail-item > span {
  display: block;
  margin-bottom: 6px;
  color: #9ca3af;
  font-size: 11px;
}


.detail-item > strong {
  display: block;
  overflow-wrap: anywhere;
  color: #374151;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
  white-space: pre-wrap;
}


.no-detail {
  color: #9ca3af;
  font-size: 12px;
  text-align: center;
}


/* =========================================================
   空状态
========================================================= */

.empty-card {
  min-height: 390px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 15px;
  text-align: center;
}


.empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
  border-radius: 18px;
  background: #eff6ff;
  font-size: 28px;
}


.empty-card h2 {
  margin: 0 0 9px;
  color: #111827;
  font-size: 19px;
}


.empty-card p {
  max-width: 460px;
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
  line-height: 1.7;
}


/* =========================================================
   响应式
========================================================= */

@media (max-width: 1100px) {

  .summary-grid {
    grid-template-columns:
      repeat(2, 1fr);
  }

}


@media (max-width: 800px) {

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }


  .toolbar-right {
    flex-direction: column;
  }


  .search-input {
    width: 100%;
  }


  .detail-grid {
    grid-template-columns: 1fr;
  }


  .record-heading {
    flex-direction: column;
    gap: 5px;
  }

}


@media (max-width: 600px) {

  .summary-grid {
    grid-template-columns: 1fr;
  }


  .page-header {
    flex-direction: column;
  }

}
</style>