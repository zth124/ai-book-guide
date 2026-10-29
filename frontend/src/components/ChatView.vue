<template>
  <div class="chat-container">
    <!-- 聊天记录区域 -->
    <div class="chat-history" ref="chatHistoryRef">
      <!-- 欢迎语 -->
      <div class="message ai">
        <div class="avatar">🤖</div>
        <div class="bubble">你好！我是 AI 图书导购。请告诉我你的基础、想学的方向以及预算。</div>
      </div>

      <!-- 循环渲染聊天记录 -->
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>

        <!-- 纯文本消息 -->
        <div v-if="msg.type === 'text'" class="bubble">{{ msg.content }}</div>

        <!-- 结构化方案消息（复用 PlanCard 组件） -->
        <PlanCard
          v-if="msg.type === 'plan'"
          :plan="msg.content"
          @confirm="handleConfirm(msg.content)"
          @adjust="handleAdjust"
        />
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-area">
      <input
        v-model="inputText"
        @keyup.enter="sendMessage"
        placeholder="例如：我只有Java基础，想学Spring Boot，预算200以内"
      />
      <button @click="sendMessage">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import PlanCard from './PlanCard.vue'

const messages = ref([])
const inputText = ref('')
const chatHistoryRef = ref(null)

// 会话 ID：同一浏览器内保持同一个，用于后端维持多轮上下文
const sessionId = (typeof crypto !== 'undefined' && crypto.randomUUID)
  ? crypto.randomUUID()
  : 'session-' + Date.now()

const sendMessage = async () => {
  if (!inputText.value.trim()) return

  const userText = inputText.value
  messages.value.push({ role: 'user', type: 'text', content: userText })
  inputText.value = ''
  scrollToBottom()

  try {
    // 真实呼叫后端，带上 session_id 维持多轮对话
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, session_id: sessionId })
    })
    const data = await res.json()

    if (data.code === 200) {
      if (data.type === 'plan') {
        // 后端返回结构化方案
        messages.value.push({ role: 'ai', type: 'text', content: '已经为你规划好专属购书方案：' })
        messages.value.push({ role: 'ai', type: 'plan', content: data.data })
      } else if (data.type === 'clarify') {
        // 后端反问了补充信息
        messages.value.push({ role: 'ai', type: 'text', content: data.message })
      } else {
        // 普通文本
        messages.value.push({ role: 'ai', type: 'text', content: data.message })
      }
    } else {
      messages.value.push({ role: 'ai', type: 'text', content: data.message || 'AI 大脑开小差了，请重试。' })
    }
    scrollToBottom()
  } catch (error) {
    messages.value.push({ role: 'ai', type: 'text', content: "网络错误，无法连接 AI 服务。" })
  }
}

// 处理“确认购买” (真正的加购逻辑)
const handleConfirm = async (plan) => {
  try {
    // 暂存优惠券 ID，结算时一并提交
    if (plan.coupon && plan.coupon.applied && plan.coupon.id != null) {
      localStorage.setItem('pending_coupon_id', String(plan.coupon.id))
    } else {
      localStorage.removeItem('pending_coupon_id')
    }
    for (const book of plan.books) {
      await fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 1, book_id: book.id, qty: 1 })
      })
    }
    alert(`✅ 已成功将方案中的 ${plan.books.length} 本书加入购物车！请去购物车页面查看。`)
  } catch (error) {
    alert("加购失败，请检查后端是否运行")
  }
}

// 处理“微调”
const handleAdjust = () => {
  inputText.value = '第二本能换成实战类的书吗？'
}

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatHistoryRef.value) {
      chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px); /* 填满屏幕剩余高度 */
  max-width: 800px;
  margin: 0 auto;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  overflow: hidden;
}
.chat-history {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f9fbfc;
}
.message {
  display: flex;
  margin-bottom: 20px;
  gap: 12px;
}
.message.user { flex-direction: row-reverse; }
.avatar {
  width: 40px; height: 40px;
  background: #eee; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.message.user .avatar { background: #42b883; }
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
  line-height: 1.5;
}
.message.user .bubble {
  background: #42b883;
  color: white;
  border-bottom-right-radius: 2px;
}
.message.ai .bubble {
  border-bottom-left-radius: 2px;
}
.chat-input-area {
  display: flex;
  padding: 15px 20px;
  background: white;
  border-top: 1px solid #eee;
  gap: 10px;
}
.chat-input-area input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 24px;
  outline: none;
}
.chat-input-area input:focus { border-color: #42b883; }
.chat-input-area button {
  padding: 0 24px;
  background: #35495e;
  color: white;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-weight: bold;
}
</style>