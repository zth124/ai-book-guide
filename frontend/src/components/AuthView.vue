<template>
  <div class="auth">
    <div class="auth-shell">
      <!-- 左侧品牌区 -->
      <aside class="aside">
        <div class="brand">
          <span class="brand-mark"><Icon name="book" :size="20" /></span>
          <span class="brand-type">
            <strong>BookWise</strong>
            <em>AI 图书导购</em>
          </span>
        </div>

        <div class="aside-copy">
          <h1>把选书这件事<br /><span class="grad-text">交给 AI</span></h1>
          <p>登录后，你的书单、购物车和订单都会记在这个账号下，换设备登录也能接着用。</p>
        </div>

        <ul class="features">
          <li>
            <span class="fi"><Icon name="sparkles" :size="15" /></span>
            <div><strong>像和人聊天一样选书</strong><em>说清基础、方向和预算，方案出来还能接着改</em></div>
          </li>
          <li>
            <span class="fi"><Icon name="search" :size="15" /></span>
            <div><strong>价格和库存当场看清</strong><em>比价、库存、优惠、物流，选书时一起给你</em></div>
          </li>
          <li>
            <span class="fi"><Icon name="shield" :size="15" /></span>
            <div><strong>书单跟着账号走</strong><em>购物车和订单一并留存，换台设备登录也在</em></div>
          </li>
        </ul>
      </aside>

      <!-- 右侧表单 -->
      <div class="panel-stage">
        <span class="stage-glow" aria-hidden="true"></span>
        <span class="stage-ring r1" aria-hidden="true"></span>
        <span class="stage-ring r2" aria-hidden="true"></span>
        <section class="panel glass">
        <div class="panel-head">
          <h2>{{ isLogin ? '登录账号' : '创建账号' }}</h2>
          <p>{{ isLogin ? '欢迎回来，继续你的选书计划' : '注册后即可保存书单、购物车与订单' }}</p>
        </div>

        <div class="segmented" role="tablist">
          <span class="thumb" :style="{ transform: isLogin ? 'translateX(0)' : 'translateX(100%)' }"></span>
          <button role="tab" :aria-selected="isLogin" :class="{ on: isLogin }" @click="switchMode('login')">登录</button>
          <button role="tab" :aria-selected="!isLogin" :class="{ on: !isLogin }" @click="switchMode('register')">注册</button>
        </div>

        <form class="form" @submit.prevent="submit">
          <label class="field">
            <span class="label">用户名</span>
            <div class="control" :class="{ invalid: nameError }">
              <Icon name="user" :size="16" class="ctl-icon" />
              <input
                v-model="name"
                type="text"
                maxlength="20"
                autocomplete="username"
                placeholder="2-20 个字，例如：张小明"
                @input="nameError = ''"
              />
              <span class="counter">{{ name.length }}/20</span>
            </div>
            <span v-if="nameError" class="field-error">{{ nameError }}</span>
          </label>

          <label class="field">
            <span class="label">密码</span>
            <div class="control" :class="{ invalid: pwdError }">
              <Icon name="key" :size="16" class="ctl-icon" />
              <input
                v-model="password"
                :type="showPwd ? 'text' : 'password'"
                maxlength="32"
                :autocomplete="isLogin ? 'current-password' : 'new-password'"
                placeholder="6-32 位，区分大小写"
                @input="pwdError = ''"
              />
              <button type="button" class="eye" :aria-label="showPwd ? '隐藏密码' : '显示密码'" @click="showPwd = !showPwd">
                <Icon :name="showPwd ? 'eyeOff' : 'eye'" :size="16" />
              </button>
            </div>
            <span v-if="pwdError" class="field-error">{{ pwdError }}</span>
          </label>

          <label v-if="!isLogin" class="field">
            <span class="label">确认密码</span>
            <div class="control" :class="{ invalid: confirmError }">
              <Icon name="check" :size="16" class="ctl-icon" />
              <input
                v-model="confirm"
                :type="showPwd ? 'text' : 'password'"
                maxlength="32"
                autocomplete="new-password"
                placeholder="再输入一次密码"
                @input="confirmError = ''"
              />
            </div>
            <span v-if="confirmError" class="field-error">{{ confirmError }}</span>
          </label>

          <p v-if="error" class="alert">
            <Icon name="close" :size="14" />
            <span>{{ error }}</span>
          </p>

          <button type="submit" class="submit" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '处理中…' : (isLogin ? '登录并进入书城' : '注册并进入书城') }}
            <Icon v-if="!loading" name="arrow" :size="16" />
          </button>
        </form>

        <p class="fine">
          {{ isLogin ? '还没有账号？点上面的「注册」建一个。' : '注册会创建独立账号，购物车与订单各自分开。' }}
        </p>
      </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Icon from './Icon.vue'
import { api } from '../api'

const emit = defineEmits(['auth'])

const mode = ref('login')
const isLogin = computed(() => mode.value === 'login')

const name = ref('')
const password = ref('')
const confirm = ref('')
const showPwd = ref(false)
const loading = ref(false)
const error = ref('')

const nameError = ref('')
const pwdError = ref('')
const confirmError = ref('')

const switchMode = (m) => {
  if (mode.value === m) return
  mode.value = m
  error.value = ''
  nameError.value = ''
  pwdError.value = ''
  confirmError.value = ''
  confirm.value = ''
}

const validate = () => {
  let ok = true
  const n = name.value.trim()
  if (n.length < 2) { nameError.value = '用户名至少 2 个字'; ok = false }
  if (n.length > 20) { nameError.value = '用户名不能超过 20 个字'; ok = false }
  if (password.value.length < 6) { pwdError.value = '密码至少 6 位'; ok = false }
  if (password.value.length > 32) { pwdError.value = '密码不能超过 32 位'; ok = false }
  if (!isLogin.value && confirm.value !== password.value) {
    confirmError.value = '两次输入的密码不一致'
    ok = false
  }
  return ok
}

const submit = async () => {
  error.value = ''
  if (!validate()) return

  loading.value = true
  try {
    const path = isLogin.value ? '/api/users/login' : '/api/users/register'
    const data = await api(path, {
      method: 'POST',
      body: JSON.stringify({
        name: name.value.trim(),
        password: password.value
      })
    })
    emit('auth', data.data)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}
.auth-shell {
  width: 100%;
  max-width: 1040px;
  display: grid;
  grid-template-columns: 1.02fr 0.98fr;
  gap: 44px;
  align-items: center;
}

/* ---------- 左侧品牌 ---------- */
.aside { padding: 8px 4px; animation: fadeUp 0.6s var(--ease) both; }
.brand { display: flex; align-items: center; gap: 11px; }
.brand-mark {
  width: 42px; height: 42px; border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  background: var(--mark-bg);
  color: #06282b;
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 14px 30px -16px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.brand-type { display: flex; flex-direction: column; line-height: 1.25; }
.brand-type strong { font-size: 17px; letter-spacing: -0.02em; }
.brand-type em { font-style: normal; font-size: 10.5px; color: var(--text-faint); letter-spacing: 0.1em; }

.aside-copy { margin-top: 34px; }
.aside-copy h1 {
  margin: 0;
  font-size: clamp(32px, 3.6vw, 46px);
  line-height: 1.12;
  letter-spacing: -0.04em;
  font-weight: 800;
}
.aside-copy p {
  margin: 16px 0 0;
  max-width: 420px;
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--text-dim);
}

.features { list-style: none; margin: 30px 0 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.features li { display: flex; align-items: flex-start; gap: 12px; }
.fi {
  width: 30px; height: 30px; border-radius: 9px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #b8e9e0;
  background: rgba(47, 143, 136, 0.12);
  border: 1px solid rgba(47, 143, 136, 0.28);
}
.features strong { display: block; font-size: 13px; font-weight: 600; letter-spacing: -0.01em; }
.features em { display: block; margin-top: 3px; font-style: normal; font-size: 11.5px; line-height: 1.6; color: var(--text-faint); }

/* ---------- 右侧表单 ---------- */
.panel {
  padding: 28px 30px 24px;
  animation: cardIn 0.55s var(--ease) both;
}

/* 卡片背后的光晕与细圆环，做出“玻璃浮在光里”的层次 */
.panel-stage { position: relative; display: flex; }
.panel-stage .panel { position: relative; z-index: 1; width: 100%; }
.stage-glow {
  position: absolute; inset: -46px -34px;
  background: radial-gradient(58% 56% at 62% 26%, rgba(47, 143, 136, 0.48), transparent 72%);
  filter: blur(42px);
  pointer-events: none;
}
.stage-ring {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid rgba(214, 242, 239, 0.12);
  pointer-events: none;
}
.stage-ring.r1 { width: 408px; height: 408px; }
.stage-ring.r2 { width: 512px; height: 512px; border-color: rgba(214, 242, 239, 0.07); }
.panel.glass {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.092), rgba(255, 255, 255, 0.03) 48%, rgba(255, 255, 255, 0.015)),
    radial-gradient(120% 72% at 38% 0%, rgba(167, 232, 222, 0.12), transparent 62%);
  box-shadow:
    0 50px 100px -60px rgba(2, 20, 22, 0.95),
    inset 0 1px 0 rgba(255, 255, 255, 0.24),
    inset 0 56px 86px -60px rgba(255, 255, 255, 0.26);
}
.panel-head h2 { margin: 0; font-size: 21px; letter-spacing: -0.025em; }
.panel-head p { margin: 7px 0 0; font-size: 12.5px; color: var(--text-dim); }

.segmented {
  position: relative;
  display: grid; grid-template-columns: 1fr 1fr;
  margin: 22px 0 20px;
  padding: 4px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--stroke);
}
.thumb {
  position: absolute;
  top: 4px; left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  border-radius: 10px;
  background: rgba(167, 232, 222, 0.2);
  border: 1px solid rgba(167, 232, 222, 0.32);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.24);
  transition: transform 0.32s var(--ease);
}
.segmented button {
  position: relative; z-index: 1;
  padding: 9px 0; border: 0; background: transparent; cursor: pointer;
  font-size: 13px; font-family: inherit; font-weight: 600;
  color: var(--text-dim);
  transition: color 0.25s;
}
.segmented button.on { color: #fff; }

.form { display: flex; flex-direction: column; gap: 15px; }
.field { display: block; }
.label { display: block; margin-bottom: 7px; font-size: 11.5px; color: var(--text-faint); letter-spacing: 0.06em; }
.control {
  display: flex; align-items: center; gap: 10px;
  height: 48px; padding: 0 13px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--stroke);
  color: var(--text-faint);
  transition: border-color 0.22s, box-shadow 0.22s, background 0.22s;
}
.control:focus-within {
  border-color: rgba(47, 143, 136, 0.6);
  background: rgba(47, 143, 136, 0.06);
  box-shadow: 0 0 0 4px rgba(47, 143, 136, 0.11);
}
.control.invalid { border-color: rgba(251, 113, 133, 0.6); box-shadow: 0 0 0 4px rgba(251, 113, 133, 0.09); }
.ctl-icon { flex-shrink: 0; }
.control input {
  flex: 1; min-width: 0; height: 100%;
  border: 0; outline: 0; background: transparent;
  color: var(--text); font-size: 14px; font-family: inherit;
}
.control input::placeholder { color: var(--text-faint); }
.counter { font-size: 10.5px; color: var(--text-faint); font-variant-numeric: tabular-nums; }
.eye {
  width: 30px; height: 30px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: 0; border-radius: 9px; cursor: pointer;
  background: transparent; color: var(--text-faint);
  transition: color 0.2s, background 0.2s;
}
.eye:hover { color: var(--text); background: rgba(255, 255, 255, 0.07); }
.field-error { display: block; margin-top: 6px; font-size: 11.5px; color: var(--danger); }

.alert {
  display: flex; align-items: flex-start; gap: 8px;
  margin: 2px 0 0; padding: 10px 13px;
  border-radius: 11px;
  font-size: 12.5px; line-height: 1.55; color: #fda4af;
  background: rgba(251, 113, 133, 0.1);
  border: 1px solid rgba(251, 113, 133, 0.28);
  animation: fadeUp 0.25s var(--ease) both;
}

.submit {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  height: 50px; margin-top: 4px;
  border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 14px; cursor: pointer;
  font-size: 14px; font-family: inherit; font-weight: 700; color: var(--cta-fg);
  background: var(--cta-bg);
  box-shadow: 0 18px 38px -20px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transition: transform 0.2s var(--ease), box-shadow 0.2s, opacity 0.2s;
}
.submit:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 24px 44px -20px rgba(2, 20, 22, 1), inset 0 1px 0 rgba(255, 255, 255, 0.8); }
.submit:disabled { opacity: 0.7; cursor: default; }
.spinner {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}

.fine { margin: 16px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--text-faint); }

@media (max-width: 900px) {
  .auth { padding: 20px 16px; align-items: flex-start; }
  .auth-shell { grid-template-columns: 1fr; gap: 16px; max-width: 460px; }
  .stage-glow { display: none; }
  .stage-ring.r2 { display: none; }
  .stage-ring.r1 { width: 340px; height: 340px; }
  /* 窄屏只留品牌行 + 表单，保证提交按钮不用滚动就能看到 */
  .aside-copy, .features { display: none; }
  .panel { padding: 22px 20px 18px; }
}
</style>
