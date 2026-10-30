<template>
  <div class="chat-container">
    <!-- 聊天头部 -->
    <div class="chat-header">
      <div class="ai-badge">✨ AI 导购</div>
      <span class="chat-tip">告诉我你的基础、方向和预算</span>
    </div>

    <!-- 聊天记录区域 -->
    <div class="chat-history" ref="chatHistoryRef">
      <!-- 欢迎语 -->
      <div class="message ai">
        <div class="avatar ai-avatar">🤖</div>
        <div class="bubble ai-bubble">
          你好！我是 BookWise AI 导购 📚<br>
          告诉我你的学习基础、方向和预算，我帮你推荐最合适的书单。
        </div>
      </div>

      <!-- 循环渲染聊天记录 -->
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <div :class="['avatar', msg.role === 'user' ? 'user-avatar' : 'ai-avatar']">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>

        <!-- 纯文本消息 -->
        <div v-if="msg.type === 'text'" :class="['bubble', msg.role === 'user' ? 'user-bubble' : 'ai-bubble']">
          {{ msg.content }}
        </div>

        <!-- 结构化方案消息 -->
        <PlanCard
          v-if="msg.type === 'plan'"
          :plan="msg.content"
          @confirm="handleConfirm(msg.content)"
          @adjust="handleAdjust"
        />
      </div>
    </div>

    <!-- 快捷示例 -->
    <div class="quick-prompts">
      <button @click="inputText = '我有Java基础，想学Spring Boot，预算200以内'">Java → Spring Boot</button>
      <button @click="inputText = '想入门前端，预算150左右'">前端入门</button>
      <button @click="inputText = '我想系统学习算法'">算法路线</button>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input-area">
      <div class="input-wrap">
        <input
          v-model="inputText"
          @keyup.enter="sendMessage"
          placeholder="试试：我只有Java基础，想学Spring Boot，预算200以内"
        />
        <button class="send-btn" @click="sendMessage">
          <span>发送</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import PlanCard from './PlanCard.vue'

const messages = ref([])
const inputText = ref('')
const chatHistoryRef = ref(null)

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
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, session_id: sessionId })
    })
    const data = await res.json()

    if (data.code === 200) {
      if (data.type === 'plan') {
        messages.value.push({ role: 'ai', type: 'plan', content: data.data })
      } else if (data.type === 'clarify') {
        messages.value.push({ role: 'ai', type: 'text', content: data.message })
      } else {
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

const handleConfirm = async (plan) => {
  try {
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

const handleAdjust = () => {
  inputText.value = '第二本能换成实战类的书吗？'
}

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
  display: flex; flex-direction: column;
  height: calc(100vh - 160px);
  max-width: 820px; margin: 0 auto;
  background: rgba(255,255,255,0.7); backdrop-filter: blur(12px);
  border-radius: 20px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  overflow: hidden; border: 1px solid rgba(255,255,255,0.8);
}
.chat-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 22px; background: rgba(255,255,255,0.6);
  border-bottom: 1px solid rgba(0,0,0,0.05);
}
.ai-badge {
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
}
.chat-tip { font-size: 13px; color: #9ca3af; }

.chat-history {
  flex: 1; padding: 24px; overflow-y: auto;
  background: linear-gradient(180deg, rgba(245,247,255,0.5), rgba(255,255,255,0.2));
}
.message { display: flex; margin-bottom: 22px; gap: 12px; animation: fadeUp .3s ease both; }
.message.user { flex-direction: row-reverse; }

.avatar {
  width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.ai-avatar { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; }
.user-avatar { background: #f3f4f6; color: #4b5563; }

.bubble {
  max-width: 70%; padding: 12px 16px; border-radius: 16px;
  line-height: 1.55; font-size: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.ai-bubble {
  background: white; color: #1f2937; border-top-left-radius: 4px;
}
.user-bubble {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; border-top-right-radius: 4px;
}

.quick-prompts {
  display: flex; gap: 8px; padding: 0 24px 12px; flex-wrap: wrap;
}
.quick-prompts button {
  background: rgba(99,102,241,0.08); color: #4f46e5;
  border: 1px solid rgba(99,102,241,0.15); border-radius: 20px;
  padding: 6px 14px; font-size: 12px; font-weight: 500; cursor: pointer;
  transition: all .15s;
}
.quick-prompts button:hover { background: rgba(99,102,241,0.15); }

.chat-input-area { padding: 16px 24px 20px; background: rgba(255,255,255,0.5); }
.input-wrap {
  display: flex; align-items: center; gap: 10px;
  background: white; border-radius: 24px; padding: 6px 6px 6px 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08), 0 0 0 1px rgba(99,102,241,0.1);
  transition: box-shadow .2s;
}
.input-wrap:focus-within { box-shadow: 0 4px 16px rgba(99,102,241,0.2), 0 0 0 2px rgba(99,102,241,0.2); }
.input-wrap input {
  flex: 1; border: none; outline: none; padding: 10px 0;
  font-size: 14px; background: transparent; color: #1f2937;
}
.send-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 22px; border: none; border-radius: 20px; cursor: pointer;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  font-size: 13px; font-weight: 600; transition: transform .15s, box-shadow .15s;
}
.send-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,0.35); }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>