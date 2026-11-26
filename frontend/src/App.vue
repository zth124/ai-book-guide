<template>
  <div class="app">
    <!-- 登录 / 注册 -->
    <AuthView v-if="!user" @auth="onAuth" />

    <template v-else>
      <!-- 顶部导航 -->
      <header class="nav">
        <div class="nav-inner">
          <button class="brand" @click="switchView('books')">
            <span class="brand-mark"><Icon name="book" :size="17" /></span>
            <span class="brand-type">
              <strong>BookWise</strong>
              <em>AI 图书导购</em>
            </span>
          </button>

          <nav class="tabs">
            <button
              v-for="t in tabs"
              :key="t.key"
              :class="['tab', { active: currentView === t.key }]"
              @click="switchView(t.key)"
            >
              <Icon :name="t.icon" :size="16" />
              <span>{{ t.label }}</span>
            </button>
          </nav>

          <div class="nav-user">
            <button class="user-chip" @click="switchView('profile')" title="进入「我的」">
              <span class="avatar">
                <img v-if="avatarSrc" :src="avatarSrc" alt="" />
                <template v-else>{{ userInitial }}</template>
              </span>
              <span class="uname">{{ user.name }}</span>
            </button>
            <button class="logout" @click="switchUser">退出</button>
          </div>
        </div>
      </header>

      <main class="main">
        <!-- 图书 -->
        <section v-if="currentView === 'books'" class="page">
          <div class="hero">
            <div class="hero-copy">
              <span class="eyebrow"><Icon name="sparkles" :size="14" /> AI 选书</span>
              <h2 class="hero-title">把选书这件事<br /><span class="grad-text">交给 AI</span></h2>
              <p class="hero-desc">
                说清楚基础、方向和预算，它去比价、查库存、算优惠，
                给你一份带路线的书单；之后想改，随时说。
              </p>
              <div class="hero-actions">
                <button class="btn btn-primary" @click="switchView('chat')">
                  <Icon name="sparkles" :size="16" /> 让 AI 推荐
                </button>
                <button class="btn btn-ghost" @click="openCart">
                  <Icon name="cart" :size="16" /> 查看购物车
                </button>
              </div>
            </div>

            <div class="hero-visual" aria-hidden="true">
              <div class="halo"></div>
              <div class="stage">
                <span class="ring"></span>
                <span class="ring ring-2"></span>
                <div class="core">
                  <Icon name="sparkles" :size="28" />
                  <span>AI 导购</span>
                </div>
              </div>
              <div class="orbit o1"><span>检索</span></div>
              <div class="orbit o2"><span>比价</span></div>
              <div class="orbit o3"><span>库存</span></div>
              <div class="orbit o4"><span>优惠券</span></div>
              <div class="orbit o5"><span>预算</span></div>
            </div>
          </div>

          <div class="toolbar">
            <div class="search">
              <Icon name="search" :size="17" />
              <input v-model="keyword" placeholder="搜索书名、作者、标签…" @keyup.enter="fetchBooks" />
              <button class="btn btn-primary search-btn" @click="fetchBooks">搜索</button>
            </div>
            <div class="filters">
              <button
                v-for="lv in levels"
                :key="lv.value"
                :class="['filter', { active: level === lv.value }]"
                @click="setLevel(lv.value)"
              >
                {{ lv.label }}
              </button>
            </div>
          </div>

          <div v-if="loading" class="grid">
            <div v-for="n in 6" :key="n" class="skeleton" style="height: 322px"></div>
          </div>

          <div v-else-if="error" class="state">
            <div class="state-icon"><Icon name="refresh" :size="24" /></div>
            <p>{{ error }}</p>
            <button class="btn btn-ghost" @click="fetchBooks">重新加载</button>
          </div>

          <div v-else-if="books.length === 0" class="state">
            <div class="state-icon"><Icon name="search" :size="24" /></div>
            <p>没有匹配的图书，换个关键词或难度试试</p>
          </div>

          <div v-else class="grid">
            <article
              v-for="(book, i) in books"
              :key="book.id"
              class="book"
              :style="{ '--i': i }"
              @mousemove="spot"
              @mouseleave="clearSpot"
            >
              <div class="book-cover" :style="{ background: coverGradient(book.level) }">
                <span class="book-orbit"></span>
                <span class="book-level">{{ book.level }}</span>
                <span v-if="book.rating" class="book-rating">
                  <Icon name="star" :size="11" />{{ book.rating }}
                </span>
                <span class="book-spine"></span>
              </div>
              <div class="book-body">
                <h3 class="book-title">{{ book.title }}</h3>
                <p class="book-author">{{ book.author }}</p>
                <div class="book-tags">
                  <span class="tag">{{ book.category }}</span>
                  <span v-if="book.publisher" class="tag ghost">{{ book.publisher }}</span>
                </div>
              </div>
              <div class="book-foot">
                <span class="price"><small>￥</small>{{ book.list_price }}</span>
                <button class="add" @click.stop="addToCart(book.id)">
                  <Icon name="plus" :size="14" /> 加购
                </button>
              </div>
            </article>
          </div>
        </section>

        <!-- AI 导购 -->
        <section v-else-if="currentView === 'chat'" class="page">
          <ChatView :user-id="user.id" />
        </section>

        <!-- 购物车 -->
        <section v-else-if="currentView === 'cart'" class="page">
          <CartView :key="cartKey" :user-id="user.id" @orders="currentView = 'orders'" />
        </section>

        <!-- 订单 -->
        <section v-else-if="currentView === 'orders'" class="page">
          <OrderView :user-id="user.id" />
        </section>

        <!-- 我的 -->
        <section v-else class="page">
          <ProfileView
            :user="user"
            @update="onUserUpdate"
            @cart="openCart"
            @orders="currentView = 'orders'"
            @logout="switchUser"
          />
        </section>
      </main>

      <div v-if="toast" class="toast">{{ toast }}</div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import CartView from './components/CartView.vue'
import ChatView from './components/ChatView.vue'
import OrderView from './components/OrderView.vue'
import ProfileView from './components/ProfileView.vue'
import AuthView from './components/AuthView.vue'
import Icon from './components/Icon.vue'
import { api, loadUser, saveUser, clearUser, avatarUrl } from './api'

const currentView = ref('books')
const cartKey = ref(0)
const books = ref([])
const keyword = ref('')
const level = ref('')
const loading = ref(false)
const error = ref('')
const toast = ref('')

const user = ref(loadUser())

const tabs = [
  { key: 'books', label: '图书', icon: 'book' },
  { key: 'chat', label: 'AI 导购', icon: 'sparkles' },
  { key: 'cart', label: '购物车', icon: 'cart' },
  { key: 'orders', label: '订单', icon: 'receipt' },
  { key: 'profile', label: '我的', icon: 'user' }
]

const levels = [
  { value: '', label: '全部' },
  { value: '入门', label: '入门' },
  { value: '进阶', label: '进阶' },
  { value: '实战', label: '实战' }
]

const userInitial = computed(() => (user.value && user.value.name ? user.value.name.slice(0, 1) : '书'))
const avatarSrc = computed(() => avatarUrl(user.value))

let toastTimer = null
const showToast = (msg) => {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2400)
}

// 登录 / 注册成功后：缓存用户并加载图书
const onAuth = async (data) => {
  saveUser(data)
  user.value = data
  currentView.value = 'books'
  await fetchBooks()
}

// 「我的」页改动用户名或头像后，同步到导航和本地缓存
const onUserUpdate = (next) => {
  user.value = next
  saveUser(next)
}

const switchUser = () => {
  clearUser()
  user.value = null
  books.value = []
  currentView.value = 'books'
}

const switchView = (key) => {
  if (key === 'cart') { openCart(); return }
  currentView.value = key
}

const fetchBooks = async () => {
  loading.value = true
  error.value = ''
  try {
    const qs = new URLSearchParams()
    if (keyword.value.trim()) qs.set('keyword', keyword.value.trim())
    if (level.value) qs.set('level', level.value)
    const data = await api(`/api/books?${qs.toString()}`)
    books.value = data.data || []
  } catch (e) {
    error.value = e.message
    books.value = []
  } finally {
    loading.value = false
  }
}

const setLevel = (v) => {
  level.value = v
  fetchBooks()
}

const addToCart = async (bookId) => {
  try {
    await api('/api/cart/add', {
      method: 'POST',
      body: JSON.stringify({ user_id: user.value.id, book_id: bookId, qty: 1 })
    })
    showToast('已加入购物车')
  } catch (e) {
    showToast(e.message)
  }
}

const openCart = () => {
  cartKey.value += 1
  currentView.value = 'cart'
}

// 指针光斑：跟随鼠标的高光，纯 CSS 变量驱动
const spot = (e) => {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  el.style.setProperty('--mx', `${e.clientX - r.left}px`)
  el.style.setProperty('--my', `${e.clientY - r.top}px`)
}
const clearSpot = (e) => {
  e.currentTarget.style.removeProperty('--mx')
  e.currentTarget.style.removeProperty('--my')
}

// 根据难度生成书封的网格渐变
const coverGradient = (lv) => {
  const palettes = {
    '入门': ['#3a8fa0', '#a7e8de'],
    '进阶': ['#2a7f86', '#dfb6ae'],
    '实战': ['#3c8ea6', '#164f52']
  }
  const [a, b] = palettes[lv] || palettes['进阶']
  return `radial-gradient(120% 120% at 12% 0%, ${a} 0%, transparent 56%), radial-gradient(120% 120% at 92% 8%, ${b} 0%, transparent 60%), linear-gradient(160deg, #0e2b30 0%, #061419 100%)`
}

onMounted(() => {
  if (user.value) fetchBooks()
})
</script>

<style scoped>
.app { min-height: 100vh; }

/* ---------- 导航 ---------- */
.nav {
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  background: rgba(6, 22, 26, 0.66);
  border-bottom: 1px solid var(--stroke);
}
.nav-inner {
  max-width: 1240px; margin: 0 auto;
  height: 70px; padding: 0 28px;
  display: flex; align-items: center; gap: 28px;
}
.brand {
  display: flex; align-items: center; gap: 11px;
  background: none; border: 0; cursor: pointer; padding: 0;
}
.brand-mark {
  width: 38px; height: 38px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--mark-bg);
  color: #06282b;
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 12px 26px -14px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.brand-type { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.2; }
.brand-type strong { color: var(--text); font-size: 16px; letter-spacing: -0.02em; }
.brand-type em { font-style: normal; font-size: 10.5px; color: var(--text-faint); letter-spacing: 0.08em; }

.tabs { display: flex; gap: 4px; margin-left: auto; }
.tab {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 15px; border-radius: 12px; border: 0;
  background: transparent; color: var(--text-dim);
  font-size: 13.5px; font-weight: 500; cursor: pointer;
  transition: color 0.2s, background 0.2s, box-shadow 0.2s;
}
.tab:hover { color: var(--text); background: var(--surface); }
.tab.active {
  color: #f2fbfa;
  background: rgba(167, 232, 222, 0.14);
  border: 1px solid rgba(167, 232, 222, 0.26);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18), 0 10px 26px -18px rgba(2, 20, 22, 0.9);
}

.nav-user { display: flex; align-items: center; gap: 9px; }
.user-chip {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 11px 4px 4px;
  border-radius: 999px; cursor: pointer;
  background: var(--surface); border: 1px solid var(--stroke);
  transition: all 0.2s var(--ease);
}
.user-chip:hover { border-color: rgba(47, 143, 136, 0.42); background: rgba(47, 143, 136, 0.12); }
.avatar {
  width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  font-size: 13px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #2f8f88, #dfb6ae);
  box-shadow: 0 8px 18px -8px rgba(223, 182, 174, 0.9);
}
.avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.uname {
  font-size: 13px; color: var(--text); max-width: 96px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.logout {
  border: 1px solid var(--stroke); background: var(--surface);
  color: var(--text-dim); font-size: 11.5px;
  padding: 5px 12px; border-radius: 999px; cursor: pointer;
  transition: all 0.2s;
}
.logout:hover { color: var(--text); border-color: var(--stroke-2); }

/* ---------- 主区域 ---------- */
.main { max-width: 1240px; margin: 0 auto; padding: 40px 28px 72px; }
.page { animation: fadeUp 0.5s var(--ease) both; }

/* ---------- Hero ---------- */
.hero {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 40px;
  align-items: center;
  padding: 24px 0 28px;
}
.eyebrow {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 13px; border-radius: 999px;
  background: rgba(47, 143, 136, 0.12);
  border: 1px solid rgba(47, 143, 136, 0.32);
  color: #b8e9e0; font-size: 11.5px; font-weight: 600;
  letter-spacing: 0.04em;
}
.hero-title {
  margin: 20px 0 0;
  font-size: clamp(38px, 4.6vw, 60px);
  line-height: 1.08;
  letter-spacing: -0.045em;
  font-weight: 700;
}
.hero-desc {
  margin: 20px 0 0;
  max-width: 480px;
  font-size: 14.5px; line-height: 1.85; color: var(--text-dim);
}
.hero-actions { display: flex; gap: 12px; margin-top: 28px; flex-wrap: wrap; }

.hero-visual {
  position: relative;
  height: 380px;
  display: flex; align-items: center; justify-content: center;
}
.halo {
  position: absolute; width: 360px; height: 360px; border-radius: 50%;
  background: radial-gradient(circle, rgba(47, 143, 136, 0.34), rgba(167, 232, 222, 0.12) 46%, transparent 72%);
  filter: blur(34px);
  animation: pulseDot 8s ease-in-out infinite;
}

/* 玻璃方盘：参考图那种厚边缘 + 细圆环 */
.stage {
  position: relative;
  width: 296px; height: 296px;
  border-radius: 34px;
  display: flex; align-items: center; justify-content: center;
  background:
    linear-gradient(158deg, rgba(167, 232, 222, 0.13), rgba(255, 255, 255, 0.03) 46%, rgba(4, 20, 23, 0.36)),
    radial-gradient(90% 70% at 40% 0%, rgba(255, 255, 255, 0.1), transparent 62%);
  border: 1px solid rgba(214, 242, 239, 0.2);
  box-shadow:
    0 44px 90px -52px rgba(2, 20, 22, 0.95),
    inset 0 1px 0 rgba(255, 255, 255, 0.26),
    inset 0 -30px 60px -40px rgba(2, 20, 22, 0.9);
  backdrop-filter: blur(12px);
}
.stage::after {
  content: '';
  position: absolute; inset: 0;
  border-radius: inherit; padding: 1px;
  pointer-events: none;
  background: linear-gradient(150deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.06) 24%, transparent 52%, rgba(167, 232, 222, 0.22) 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
}
.ring {
  position: absolute;
  width: 214px; height: 214px; border-radius: 50%;
  border: 1px solid rgba(214, 242, 239, 0.34);
}
.ring-2 { width: 248px; height: 248px; border-color: rgba(214, 242, 239, 0.13); }

.core {
  position: relative;
  width: 132px; height: 132px; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px;
  color: #f4fbfa;
  background:
    radial-gradient(circle at 34% 22%, rgba(255, 255, 255, 0.55), transparent 44%),
    radial-gradient(circle at 68% 86%, rgba(167, 232, 222, 0.45), transparent 56%),
    linear-gradient(158deg, #2f8f88 0%, #1a6567 54%, #0d3c40 100%);
  border: 1px solid rgba(255, 255, 255, 0.32);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    inset 0 -20px 36px -16px rgba(2, 20, 22, 0.85),
    0 26px 54px -24px rgba(2, 20, 22, 0.95);
  animation: floaty 7s ease-in-out infinite;
}
.core span { font-size: 11.5px; font-weight: 600; letter-spacing: 0.14em; text-shadow: 0 1px 10px rgba(2, 20, 22, 0.6); }
.orbit {
  position: absolute;
  padding: 7px 14px; border-radius: 999px;
  font-size: 12px; color: var(--text);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--stroke-2);
  backdrop-filter: blur(14px);
  box-shadow: 0 14px 30px -18px rgba(0, 0, 0, 0.9);
  animation: floaty 5s ease-in-out infinite;
}
.o1 { top: 18px; left: 6%; animation-delay: 0.2s; }
.o2 { top: 118px; right: 0%; animation-delay: 1.1s; }
.o3 { bottom: 92px; left: -2%; animation-delay: 2s; }
.o4 { bottom: 12px; right: 12%; animation-delay: 0.7s; }
.o5 { top: 0px; right: 34%; animation-delay: 1.6s; }

/* ---------- 搜索与筛选 ---------- */
.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 18px; margin-bottom: 26px; flex-wrap: wrap;
}
.search {
  display: flex; align-items: center; gap: 10px;
  flex: 1; min-width: 280px; max-width: 460px;
  height: 50px; padding: 0 6px 0 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--stroke);
  color: var(--text-faint);
  transition: border-color 0.25s, box-shadow 0.25s;
}
.search:focus-within {
  border-color: rgba(47, 143, 136, 0.55);
  box-shadow: 0 0 0 4px rgba(47, 143, 136, 0.1);
}
.search input {
  flex: 1; border: 0; outline: 0; background: transparent;
  color: var(--text); font-size: 14px;
}
.search input::placeholder { color: var(--text-faint); }
.search-btn { padding: 10px 20px; border-radius: 12px; }

.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.filter {
  padding: 8px 17px; border-radius: 999px; cursor: pointer;
  background: var(--surface); border: 1px solid var(--stroke);
  color: var(--text-dim); font-size: 13px; font-weight: 500;
  transition: all 0.22s var(--ease);
}
.filter:hover { color: var(--text); border-color: var(--stroke-2); }
.filter.active {
  color: #f2fbfa;
  background: rgba(167, 232, 222, 0.16);
  border-color: rgba(167, 232, 222, 0.3);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

/* ---------- 图书网格 ---------- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(262px, 1fr));
  gap: 22px;
}
.book {
  position: relative;
  display: flex; flex-direction: column;
  border-radius: 18px;
  border: 1px solid var(--stroke);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.018) 60%, rgba(255, 255, 255, 0.012)),
    radial-gradient(120% 70% at 50% 0%, rgba(167, 232, 222, 0.06), transparent 62%);
  overflow: hidden;
  isolation: isolate;
  animation: cardIn 0.55s var(--ease) both;
  animation-delay: calc(var(--i, 0) * 45ms);
  transition: transform 0.35s var(--ease), border-color 0.35s, box-shadow 0.35s;
}
.book > * { position: relative; z-index: 1; }
.book::after {
  content: '';
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background: radial-gradient(240px circle at var(--mx, 50%) var(--my, 50%), rgba(167, 232, 222, 0.22), transparent 68%);
  opacity: 0;
  transition: opacity 0.3s;
}
.book:hover {
  transform: translateY(-8px);
  border-color: rgba(167, 232, 222, 0.34);
  box-shadow: 0 36px 70px -38px rgba(2, 20, 22, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.16);
}
.book:hover::after { opacity: 1; }

.book-cover { height: 150px; position: relative; overflow: hidden; }
.book-cover::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(154deg, rgba(255, 255, 255, 0.22), transparent 42%, transparent 78%, rgba(255, 255, 255, 0.05));
  pointer-events: none;
}
.book-orbit {
  position: absolute; right: -30px; top: 22px;
  width: 128px; height: 128px; border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.22);
  box-shadow: inset 0 0 0 18px rgba(255, 255, 255, 0.02);
}
.book-spine {
  position: absolute; left: 0; top: 0; bottom: 0; width: 6px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0.12));
  opacity: 0.5;
}
.book-level {
  position: absolute; left: 16px; bottom: 14px;
  padding: 4px 11px; border-radius: 999px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
  color: #0b1020; background: rgba(255, 255, 255, 0.9);
}
.book-rating {
  position: absolute; top: 14px; right: 14px;
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 700; color: #ffe9a8;
  background: rgba(10, 12, 22, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(8px);
}
.book-body { padding: 16px 18px 0; flex: 1; }
.book-title {
  margin: 0; font-size: 15.5px; font-weight: 700; line-height: 1.4;
  letter-spacing: -0.01em;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.book-author { margin: 7px 0 0; font-size: 12.5px; color: var(--text-dim); }
.book-tags { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
.tag {
  padding: 4px 10px; border-radius: 8px;
  font-size: 11px; font-weight: 600;
  color: #b8e9e0; background: rgba(47, 143, 136, 0.14);
  border: 1px solid rgba(47, 143, 136, 0.26);
}
.tag.ghost { color: var(--text-faint); background: var(--surface); border-color: var(--stroke); }

.book-foot {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 18px 18px;
}
.price {
  font-size: 21px; font-weight: 800; letter-spacing: -0.02em; color: #fff;
}
.price small { font-size: 12px; font-weight: 600; color: var(--text-dim); margin-right: 2px; }
.add {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 8px 15px; border-radius: 999px; cursor: pointer;
  border: 1px solid rgba(47, 143, 136, 0.4);
  background: rgba(47, 143, 136, 0.14);
  color: #cdeee9; font-size: 12.5px; font-weight: 600;
  transition: all 0.2s var(--ease);
}
.add:hover {
  background: var(--cta-bg);
  color: var(--cta-fg); border-color: rgba(255, 255, 255, 0.4);
  box-shadow: 0 12px 26px -14px rgba(2, 20, 22, 0.9);
}

/* ---------- 状态 ---------- */
.state {
  padding: 64px 20px; text-align: center; color: var(--text-dim);
  border: 1px dashed var(--stroke-2); border-radius: var(--radius);
}
.state-icon {
  width: 58px; height: 58px; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 16px; color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--stroke);
}
.state p { margin: 0 0 18px; font-size: 14px; }

/* ---------- 提示 ---------- */
.toast {
  position: fixed; left: 50%; bottom: 40px; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 14px;
  font-size: 13.5px; color: var(--text);
  background: rgba(16, 19, 32, 0.92);
  border: 1px solid var(--stroke-2);
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 50px -20px rgba(0, 0, 0, 0.9);
  z-index: 300;
  animation: fadeUp 0.3s var(--ease) both;
}

/* ---------- 响应式 ---------- */
@media (max-width: 980px) {
  .hero { grid-template-columns: 1fr; gap: 0; padding-bottom: 34px; }
  .hero-visual { height: 300px; order: -1; margin-bottom: 4px; }
  .stage { width: 246px; height: 246px; border-radius: 28px; }
  .ring { width: 180px; height: 180px; }
  .ring-2 { width: 210px; height: 210px; }
  .core { width: 110px; height: 110px; }
  .halo { width: 270px; height: 270px; }
  .orbit { display: none; }
  .nav-inner { gap: 14px; padding: 0 18px; }
  .nav-user .uname { display: none; }
}
@media (max-width: 720px) {
  .main { padding: 26px 18px 56px; }
  .tabs .tab span { display: none; }
  .tab { padding: 9px 12px; }
  .hero-title { font-size: 40px; }
  .grid { grid-template-columns: 1fr; }
  .search { max-width: none; }
  .book-cover { height: 132px; margin: 12px 12px 0; border-radius: 13px; }
  .book-spine { border-radius: 13px 0 0 13px; opacity: 0.3; }
}
@media (max-width: 560px) {
  .nav-inner { padding: 0 12px; gap: 8px; height: 62px; }
  .brand-type { display: none; }
  .tabs { gap: 0; }
  .tab { padding: 9px 10px; }
  .logout { display: none; }
  .hero-visual { height: 276px; }
  .stage { width: 228px; height: 228px; }
  .core { width: 100px; height: 100px; }
  .ring { width: 166px; height: 166px; }
  .ring-2 { width: 194px; height: 194px; }
}
</style>
