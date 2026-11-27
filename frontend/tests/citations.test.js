import test from 'node:test'
import assert from 'node:assert/strict'
import { citationLinks } from '../src/utils/citations.js'

test('different excerpts of the same job produce one text link and retain both quotes', () => {
  const source = Object.freeze([
    Object.freeze({ job_id: 'JOB_0622', quote: '配合运维完成服务部署' }),
    Object.freeze({ job_id: 'JOB_0622', quote: 'Java、Netty' }),
    Object.freeze({ job_id: 'JOB_0053', quote: '参与单元测试' }),
  ])
  assert.deepEqual(citationLinks(source), [
    { job_id: 'JOB_0622', quotes: ['配合运维完成服务部署', 'Java、Netty'] },
    { job_id: 'JOB_0053', quotes: ['参与单元测试'] },
  ])
  assert.equal(source.length, 3)
})

test('repeated excerpts are deduplicated within a link tooltip', () => {
  assert.deepEqual(citationLinks([{ job_id: 'JOB_0053', quote: '单元测试' },
    { job_id: 'JOB_0053', quote: '单元测试' }]), [{ job_id: 'JOB_0053', quotes: ['单元测试'] }])
})

test('missing citations do not break answer rendering', () => {
  assert.deepEqual(citationLinks(null), [])
  assert.deepEqual(citationLinks([null, {}, { job_id: '' }]), [])
})
