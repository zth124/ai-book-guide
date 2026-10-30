<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="brand">
        <div class="brand-icon">📖</div>
        <div class="brand-text">
          <h1>BookWise</h1>
          <span>AI 智能图书商城</span>
        </div>
      </div>
      <div class="nav-links">
        <button :class="{ active: currentView === 'books' }" @click="currentView = 'books'">
          <span class="nav-icon">📚</span> 图书
        </button>
        <button :class="{ active: currentView === 'chat' }" @click="currentView = 'chat'">
          <span class="nav-icon">✨</span> AI 导购
        </button>
        <button :class="{ active: currentView === 'cart' }" @click="currentView = 'cart'; refreshCart()">
          <span class="nav-icon">🛒</span> 购物车
        </button>
      </div>
    </nav>

    <!-- 根据 currentView 显示不同页面 -->
    <main class="content">
      <!-- 1. 图书列表视图 -->
      <div v-if="currentView === 'books'">
        <div class="page-header">
          <h2>探索好书</h2>
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input v-model="keyword" placeholder="搜索书名、作者、标签..." @keyup.enter="fetchBooks" />
            <button @click="fetchBooks">搜索</button>
          </div>
        </div>

        <div class="book-grid">
          <div v-for="book in books" :key="book.id" class="book-card">
            <div class="book-cover" :style="{ background: coverGradient(book.level) }">
              <div class="cover-tag">{{ book.level }}</div>
            </div>
            <div class="book-info">
              <h3 class="book-title">{{ book.title }}</h3>
              <p class="book-author">{{ book.author }}</p>
              <div class="book-meta">
                <span class="meta-tag category">{{ book.category }}</span>
                <span v-if="book.rating" class="meta-tag rating">★ {{ book.rating }}</span>
              </div>
              <div class="book-footer">
                <span class="book-price">￥{{ book.list_price }}</span>
                <button class="add-btn" @click="addToCart(book.id)">+ 加购</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. 购物车视图 -->
      <CartView v-if="currentView === 'cart'" :key="cartKey" />

      <!-- 3. AI 聊天视图 -->
      <ChatView v-if="currentView === 'chat'" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import CartView from './components/CartView.vue'
import ChatView from './components/ChatView.vue'

const currentView = ref('books')
const cartKey = ref(0)
const books = ref([])
const keyword = ref('')

const fetchBooks = async () => {
  const res = await fetch(`/api/books?keyword=${keyword.value}`)
  const data = await res.json()
  books.value = data.data
}

const addToCart = async (bookId) => {
  const res = await fetch('/api/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: 1, book_id: bookId, qty: 1 })
  })
  const data = await res.json()
  if (data.status === 'success') {
    alert(`✅ 成功加入购物车！`)
  }
}

const refreshCart = () => { cartKey.value += 1 }

// 根据 level 给书脊一个渐变配色
const coverGradient = (level) => {
  const palettes = {
    '入门': ['#4facfe', '#00f2fe'],
    '进阶': ['#fa709a', '#fee140'],
    '实战': ['#30cfd0', '#330867'],
  }
  const [a, b] = palettes[level] || palettes['进阶']
  return `linear-gradient(135deg, ${a} 0%, ${b} 100%)`
}

onMounted(() => { fetchBooks() })
</script>

<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  background: linear-gradient(135deg, #f0f4ff 0%, #fdf4ff 50%, #fef3f2 100%);
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #1f2937;
}

/* 导航栏 */
.navbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 40px; height: 64px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  position: sticky; top: 0; z-index: 100;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-icon {
  width: 40px; height: 40px; border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}
.brand-text h1 { margin: 0; font-size: 18px; letter-spacing: -0.02em; }
.brand-text span { font-size: 11px; color: #9ca3af; }

.nav-links { display: flex; gap: 4px; }
.nav-links button {
  background: transparent; border: none; cursor: pointer;
  padding: 8px 16px; border-radius: 10px;
  display: flex; align-items: center; gap: 6px;
  color: #6b7280; font-size: 14px; font-weight: 500;
  transition: all .2s ease;
}
.nav-links button:hover { background: #f3f4f6; color: #1f2937; }
.nav-links button.active {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
}
.nav-icon { font-size: 15px; }

/* 内容区 */
.content { padding: 30px 40px; max-width: 1280px; margin: 0 auto; }
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 28px; flex-wrap: wrap; gap: 16px;
}
.page-header h2 { margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.02em; }

.search-box {
  position: relative; display: flex; align-items: center;
  background: white; border-radius: 24px; padding: 4px 4px 4px 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  width: 360px;
}
.search-box .search-icon { font-size: 14px; opacity: 0.5; }
.search-box input {
  flex: 1; border: none; outline: none; padding: 10px 10px;
  font-size: 14px; background: transparent;
}
.search-box button {
  padding: 10px 20px; border: none; border-radius: 20px; cursor: pointer;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  font-size: 13px; font-weight: 600; transition: transform .15s;
}
.search-box button:hover { transform: translateY(-1px); }

/* 图书网格 */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
}
.book-card {
  background: white; border-radius: 16px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06);
  transition: transform .25s ease, box-shadow .25s ease;
  cursor: pointer;
}
.book-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08), 0 20px 40px rgba(99, 102, 241, 0.15);
}

.book-cover {
  height: 140px; position: relative; overflow: hidden;
  display: flex; align-items: flex-end;
}
.book-cover .cover-tag {
  position: absolute; top: 14px; right: 14px;
  background: rgba(255,255,255,0.22); backdrop-filter: blur(6px);
  color: white; font-size: 11px; padding: 3px 10px; border-radius: 20px;
  font-weight: 600; letter-spacing: 0.04em;
}
.book-info { padding: 16px 18px 18px; display: flex; flex-direction: column; gap: 8px; }
.book-title { margin: 0; font-size: 15px; font-weight: 700; line-height: 1.35; }
.book-author { margin: 0; font-size: 13px; color: #6b7280; }
.book-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.meta-tag { font-size: 11px; padding: 3px 9px; border-radius: 10px; font-weight: 600; }
.meta-tag.category { background: #f3f4f6; color: #4b5563; }
.meta-tag.rating { background: #fef3c7; color: #b45309; }
.book-footer {
  margin-top: 4px; display: flex; justify-content: space-between; align-items: center;
}
.book-price { font-size: 18px; font-weight: 800; color: #dc2626; }
.add-btn {
  border: none; padding: 7px 14px; border-radius: 20px; cursor: pointer;
  background: #1f2937; color: white; font-size: 12px; font-weight: 600;
  transition: all .15s;
}
.add-btn:hover { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
</style>