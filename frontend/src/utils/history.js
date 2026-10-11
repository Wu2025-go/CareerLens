// =========================================================
// CareerLens 历史记录工具
// frontend/src/utils/history.js
// =========================================================

const STORAGE_KEY = 'careerlens_history_v1'

const MAX_HISTORY_COUNT = 100


// =========================================================
// 安全解析 JSON
// =========================================================

const safeParse = (value, fallback = []) => {
  try {
    return JSON.parse(value)
  } catch (error) {
    console.error('历史记录解析失败：', error)
    return fallback
  }
}


// =========================================================
// 生成唯一 ID
// =========================================================

const createId = () => {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID()
  }

  return (
    `${Date.now()}-` +
    `${Math.random().toString(16).slice(2)}`
  )
}


// =========================================================
// 获取全部历史记录
// =========================================================

export const getHistoryRecords = () => {
  const raw =
    localStorage.getItem(
      STORAGE_KEY
    )

  if (!raw) {
    return []
  }

  const records =
    safeParse(raw, [])

  if (!Array.isArray(records)) {
    return []
  }

  return records.sort(
    (a, b) =>
      Number(b.createdAt || 0) -
      Number(a.createdAt || 0)
  )
}


// =========================================================
// 保存历史记录
// =========================================================

export const saveHistoryRecord = ({
  type,
  title,
  summary = '',
  detail = {},
  meta = {}
}) => {
  if (!type || !title) {
    return null
  }

  const records =
    getHistoryRecords()

  const now =
    Date.now()

  const record = {
    id: createId(),

    type,

    title,

    summary,

    detail,

    meta,

    createdAt: now,

    createdTime:
      new Date(now)
        .toLocaleString(
          'zh-CN',
          {
            hour12: false
          }
        )
  }

  records.unshift(record)

  const limitedRecords =
    records.slice(
      0,
      MAX_HISTORY_COUNT
    )

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(
      limitedRecords
    )
  )

  // 通知其他组件历史记录发生变化
  window.dispatchEvent(
    new CustomEvent(
      'careerlens-history-change'
    )
  )

  return record
}


// =========================================================
// 删除单条历史记录
// =========================================================

export const deleteHistoryRecord = (
  id
) => {
  const records =
    getHistoryRecords()
      .filter(
        item =>
          item.id !== id
      )

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(records)
  )

  window.dispatchEvent(
    new CustomEvent(
      'careerlens-history-change'
    )
  )
}


// =========================================================
// 清空历史记录
// =========================================================

export const clearHistoryRecords = () => {
  localStorage.removeItem(
    STORAGE_KEY
  )

  window.dispatchEvent(
    new CustomEvent(
      'careerlens-history-change'
    )
  )
}


// =========================================================
// 按类型获取
// =========================================================

export const getHistoryByType = (
  type
) => {
  if (!type || type === 'all') {
    return getHistoryRecords()
  }

  return getHistoryRecords()
    .filter(
      item =>
        item.type === type
    )
}


// =========================================================
// 类型显示名称
// =========================================================

export const HISTORY_TYPE_LABELS = {
  ask: 'AI 问答',
  skill: '技能测评',
  recommend: '岗位推荐'
}


// =========================================================
// 类型图标
// =========================================================

export const HISTORY_TYPE_ICONS = {
  ask: 'AI',
  skill: '技',
  recommend: '岗'
}