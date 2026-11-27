import test from 'node:test'
import assert from 'node:assert/strict'
import { datasetScope, datasetUrl } from '../src/utils/dataset.js'
import { buildAskPayload, buildGoal, createGoal, postJobGoal, splitEnteredSkills } from '../src/utils/jobGoal.js'

test.afterEach(() => { datasetScope.value = 'real' })

test('ordinary questions, confirmed goals and POST requests carry the selected scope', async () => {
  const saved = globalThis.fetch
  try {
    for (const scope of ['real', 'synthetic', 'all']) {
      datasetScope.value = scope
      const goal = buildGoal(createGoal({ city: '杭州', job_category: '内容运营' }), ['SEO'])
      assert.equal(goal.dataset_scope, scope)
      assert.equal(buildAskPayload('平均薪资是多少？').dataset_scope, scope)
      assert.deepEqual(buildAskPayload('需要哪些技能？', goal).goal, goal)
      let body
      globalThis.fetch = async (_url, options) => {
        body = JSON.parse(options.body)
        return { ok: true, json: async () => ({ success: true }) }
      }
      await postJobGoal('/api/ask', buildAskPayload('平均薪资是多少？'))
      assert.equal(body.dataset_scope, scope)
      assert.equal(body.question, '平均薪资是多少？')
    }
  } finally { globalThis.fetch = saved }
})

test('trend URLs retain filters and never serialize skill arrays or stale source scope', () => {
  datasetScope.value = 'synthetic'
  const url = datasetUrl('/api/trends', { city: '北京', job_category: '数据分析', min_salary: 0,
    skills: ['Excel'], dataset_scope: 'real', expand_city: true, keyword: '' })
  const params = new URL(url, 'http://localhost').searchParams
  assert.equal(params.get('dataset_scope'), 'synthetic')
  assert.equal(params.get('city'), '北京')
  assert.equal(params.get('min_salary'), '0')
  assert.equal(params.has('skills'), false)
  assert.equal(params.has('expand_city'), false)
})

test('skill entry preserves slashes and programming punctuation', () => {
  assert.deepEqual(splitEnteredSkills('A/B测试，TCP/IP;CI/CD、C++|C#\n.NET'),
    ['A/B测试', 'TCP/IP', 'CI/CD', 'C++', 'C#', '.NET'])
})

test('invalid salary is rejected before sending and an explicit zero is retained', () => {
  assert.throws(() => buildGoal(createGoal({ min_salary: -1 }), []))
  assert.throws(() => buildGoal(createGoal({ min_salary: 'infinity' }), []))
  assert.equal(buildGoal(createGoal({ min_salary: 0 }), []).min_salary, 0)
})
