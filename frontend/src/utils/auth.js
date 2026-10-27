import { reactive } from 'vue'
import { setHistoryUser } from './history.js'

export const authState = reactive({ user: null, ready: false, error: '' })

// 密码与会话令牌不写入 localStorage；会话由 HttpOnly Cookie 交给浏览器管理。
const useUser = (user) => {
  authState.user = user || null
  setHistoryUser(user?.id || null)
}

export const authRequest = async (path, { method = 'GET', data } = {}) => {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 20_000)
  try {
    const response = await fetch(`/api/auth/${path}`, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        ...(data ? { 'Content-Type': 'application/json' } : {}),
        ...(method === 'POST' ? { 'X-CareerLens-Client': 'browser' } : {})
      },
      body: data ? JSON.stringify(data) : undefined,
      signal: controller.signal
    })
    let result
    try { result = await response.json() } catch { throw new Error('账号服务响应异常，请稍后重试。') }
    if (!response.ok) {
      throw new Error(typeof result.detail === 'string' ? result.detail : '账号操作失败，请检查输入后重试。')
    }
    return result
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('账号服务响应较慢，请稍后重试。')
    if (error instanceof TypeError) throw new Error('无法连接账号服务，请检查网络。')
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

export const restoreSession = async () => {
  authState.error = ''
  try {
    const result = await authRequest('me')
    useUser(result.authenticated ? result.user : null)
  } catch (error) {
    useUser(null)
    authState.error = error.message
  } finally {
    authState.ready = true
  }
}

export const loginAccount = async (username, password) => {
  const result = await authRequest('login', { method: 'POST', data: { username, password } })
  if (!result.authenticated || !result.user?.id) throw new Error('登录状态无效，请重试。')
  authState.error = ''
  authState.ready = true
  useUser(result.user)
}

export const logoutAccount = async () => {
  await authRequest('logout', { method: 'POST' })
  useUser(null)
  authState.error = ''
}
