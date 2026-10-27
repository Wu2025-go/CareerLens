import { onBeforeUnmount, onMounted, ref } from 'vue'

export const PAGE_PATHS = Object.freeze({
  dashboard: '/',
  ask: '/ask',
  skills: '/skills',
  recommend: '/recommend',
  trends: '/trends',
  history: '/history',
  login: '/login'
})

const PATH_PAGES = Object.fromEntries(
  Object.entries(PAGE_PATHS).map(([page, path]) => [path, page])
)

export const pageFromPath = (path) => {
  const normalized = String(path || '/').split(/[?#]/, 1)[0].replace(/\/+$/, '') || '/'
  return Object.hasOwn(PATH_PAGES, normalized) ? PATH_PAGES[normalized] : 'not-found'
}

// 页面初次加载、刷新、前进/后退和侧栏导航共用同一份路由表。
export const usePageNavigation = () => {
  const activePage = ref(pageFromPath(window.location.pathname))
  const syncPage = () => {
    activePage.value = pageFromPath(window.location.pathname)
  }
  const setPage = (page) => {
    if (!Object.hasOwn(PAGE_PATHS, page)) return
    const path = PAGE_PATHS[page]
    if (window.location.pathname !== path) window.history.pushState({}, '', path)
    activePage.value = page
  }
  const navigate = (event, page) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    setPage(page)
  }
  onMounted(() => window.addEventListener('popstate', syncPage))
  onBeforeUnmount(() => window.removeEventListener('popstate', syncPage))
  return { activePage, setPage, navigate }
}
