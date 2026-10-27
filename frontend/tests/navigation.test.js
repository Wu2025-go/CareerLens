import test from 'node:test'
import assert from 'node:assert/strict'
import { pageFromPath } from '../src/utils/navigation.js'

test('deep links select the intended page', () => {
  for (const [path, page] of Object.entries({
    '/': 'dashboard', '/ask': 'ask', '/skills': 'skills',
    '/recommend': 'recommend', '/trends': 'trends', '/history': 'history', '/login': 'login'
  })) assert.equal(pageFromPath(path), page)
})

test('trailing slash, query, and fragment preserve page selection', () => {
  assert.equal(pageFromPath('/ask/'), 'ask')
  assert.equal(pageFromPath('/recommend?city=广州'), 'recommend')
  assert.equal(pageFromPath('/history#latest'), 'history')
})

test('unknown and prototype-like paths show the missing-page view', () => {
  for (const path of ['/unknown', '/api/missing', '/constructor', '/toString']) {
    assert.equal(pageFromPath(path), 'not-found')
  }
})
