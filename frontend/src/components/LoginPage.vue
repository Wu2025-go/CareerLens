<script setup>
import { onMounted, reactive, ref } from 'vue'
import { authRequest, loginAccount } from '../utils/auth.js'

const emit = defineEmits(['authenticated', 'guest'])
const mode = ref('login')
const username = ref('')
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const checking = ref(true)
const available = ref(false)
const error = ref('')
const success = ref('')
const serviceMessage = ref('')
const stats = reactive({ jobs: '--', skills: '--', cities: '--' })

const checkService = async () => {
  checking.value = true
  try {
    const result = await authRequest('status')
    available.value = Boolean(result.available)
    serviceMessage.value = result.message || ''
  } catch (err) {
    available.value = false
    serviceMessage.value = err.message
  } finally {
    checking.value = false
  }
}

const changeMode = (value) => {
  mode.value = value
  password.value = ''
  confirmation.value = ''
  error.value = ''
  success.value = ''
}

const submit = async () => {
  if (busy.value || !available.value) return
  error.value = ''
  success.value = ''
  const account = username.value.trim()
  if (!/^[A-Za-z0-9]{6,20}$/.test(account)) {
    error.value = '账号须为6至20位字母或数字。'
    return
  }
  if (password.value.length < 8 || password.value.length > 128 || !password.value.trim()) {
    error.value = '密码须为8至128个字符，且不能全部为空白。'
    return
  }
  if (mode.value === 'register' && password.value !== confirmation.value) {
    error.value = '两次输入的密码不一致。'
    return
  }
  busy.value = true
  try {
    if (mode.value === 'register') {
      const result = await authRequest('register', {
        method: 'POST', data: { username: account, password: password.value }
      })
      username.value = result.user.username
      changeMode('login')
      success.value = '注册成功，请使用刚才的账号和密码登录。'
    } else {
      await loginAccount(account, password.value)
      password.value = ''
      emit('authenticated')
    }
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  checkService()
  // 直接读取现有数据统计，不把技能数或城市数写成企业合作数、行业数。
  fetch('/api/trends').then(async (response) => {
    if (!response.ok) return
    const { summary } = await response.json()
    for (const [key, field] of [['jobs', 'job_count'], ['skills', 'skill_count'], ['cities', 'city_count']]) {
      const value = summary?.[field]
      if (Number.isFinite(value)) stats[key] = value.toLocaleString('zh-CN')
    }
  }).catch(() => { /* 统计加载失败不影响登录；保持 --。 */ })
})
</script>

<template>
  <div class="login">
    <aside class="login-hero">
      <svg class="hero-lines" viewBox="0 0 600 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <circle cx="520" cy="120" r="170" fill="none" stroke="rgba(255,255,255,0.14)" stroke-width="1.5" />
        <circle cx="520" cy="120" r="250" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1.5" />
        <path d="M-40 640 Q 220 540 460 700 T 760 660" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1.5" />
        <path d="M-40 700 Q 220 600 460 760 T 760 720" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1.5" />
        <line x1="60" y1="-20" x2="60" y2="820" stroke="rgba(255,255,255,0.10)" stroke-width="1.5" />
      </svg>
      <div class="hero-content">
        <a class="hero-brand" href="/" @click.prevent="!busy && emit('guest')">
          <img class="hero-logo" src="/career-logo.jpg" alt="CareerLens 职见" />
          <div class="hero-brand-text">
            <h1>CareerLens</h1>
            <p>职见 · 大学生就业数据分析平台</p>
          </div>
        </a>
        <div class="hero-intro">
          <h2>用数据看清<br />你的就业方向</h2>
          <p>基于岗位证据的就业问答、技能测评与岗位推荐，帮助你了解就业方向和学习重点。</p>
          <div class="hero-stats" aria-label="当前岗位样本统计">
            <div><strong>{{ stats.jobs }}</strong><span>岗位样本</span></div>
            <div><strong>{{ stats.skills }}</strong><span>技能标签</span></div>
            <div><strong>{{ stats.cities }}</strong><span>覆盖城市</span></div>
          </div>
        </div>
      </div>
    </aside>

    <main class="login-panel">
      <div class="login-card">
        <h2 class="form-title">{{ mode === 'login' ? '欢迎回来' : '创建你的账号' }}</h2>
        <p class="form-intro">{{ mode === 'login' ? '登录 CareerLens，继续探索就业方向。' : '注册后，使用账号和密码登录。' }}</p>
        <div class="tabs" aria-label="选择账号操作">
          <button type="button" class="tab" :class="{ active: mode === 'login' }" :aria-pressed="mode === 'login'" :disabled="busy" @click="changeMode('login')">账号登录</button>
          <button type="button" class="tab" :class="{ active: mode === 'register' }" :aria-pressed="mode === 'register'" :disabled="busy" @click="changeMode('register')">注册</button>
        </div>

        <div v-if="checking" class="service-notice" role="status">正在连接账号服务…</div>
        <div v-else-if="!available" class="service-notice" role="status">
          <p>{{ serviceMessage || '账号服务暂不可用，请稍后重试。' }}</p>
          <button type="button" class="retry-button" @click="checkService">重新连接</button>
        </div>
        <p v-if="success" class="success" role="status">{{ success }}</p>

        <form class="form" @submit.prevent="submit">
          <label class="field" for="account-username">
            <span>账号</span>
            <input id="account-username" v-model="username" name="username" type="text" placeholder="6–20位字母或数字" autocomplete="username" autocapitalize="none" spellcheck="false" minlength="6" maxlength="20" pattern="[A-Za-z0-9]{6,20}" required :disabled="busy" aria-describedby="account-help account-error" />
          </label>
          <p id="account-help" class="field-help">账号不区分字母大小写。</p>
          <label class="field" for="account-password">
            <span>{{ mode === 'login' ? '密码' : '设置密码' }}</span>
            <input id="account-password" v-model="password" name="password" type="password" placeholder="8–128个字符" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="8" maxlength="128" required :disabled="busy" aria-describedby="account-error" />
          </label>
          <label v-if="mode === 'register'" class="field" for="account-confirmation">
            <span>确认密码</span>
            <input id="account-confirmation" v-model="confirmation" name="confirmation" type="password" placeholder="再次输入密码" autocomplete="new-password" minlength="8" maxlength="128" required :disabled="busy" aria-describedby="account-error" />
          </label>
          <p v-if="error" id="account-error" class="field-error" role="alert">{{ error }}</p>
          <button class="submit-btn" type="submit" :disabled="busy || checking || !available" :aria-busy="busy">
            {{ busy ? '正在提交…' : mode === 'login' ? '登录' : '注册' }}
          </button>
        </form>
        <p class="storage-hint">使用记录保存在当前浏览器，按账号区分，暂不支持跨设备同步。</p>
        <button type="button" class="guest-button" :disabled="busy" @click="emit('guest')">先逛逛，进入平台 <span aria-hidden="true">→</span></button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login { display: flex; width: 100%; min-height: 100vh; background: var(--bg); }
.login-hero { position: relative; width: 46%; min-width: 360px; overflow: hidden; padding: 56px 52px; background: linear-gradient(150deg, #185fa5 0%, #378add 100%); color: white; }
.hero-lines { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.hero-content { position: relative; z-index: 1; display: flex; flex-direction: column; height: 100%; min-height: calc(100vh - 112px); }
.hero-brand { display: flex; align-items: center; gap: 14px; color: inherit; text-decoration: none; }
.hero-logo { width: 56px; height: 56px; flex-shrink: 0; border-radius: 14px; background: white; object-fit: contain; box-shadow: 0 4px 14px rgba(9,47,84,.25); }
.hero-brand-text h1 { margin: 0; font-size: 22px; letter-spacing: .4px; }
.hero-brand-text p { margin: 3px 0 0; font-size: 13px; color: rgba(255,255,255,.82); }
.hero-intro { margin: auto 0; padding: 64px 0; }
.hero-intro h2 { margin: 0 0 18px; font-size: 38px; line-height: 1.3; font-weight: 700; letter-spacing: .5px; }
.hero-intro > p { margin: 0 0 36px; max-width: 360px; font-size: 15px; line-height: 1.8; color: rgba(255,255,255,.88); }
.hero-stats { display: flex; flex-wrap: wrap; gap: 26px 36px; }
.hero-stats > div { display: flex; flex-direction: column; }
.hero-stats strong { font-size: 30px; font-weight: 700; }
.hero-stats span { margin-top: 4px; font-size: 13px; color: rgba(255,255,255,.78); }
.login-panel { flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center; padding: 40px; }
.login-card { width: 100%; max-width: 380px; }
.form-title { margin: 0 0 10px; font-size: 28px; }
.form-intro { margin: 0 0 28px; color: var(--text-2); line-height: 1.7; font-size: 14px; }
.tabs { display: flex; gap: 8px; margin-bottom: 28px; }
.tab { flex: 1; padding: 12px 0; border: 0; border-radius: 11px; background: transparent; color: var(--text-2); font-size: 15px; font-weight: 600; }
.tab.active { background: linear-gradient(135deg, #185fa5, #378add); color: white; box-shadow: 0 6px 18px rgba(24,95,165,.25); }
.form { display: flex; flex-direction: column; }
.field { display: flex; flex-direction: column; margin-bottom: 16px; }
.field > span { margin-bottom: 8px; color: var(--text-2); font-size: 13.5px; font-weight: 600; }
.field input { width: 100%; height: 46px; padding: 0 16px; border: 1px solid var(--border); border-radius: 12px; background: white; color: var(--text); font-size: 14.5px; font-family: inherit; }
.field input:focus { outline: 2px solid #378add; outline-offset: 2px; }
.field-help { margin: -8px 0 16px; font-size: 12px; color: var(--text-2); }
.field-error { margin: 0 0 12px; color: #b91c1c; font-size: 13px; line-height: 1.6; }
.submit-btn { height: 48px; margin-top: 8px; border: 0; border-radius: 12px; background: linear-gradient(135deg, #185fa5, #378add); color: white; font-size: 15.5px; font-weight: 600; box-shadow: 0 8px 22px rgba(24,95,165,.28); }
.submit-btn:disabled, .tab:disabled, .guest-button:disabled { cursor: wait; opacity: .6; }
.success { margin: 0 0 20px; padding: 12px 16px; border-radius: 10px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #047857; font-size: 14px; line-height: 1.6; }
.service-notice { margin: 0 0 20px; padding: 12px 14px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 10px; color: #9a3412; font-size: 13px; line-height: 1.6; }
.service-notice p { margin: 0 0 8px; }
.retry-button { border: 0; background: transparent; color: #9a3412; font-size: 13px; padding: 0; text-decoration: underline; }
.storage-hint { margin: 18px 0 8px; color: var(--text-2); font-size: 12px; line-height: 1.7; }
.guest-button { display: block; margin: 12px auto 0; padding: 10px; background: transparent; border: 0; color: #185fa5; font-size: 14px; }
button:focus-visible, a:focus-visible { outline: 3px solid #0e7490; outline-offset: 4px; }
@media (max-width: 860px) {
  .login { flex-direction: column; }
  .login-hero { width: 100%; min-width: 0; padding: 32px 24px; }
  .hero-content { min-height: auto; }
  .hero-intro { padding: 32px 0 0; }
  .hero-intro h2 { font-size: 29px; margin-bottom: 12px; }
  .hero-intro > p { margin-bottom: 24px; }
  .hero-stats { gap: 24px; }
  .hero-stats strong { font-size: 26px; }
  .login-panel { padding: 32px 24px; }
  .form-title { font-size: 25px; }
}
</style>
