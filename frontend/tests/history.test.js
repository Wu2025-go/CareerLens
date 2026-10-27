import test from 'node:test'
import assert from 'node:assert/strict'
import { clearHistoryRecords, deleteHistoryRecord, getHistoryRecords, saveHistoryRecord, setHistoryUser } from '../src/utils/history.js'

const values = new Map()
globalThis.localStorage = {
  getItem: key => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: key => values.delete(key)
}
globalThis.window = { dispatchEvent() {} }
globalThis.CustomEvent = class { constructor(type) { this.type = type } }
const userA = '11111111-1111-4111-8111-111111111111'
const userB = '22222222-2222-4222-8222-222222222222'
const save = title => saveHistoryRecord({ type: 'ask', title })
const reset = () => { values.clear(); setHistoryUser(null) }

test('guest and two account histories stay separate after account switches', () => {
  reset()
  save('guest question')
  setHistoryUser(userA)
  assert.equal(getHistoryRecords().length, 0)
  save('account A question')
  setHistoryUser(userB)
  assert.equal(getHistoryRecords().length, 0)
  save('account B question')
  setHistoryUser(userA)
  assert.equal(getHistoryRecords()[0].title, 'account A question')
  setHistoryUser(null)
  assert.equal(getHistoryRecords()[0].title, 'guest question')
})

test('deleting or clearing an account history leaves other accounts and guest intact', () => {
  reset()
  save('guest')
  setHistoryUser(userA)
  const record = save('A')
  setHistoryUser(userB)
  save('B')
  setHistoryUser(userA)
  deleteHistoryRecord(record.id)
  assert.equal(getHistoryRecords().length, 0)
  setHistoryUser(userB)
  clearHistoryRecords()
  setHistoryUser(null)
  assert.equal(getHistoryRecords()[0].title, 'guest')
})

test('legacy guest key remains usable and history still has a 100 record limit', () => {
  reset()
  values.set('careerlens_history_v1', JSON.stringify([{ id: 'old', type: 'ask', title: 'old guest', createdAt: 1 }]))
  assert.equal(getHistoryRecords()[0].title, 'old guest')
  setHistoryUser(userA)
  for (let i = 0; i < 105; i++) save(`question ${i}`)
  assert.equal(getHistoryRecords().length, 100)
  setHistoryUser(null)
  assert.equal(getHistoryRecords()[0].title, 'old guest')
})
