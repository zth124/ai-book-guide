<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <h2>📚 智能图书商城</h2>
      <div class="links">
        <button :class="{ active: currentView === 'books' }" @click="currentView = 'books'">图书列表</button>
        <button :class="{ active: currentView === 'cart' }" @click="currentView = 'cart'; refreshCart()">购物车</button>
        <button :class="{ active: currentView === 'chat' }" @click="currentView = 'chat'">AI 导购 </button>
      </div>
    </nav>

    <!-- 根据 currentView 显示不同页面 -->
    <main class="content">
      <!-- 1. 图书列表视图 -->
      <div v-if="currentView === 'books'">
        <div class="search-box">
          <input v-model="keyword" placeholder="搜索书名（如 Spring）" @keyup.enter="fetchBooks" />
          <button @click="fetchBooks">搜索</button>
        </div>

        <div class="book-grid">
          <div v-for="book in books" :key="book.id" class="book-card">
            <h3>{{ book.title }}</h3>
            <p class="author">作者: {{ book.author }}</p>
            <p class="level">难度: {{ book.level }}</p>
            <p class="price">￥{{ book.list_price }}</p>
            <button class="add-btn" @click="addToCart(book.id)">加入购物车</button>
          </div>
        </div>
      </div>

      <!-- 2. 购物车视图 (使用刚才新建的组件) -->
      <CartView v-if="currentView === 'cart'" :key="cartKey" />

      <!-- 3. AI 聊天视图占位 -->
       <ChatView v-if="currentView === 'chat'" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import CartView from './components/CartView.vue' // 引入购物车组件
import ChatView from './components/ChatView.vue' // 新增这一行

// 视图切换控制
const currentView = ref('books')
const cartKey = ref(0) // 用来强制刷新购物车组件

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

// 切换到购物车时，强制刷新组件拉取最新数据
const refreshCart = () => {
  cartKey.value += 1
}

onMounted(() => {
  fetchBooks()
})
</script>

<style>
/* 基础样式重置 */
body { margin: 0; background: #f5f7fa; }
.app-container { font-family: sans-serif; }

/* 导航栏样式 */
.navbar {
  display: flex; justify-content: space-between; align-items: center;
  background: #35495e; color: white; padding: 0 30px; height: 60px;
}
.navbar h2 { margin: 0; font-size: 20px; }
.links button {
  background: transparent; color: #aeb9c6; border: none;
  font-size: 16px; margin-left: 20px; cursor: pointer; padding: 5px;
}
.links button.active { color: white; border-bottom: 2px solid #42b883; }

/* 内容区 */
.content { padding: 20px; max-width: 1200px; margin: 0 auto; }
.search-box { margin-bottom: 20px; }
.search-box input { padding: 8px; width: 250px; border: 1px solid #ccc; border-radius: 4px; }
.search-box button { padding: 8px 16px; margin-left: 10px; background: #42b883; color: white; border: none; border-radius: 4px; cursor: pointer; }

/* 图书网格 */
.book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
.book-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1); display: flex; flex-direction: column; }
.book-card h3 { margin: 0 0 10px 0; font-size: 18px; }
.author, .level { color: #666; font-size: 14px; margin: 5px 0; }
.price { color: #e53935; font-size: 20px; font-weight: bold; margin: 15px 0; }
.add-btn { margin-top: auto; padding: 10px; background: #35495e; color: white; border: none; border-radius: 4px; cursor: pointer; }
.add-btn:hover { background: #42b883; }

.chat-placeholder { text-align: center; color: #999; margin-top: 100px; }
</style>