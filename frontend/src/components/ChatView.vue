<template>
  <div class="chat glass">
    <div class="chat-head">
      <div class="ai-mark"><Icon name="sparkles" :size="18" /></div>
      <div class="chat-meta">
        <strong>AI 导购</strong>
        <span><i class="live"></i> 在线</span>
      </div>
    </div>

    <div class="chat-body" ref="chatHistoryRef" @scroll="onScroll">
      <div v-if="!messages.length" class="chat-empty" aria-hidden="true">
        <span class="ce-ring"></span>
        <span class="ce-ring r2"></span>
        <span class="ce-ring r3"></span>
        <div class="ce-core"><Icon name="book" :size="24" /></div>
        <p class="ce-text">随便说说你的情况<br />我帮你把书挑好</p>
      </div>

      <div class="msg ai">
        <div class="avatar ai"><Icon name="sparkles" :size="15" /></div>
        <div class="bubble ai">
          你好，我是 BookWise 导购。<br />
          告诉我你的学习基础、想学的方向和预算，我来帮你配一套书单。
        </div>
      </div>

      <div v-for="(msg, index) in messages" :key="index" :class="['msg', msg.role]">
        <div :class="['avatar', msg.role === 'user' ? 'user' : 'ai']">
          <Icon :name="msg.role === 'user' ? 'user' : 'sparkles'" :size="15" />
        </div>

        <!-- 用户提问 -->
        <div v-if="msg.role === 'user'" class="bubble user"><span>{{ msg.content }}</span></div>

        <!-- AI 一轮回复：思考过程与结果同属一条 -->
        <div v-else :class="['turn', { shell: msg.resultKind === 'text' }]">
          <div class="think">
            <button
              class="think-head"
              :disabled="!msg.done"
              @click="msg.collapsed = !msg.collapsed"
            >
              <span v-if="!msg.done" class="spinner"></span>
              <Icon v-else name="check" :size="14" class="ok" />
              <span class="think-title">
                {{ msg.done
                  ? `已思考 ${msg.steps.length} 步 · 用时 ${msg.elapsed}s`
                  : (msg.steps.length ? `正在思考… ${msg.steps.length} 步` : '正在思考…') }}
              </span>
              <Icon v-if="msg.done" name="arrow" :size="13" :class="['chev', { open: !msg.collapsed }]" />
            </button>
            <div v-show="!msg.collapsed" class="think-body">
              <div v-for="(s, i) in msg.steps" :key="i" class="step">
                <span class="dot"></span>
                <span class="step-label">{{ s.label }}</span>
                <span class="step-detail">{{ s.detail }}</span>
                <span class="step-ms">{{ s.ms }}ms</span>
              </div>
              <div v-if="!msg.done" class="step">
                <span class="dot pulsing"></span>
                <span class="step-detail muted">正在推理…</span>
              </div>
            </div>
          </div>

          <div v-if="msg.resultKind === 'text'" class="bubble ai">
            <span>{{ msg.content }}</span>
            <i v-if="msg.typing" class="caret"></i>
          </div>

          <PlanCard
            v-else-if="msg.resultKind === 'plan'"
            :plan="msg.content"
            @confirm="handleConfirm(msg.content)"
            @adjust="handleAdjust"
          />
        </div>
      </div>

      <div v-if="!following && userScrolled" class="jump-row">
        <button class="jump" @click="jumpLatest">
          回到最新 <Icon name="arrow" :size="13" />
        </button>
      </div>
    </div>

    <div class="quick">
      <button @click="inputText = '我有Java基础，想学Spring Boot，预算200以内'">Java → Spring Boot</button>
      <button @click="inputText = '想入门前端，预算150左右'">前端入门</button>
      <button @click="inputText = '我想系统学习算法'">算法路线</button>
    </div>

    <div class="composer">
      <div class="input-wrap">
        <Icon name="sparkles" :size="16" class="input-icon" />
        <input
          v-model="inputText"
          @keyup.enter="sendMessage"
          placeholder="试试：我只有 Java 基础，想学 Spring Boot，预算 200 以内"
        />
        <button class="send" :disabled="busy" @click="sendMessage" aria-label="发送">
          <Icon name="arrow" :size="16" />
        </button>
      </div>
      <p class="composer-tip">Enter 发送</p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import PlanCard from './PlanCard.vue'
import Icon from './Icon.vue'
import { api } from '../api'

const props = defineProps({
  userId: { type: Number, required: true }
})

const messages = ref([])
const inputText = ref('')
const chatHistoryRef = ref(null)
const busy = ref(false)

/* ---------------- 自动跟随 ---------------- */
// 用户没主动往上翻时，视图跟着新内容走；一旦手动滚离底部就停下，
// 回到底部（或点“回到最新”）后恢复跟随。
const following = ref(true)
const userScrolled = ref(false)
let rafId = null
// 程序自己滚动时会上报 scroll 事件，用一个时间戳把它和“用户手动滑动”区分开
let progAt = 0

const followBottom = () => {
  if (!following.value) return
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = null
    const el = chatHistoryRef.value
    if (el && following.value) {
      progAt = performance.now()
      el.scrollTop = el.scrollHeight
    }
  })
}

const onScroll = () => {
  const el = chatHistoryRef.value
  if (!el) return
  if (performance.now() - progAt < 260) return
  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
  if (gap < 48) {
    following.value = true
    userScrolled.value = false
  } else {
    following.value = false
    userScrolled.value = true
  }
}

const jumpLatest = () => {
  following.value = true
  userScrolled.value = false
  const el = chatHistoryRef.value
  if (el) {
    progAt = performance.now()
    el.scrollTop = el.scrollHeight
  }
}

// 方案这种长卡片一次性出现，停在底部会错过开头，
// 所以把它这一轮的开头顶到可视区顶部，用户能看到折叠后的思考条 + 卡片开头。
const revealTurn = async () => {
  await nextTick()
  // 等一帧把卡片布局坐实，否则 scrollHeight 还是旧的，滚动会被夹回 0
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))
  const el = chatHistoryRef.value
  if (!el) return
  const turns = el.querySelectorAll('.turn')
  const turnEl = turns[turns.length - 1]
  if (!turnEl) return
  if (rafId) { cancelAnimationFrame(rafId); rafId = null }
  progAt = performance.now()
  const delta = turnEl.getBoundingClientRect().top - el.getBoundingClientRect().top
  el.scrollTop += delta - 14
  // 停在“这一轮的开头”而不是底部，所以这里本来就不跟随新内容
  following.value = (el.scrollHeight - el.scrollTop - el.clientHeight) < 48
}

// 会话 id 持久化：刷新页面后仍是同一个 session_id，
// 后端按 session_id 保存用户画像与上一轮方案，多轮微调才不会从头开始。
const SESSION_KEY = 'bookwise_session_id'
const sessionId = (() => {
  let v = localStorage.getItem(SESSION_KEY)
  if (!v) {
    v = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : 'session-' + Date.now()
    localStorage.setItem(SESSION_KEY, v)
  }
  return v
})()

// AI 文本逐字出现，像正常对话一样；文字直接长在这轮的回复气泡里
const typeInto = async (turn, text) => {
  const target = text || ''
  turn.resultKind = 'text'
  turn.typing = true
  const step = Math.max(1, Math.ceil(target.length / 55))
  for (let i = 0; i < target.length; i += step) {
    turn.content = target.slice(0, i + step)
    followBottom()
    await new Promise(r => setTimeout(r, 16))
  }
  turn.content = target
  turn.typing = false
  followBottom()
}

const sendMessage = async () => {
  if (!inputText.value.trim() || busy.value) return

  const userText = inputText.value
  messages.value.push({ role: 'user', type: 'text', content: userText })
  inputText.value = ''
  busy.value = true
  following.value = true
  userScrolled.value = false
  followBottom()

  // 一轮 AI 回复从“思考中”开始：步骤逐步进来，结果最后落到同一条里
  const turn = {
    role: 'ai', type: 'turn',
    steps: [], done: false, collapsed: false, elapsed: '0.0',
    resultKind: null, content: '', typing: false
  }
  messages.value.push(turn)
  followBottom()
  const startedAt = performance.now()
  let finalEvent = null

  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText, session_id: sessionId, user_id: props.userId })
    })
    if (!res.ok || !res.body) throw new Error('stream unavailable')

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop() || ''

      for (const part of parts) {
        const line = part.split('\n').find(l => l.startsWith('data:'))
        if (!line) continue
        let evt
        try { evt = JSON.parse(line.slice(5)) } catch { continue }

        if (evt.kind === 'step') {
          turn.steps.push(evt.payload)
          followBottom()
        } else {
          finalEvent = evt
        }
      }
    }
  } catch (e) {
    finalEvent = { kind: 'error', payload: { message: '网络错误，无法连接 AI 服务。' } }
  }

  // 结果到了：思考面板自动收起成一行，只留结论
  turn.done = true
  turn.collapsed = true
  turn.elapsed = ((performance.now() - startedAt) / 1000).toFixed(1)
  followBottom()

  const payload = finalEvent && finalEvent.payload
  if (!payload) {
    await typeInto(turn, 'AI 没有返回结果，请重试。')
  } else if (finalEvent.kind === 'result' && payload.type === 'plan') {
    turn.resultKind = 'plan'
    turn.content = payload.data
    revealTurn()
  } else if (finalEvent.kind === 'result' && payload.type === 'clarify') {
    await typeInto(turn, payload.message)
  } else if (finalEvent.kind === 'result' && payload.type === 'text') {
    await typeInto(turn, payload.message)
  } else {
    await typeInto(turn, payload.message || 'AI 大脑开小差了，请重试。')
  }
  busy.value = false
}

const handleConfirm = async (plan) => {
  if (!plan || !plan.books || plan.books.length === 0) return
  try {
    if (plan.coupon && plan.coupon.applied && plan.coupon.id != null) {
      localStorage.setItem('pending_coupon_id', String(plan.coupon.id))
    } else {
      localStorage.removeItem('pending_coupon_id')
    }
    const failed = []
    for (const book of plan.books) {
      try {
        await api('/api/cart/add', {
          method: 'POST',
          body: JSON.stringify({ user_id: props.userId, book_id: book.id, qty: 1 })
        })
      } catch (e) {
        failed.push(`《${book.title}》：${e.message}`)
      }
    }
    if (failed.length) {
      alert(`部分图书加购失败：\n${failed.join('\n')}`)
    } else {
      alert(`已把方案中的 ${plan.books.length} 本书加入购物车，可去「购物车」结算或「订单」查看。`)
    }
  } catch (e) {
    alert(`加购失败：${e.message}`)
  }
}

const handleAdjust = () => {
  inputText.value = '第二本能换成实战类的书吗？'
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: min(760px, calc(100vh - 190px));
  max-width: 880px;
  margin: 0 auto;
  overflow: hidden;
}

/* 头部 */
.chat-head {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 22px;
  border-bottom: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.025);
}
.ai-mark {
  width: 38px; height: 38px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #2f8f88, #a7e8de);
  color: #fff;
  box-shadow: 0 12px 26px -12px rgba(47, 143, 136, 0.9);
}
.chat-meta { display: flex; flex-direction: column; gap: 3px; }
.chat-meta strong { font-size: 14.5px; letter-spacing: -0.01em; }
.chat-meta span { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--text-faint); }
.live {
  width: 6px; height: 6px; border-radius: 50%; background: var(--ok);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.9);
  animation: pulseDot 2s ease-in-out infinite;
}

/* 消息区 */
.chat-body {
  flex: 1;
  position: relative;
  padding: 24px 22px;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 20px;
  background: radial-gradient(120% 80% at 50% 0%, rgba(47, 143, 136, 0.09), transparent 62%);
}

/* 空状态：细圆环 + 珍珠核心，避免整屏空洞 */
.chat-empty {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -54%);
  width: 340px; height: 340px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0;
  pointer-events: none;
  opacity: 0.9;
}
.ce-ring {
  position: absolute; top: 50%; left: 50%;
  width: 160px; height: 160px; margin: -80px 0 0 -80px;
  border-radius: 50%; border: 1px solid rgba(214, 242, 239, 0.16);
}
.ce-ring.r2 { width: 232px; height: 232px; margin: -116px 0 0 -116px; border-color: rgba(214, 242, 239, 0.1); }
.ce-ring.r3 { width: 304px; height: 304px; margin: -152px 0 0 -152px; border-color: rgba(214, 242, 239, 0.06); }
.ce-core {
  width: 78px; height: 78px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #d9fbf4;
  background:
    radial-gradient(circle at 34% 24%, rgba(255, 255, 255, 0.28), transparent 52%),
    linear-gradient(158deg, rgba(47, 143, 136, 0.5), rgba(8, 40, 44, 0.55));
  border: 1px solid rgba(214, 242, 239, 0.24);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.24), 0 18px 40px -28px rgba(2, 20, 22, 0.9);
}
.ce-text {
  position: absolute; bottom: -14px;
  margin: 0; text-align: center;
  font-size: 12px; line-height: 1.9; color: var(--text-faint);
}
.msg { display: flex; gap: 11px; align-items: flex-start; animation: fadeUp 0.35s var(--ease) both; }
.msg.user { flex-direction: row-reverse; }

/* 一轮 AI 回复：思考条与结果同处一列，结果出来后思考条折叠成一行 */
.turn {
  display: flex; flex-direction: column; gap: 8px;
  width: 100%; min-width: 0;
  max-width: min(560px, calc(100% - 45px));
}
.turn .bubble { max-width: 100%; animation: none; }
.turn.shell {
  gap: 0; overflow: hidden;
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid var(--stroke);
  border-radius: 16px; border-top-left-radius: 5px;
  animation: fadeUp 0.3s var(--ease) both;
}
.turn.shell .think {
  border: 0; border-bottom: 1px solid rgba(255, 255, 255, 0.075);
  border-radius: 0; background: transparent;
  animation: none;
}
.turn.shell .bubble.ai {
  border: 0; border-radius: 0; background: transparent;
}

.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--stroke);
  background: var(--surface);
  color: var(--text-dim);
}
.avatar.ai {
  color: #06282b; border-color: rgba(255, 255, 255, 0.4);
  background: var(--mark-bg);
  box-shadow: 0 10px 22px -14px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.avatar.user { color: #b8e9e0; border-color: rgba(47, 143, 136, 0.35); background: rgba(47, 143, 136, 0.1); }

.bubble {
  max-width: min(540px, 76%);
  padding: 13px 17px;
  border-radius: 16px;
  font-size: 13.8px; line-height: 1.72;
  animation: fadeUp 0.3s var(--ease) both;
}
.bubble.ai {
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid var(--stroke);
  border-top-left-radius: 5px;
  color: var(--text);
}
.bubble.user {
  background: var(--bubble-bg);
  border: 1px solid rgba(167, 232, 222, 0.24);
  color: var(--text);
  border-top-right-radius: 5px;
  box-shadow: 0 18px 38px -24px rgba(2, 20, 22, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.14);
}
.caret {
  display: inline-block; width: 2px; height: 13px; margin-left: 2px;
  background: currentColor; vertical-align: -2px;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* 思考面板 */
.think {
  max-width: 100%;
  border-radius: 16px; overflow: hidden;
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.03);
  border-top-left-radius: 5px;
  animation: fadeUp 0.3s var(--ease) both;
}
.think-head {
  width: 100%;
  display: flex; align-items: center; gap: 9px;
  padding: 11px 15px;
  background: rgba(47, 143, 136, 0.07);
  border: 0; cursor: pointer;
  color: var(--text-dim); font-size: 12.5px; font-family: inherit;
  transition: background 0.2s;
}
.think-head:hover { background: rgba(47, 143, 136, 0.13); }
.think-title { flex: 1; text-align: left; color: var(--text); font-weight: 500; }
.spinner {
  width: 13px; height: 13px; border-radius: 50%;
  border: 2px solid rgba(47, 143, 136, 0.28);
  border-top-color: #a7e8de;
  animation: spin 0.8s linear infinite;
}
.ok { color: var(--ok); }
.chev { color: var(--text-faint); transform: rotate(90deg); transition: transform 0.25s var(--ease); }
.chev.open { transform: rotate(-90deg); }

.think-body { padding: 8px 15px 13px; border-top: 1px solid var(--stroke); }
.step {
  display: flex; align-items: flex-start; gap: 9px;
  padding: 5px 0; font-size: 12.2px; line-height: 1.55;
  animation: fadeUp 0.25s var(--ease) both;
}
.dot {
  width: 6px; height: 6px; border-radius: 50%; margin-top: 6px; flex-shrink: 0;
  background: linear-gradient(135deg, #2f8f88, #a7e8de);
  box-shadow: 0 0 8px rgba(47, 143, 136, 0.6);
}
.dot.pulsing { animation: pulseDot 1.1s ease-in-out infinite; }
.step-label { color: var(--text); font-weight: 600; flex-shrink: 0; min-width: 54px; }
.step-detail { color: var(--text-dim); flex: 1; word-break: break-word; }
.step-detail.muted { color: var(--text-faint); }
.step-ms { color: var(--text-faint); font-size: 10.5px; flex-shrink: 0; }

/* 用户手动上滑后，出现“回到最新” */
.jump-row {
  position: sticky; bottom: 2px; z-index: 6;
  display: flex; justify-content: flex-end;
  margin-top: -6px; padding: 0 14px 2px 0;
  pointer-events: none;
}
.jump {
  display: flex; align-items: center; gap: 5px;
  padding: 7px 14px; border-radius: 999px; cursor: pointer;
  font-size: 11.8px; font-family: inherit;
  color: var(--text);
  background: rgba(10, 32, 35, 0.86);
  border: 1px solid rgba(214, 242, 239, 0.28);
  backdrop-filter: blur(12px);
  box-shadow: 0 14px 30px -20px rgba(2, 20, 22, 0.95);
  pointer-events: auto;
  transition: border-color 0.2s, background 0.2s;
}
.jump:hover { border-color: rgba(167, 232, 222, 0.5); background: rgba(16, 50, 54, 0.92); }
.jump :deep(svg) { transform: rotate(90deg); }

/* 快捷指令 */
.quick {
  display: flex; gap: 8px; flex-wrap: wrap;
  padding: 0 22px 12px;
}
.quick button {
  padding: 7px 14px; border-radius: 999px; cursor: pointer;
  font-size: 12px; font-family: inherit;
  color: #b8e9e0;
  background: rgba(47, 143, 136, 0.1);
  border: 1px solid rgba(47, 143, 136, 0.26);
  transition: all 0.2s var(--ease);
}
.quick button:hover {
  color: #f2fbfa; border-color: rgba(167, 232, 222, 0.4);
  background: rgba(167, 232, 222, 0.18);
}

/* 输入区 */
.composer { padding: 6px 22px 18px; }
.input-wrap {
  display: flex; align-items: center; gap: 10px;
  height: 54px; padding: 0 7px 0 17px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--stroke);
  transition: border-color 0.25s, box-shadow 0.25s;
}
.input-wrap:focus-within {
  border-color: rgba(47, 143, 136, 0.6);
  box-shadow: 0 0 0 4px rgba(47, 143, 136, 0.12), 0 18px 40px -26px rgba(47, 143, 136, 0.9);
}
.input-icon { color: var(--text-faint); flex-shrink: 0; }
.input-wrap input {
  flex: 1; border: 0; outline: 0; background: transparent;
  color: var(--text); font-size: 14px; font-family: inherit;
}
.input-wrap input::placeholder { color: var(--text-faint); }
.send {
  width: 42px; height: 42px; border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.4); cursor: pointer; color: var(--cta-fg);
  background: var(--cta-bg);
  box-shadow: 0 12px 26px -16px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transition: transform 0.2s var(--ease), box-shadow 0.2s;
}
.send:hover { transform: translateY(-1px) scale(1.03); box-shadow: 0 18px 34px -16px rgba(2, 20, 22, 1), inset 0 1px 0 rgba(255, 255, 255, 0.8); }
.composer-tip { margin: 9px 0 0; font-size: 11px; color: var(--text-faint); text-align: right; }

@media (max-width: 720px) {
  .chat { height: calc(100vh - 150px); border-radius: 16px; }
  .bubble { max-width: 82%; }
}
</style>
