<template>
  <div class="profile">
    <div class="p-grid">
      <!-- 左：身份卡 -->
      <section class="identity glass">
        <div class="cover"></div>

        <div class="id-body">
          <div class="avatar-wrap">
            <button class="avatar" :disabled="uploading" @click="pickFile" title="点击更换头像">
              <img v-if="avatarSrc" :src="avatarSrc" alt="头像" />
              <span v-else class="initial">{{ initial }}</span>
              <span class="cam"><Icon name="camera" :size="15" /></span>
              <span v-if="uploading" class="loading-mask"><span class="spinner"></span></span>
            </button>
            <span class="id-badge">ID {{ user.id }}</span>
          </div>

          <div class="id-text">
            <h2>{{ user.name }}</h2>
            <p>{{ profile.created_at ? `注册于 ${profile.created_at}` : '账号已创建' }}</p>
          </div>

          <div class="stats">
            <div class="stat">
              <strong>{{ profile.order_count ?? '—' }}</strong>
              <span>订单</span>
            </div>
            <div class="stat">
              <strong>{{ profile.cart_qty ?? '—' }}</strong>
              <span>购物车件数</span>
            </div>
            <div class="stat">
              <strong>￥{{ money(profile.spent) }}</strong>
              <span>累计消费</span>
            </div>
          </div>

          <button class="avatar-btn" :disabled="uploading" @click="pickFile">
            <Icon name="camera" :size="15" />
            {{ uploading ? '上传中…' : '更换头像' }}
          </button>
          <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="file" @change="onFile" />
          <p v-if="avatarMsg" :class="['tip', avatarOk ? 'ok' : 'bad']">{{ avatarMsg }}</p>
        </div>
      </section>

      <!-- 右：设置 -->
      <div class="side">
        <section class="card glass">
          <div class="card-head">
            <span class="card-icon"><Icon name="pencil" :size="16" /></span>
            <div>
              <h3>修改用户名</h3>
            </div>
          </div>

          <div class="name-row">
            <div class="control" :class="{ invalid: !!nameError }">
              <Icon name="user" :size="15" />
              <input v-model="formName" maxlength="20" placeholder="2-20 个字" @input="onNameInput" @keyup.enter="saveName" />
              <span class="counter">{{ formName.length }}/20</span>
            </div>
            <button class="save" :disabled="saving || !nameDirty" @click="saveName">
              <span v-if="saving" class="spinner"></span>
              {{ saving ? '保存中' : '保存' }}
            </button>
          </div>
          <p v-if="nameError" class="tip bad">{{ nameError }}</p>
        </section>

        <section class="card glass">
          <div class="card-head">
            <span class="card-icon"><Icon name="shield" :size="16" /></span>
            <div>
              <h3>账号信息</h3>
            </div>
          </div>
          <div class="kv">
            <div class="kv-row"><span>账号 ID</span><strong>{{ user.id }}</strong></div>
            <div class="kv-row"><span>用户名</span><strong>{{ user.name }}</strong></div>
            <div class="kv-row"><span>头像状态</span><strong>{{ user.avatar ? '已上传自定义头像' : '默认首字母头像' }}</strong></div>
          </div>
          <div class="row-actions">
            <button class="ghost" @click="emit('cart')"><Icon name="cart" :size="14" /> 购物车</button>
            <button class="ghost" @click="emit('orders')"><Icon name="receipt" :size="14" /> 我的订单</button>
            <button v-if="user.avatar" class="ghost danger" @click="removeAvatar">
              <Icon name="close" :size="14" /> 恢复默认头像
            </button>
          </div>
        </section>

        <section class="card glass danger-zone">
          <div class="card-head">
            <span class="card-icon"><Icon name="logout" :size="16" /></span>
            <div>
              <h3>退出登录</h3>
            </div>
          </div>
          <button class="logout-btn" @click="emit('logout')">
            <Icon name="logout" :size="15" /> 退出当前账号
          </button>
        </section>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Icon from './Icon.vue'
import { api, avatarUrl } from '../api'

const props = defineProps({
  user: { type: Object, required: true }
})
const emit = defineEmits(['update', 'cart', 'orders', 'logout'])

const profile = ref({})
const formName = ref(props.user.name || '')
const saving = ref(false)
const nameError = ref('')

const fileInput = ref(null)
const uploading = ref(false)
const avatarMsg = ref('')
const avatarOk = ref(true)
const toast = ref('')
let toastTimer = null

const initial = computed(() => (props.user.name || '书').slice(0, 1))
const avatarSrc = computed(() => avatarUrl(props.user))
const money = (v) => Number(v || 0).toFixed(2)
const nameDirty = computed(() => formName.value.trim() !== (props.user.name || ''))

const flash = (msg) => {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2200)
}

// 行内提示（头像/用户名）几秒后自动消失，避免一直挂在那里
let tipTimer = null
const flashTip = (msg, ok = true) => {
  avatarOk.value = ok
  avatarMsg.value = msg
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { avatarMsg.value = '' }, 3200)
}

const loadProfile = async () => {
  try {
    const data = await api(`/api/users/${props.user.id}`)
    profile.value = data.data
    if (data.data.name !== props.user.name || (data.data.avatar || '') !== (props.user.avatar || '')) {
      // 以服务端为准：用户名或头像可能已在别处改过，同步回本地缓存与导航
      emit('update', { ...props.user, name: data.data.name, avatar: data.data.avatar })
    }
  } catch (e) {
    // 拉不到统计不影响页面使用，静默处理
  }
}

const onNameInput = () => {
  nameError.value = ''
}

const saveName = async () => {
  const next = formName.value.trim()
  if (next === props.user.name) return
  if (next.length < 2) { nameError.value = '用户名至少 2 个字'; return }
  if (next.length > 20) { nameError.value = '用户名不能超过 20 个字'; return }

  saving.value = true
  nameError.value = ''
  try {
    const data = await api(`/api/users/${props.user.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ name: next })
    })
    emit('update', { ...props.user, name: data.data.name, avatar: data.data.avatar })
    formName.value = data.data.name
    flash('用户名已保存')
    await loadProfile()
  } catch (e) {
    nameError.value = e.message
  } finally {
    saving.value = false
  }
}

const pickFile = () => {
  if (uploading.value) return
  avatarMsg.value = ''
  fileInput.value && fileInput.value.click()
}

// 本地压缩：居中裁正方形 → 512px JPEG，既保证头像清晰，又避免上传大图
const compress = (file, size = 512) => new Promise((resolve, reject) => {
  const url = URL.createObjectURL(file)
  const img = new Image()
  img.onload = () => {
    const s = Math.min(img.width, img.height)
    const sx = (img.width - s) / 2
    const sy = (img.height - s) / 2
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, sx, sy, s, s, 0, 0, size, size)
    URL.revokeObjectURL(url)
    resolve(canvas.toDataURL('image/jpeg', 0.86))
  }
  img.onerror = () => {
    URL.revokeObjectURL(url)
    reject(new Error('图片读取失败，请换一张试试'))
  }
  img.src = url
})

const onFile = async (e) => {
  const file = e.target.files && e.target.files[0]
  e.target.value = ''   // 允许重复选择同一张图
  if (!file) return
  if (!file.type.startsWith('image/')) {
    flashTip('请选择一张图片', false)
    return
  }
  if (file.size > 8 * 1024 * 1024) {
    flashTip('图片太大了，换一张小一点的', false)
    return
  }

  uploading.value = true
  avatarMsg.value = ''
  try {
    const dataUrl = await compress(file)
    const data = await api(`/api/users/${props.user.id}/avatar`, {
      method: 'POST',
      body: JSON.stringify({ avatar: dataUrl })
    })
    emit('update', { ...props.user, name: data.data.name, avatar: data.data.avatar })
    flash('头像已更新')
  } catch (err) {
    flashTip(err.message, false)
  } finally {
    uploading.value = false
  }
}

const removeAvatar = async () => {
  try {
    const data = await api(`/api/users/${props.user.id}/avatar`, { method: 'DELETE' })
    emit('update', { ...props.user, name: data.data.name, avatar: '' })
    flashTip('已恢复默认头像')
    flash('已恢复默认头像')
  } catch (e) {
    flashTip(e.message, false)
  }
}

onMounted(loadProfile)
</script>

<style scoped>
.profile { max-width: 1040px; margin: 0 auto; }
.p-grid {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 20px;
  align-items: start;
}

/* ---------- 身份卡 ---------- */
.identity { overflow: hidden; animation: cardIn 0.5s var(--ease) both; }
.cover {
  height: 92px;
  background:
    radial-gradient(90% 150% at 16% 0%, rgba(47, 143, 136, 0.75), transparent 64%),
    radial-gradient(80% 140% at 88% 6%, rgba(223, 182, 174, 0.4), transparent 68%),
    linear-gradient(160deg, #0e2f34, #06161b);
  border-bottom: 1px solid rgba(214, 242, 239, 0.12);
}
.id-body { padding: 0 22px 22px; }

.avatar-wrap { display: flex; align-items: flex-end; gap: 10px; margin-top: -46px; }
.avatar {
  position: relative;
  width: 96px; height: 96px; flex-shrink: 0;
  border-radius: 50%; padding: 0; cursor: pointer;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: var(--mark-bg);
  box-shadow: 0 22px 46px -24px rgba(2, 20, 22, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.6);
  color: #06282b;
  transition: transform 0.22s var(--ease), border-color 0.22s;
}
.avatar:hover { transform: translateY(-2px); border-color: rgba(255, 255, 255, 0.3); }
.avatar img { width: 100%; height: 100%; object-fit: cover; display: block; }
.initial { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; font-size: 34px; font-weight: 700; }
.cam {
  position: absolute; inset: auto 0 0 0;
  height: 30px;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  background: linear-gradient(180deg, transparent, rgba(6, 8, 15, 0.72));
  opacity: 0;
  transition: opacity 0.2s;
}
.avatar:hover .cam { opacity: 1; }
.loading-mask {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(6, 8, 15, 0.6);
}
.spinner {
  width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}
.id-badge {
  margin-bottom: 4px;
  padding: 4px 10px; border-radius: 999px;
  font-size: 10.5px; color: #b8e9e0;
  background: rgba(47, 143, 136, 0.14);
  border: 1px solid rgba(47, 143, 136, 0.28);
}

.id-text { margin-top: 14px; }
.id-text h2 { margin: 0; font-size: 20px; letter-spacing: -0.025em; word-break: break-all; }
.id-text p { margin: 6px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--text-faint); }

.stats {
  display: grid; grid-template-columns: repeat(3, 1fr);
  margin-top: 18px; padding: 14px 0;
  border-top: 1px solid var(--stroke);
  border-bottom: 1px solid var(--stroke);
}
.stat { text-align: center; }
.stat strong { display: block; font-size: 16px; font-weight: 800; letter-spacing: -0.02em; color: #fff; font-variant-numeric: tabular-nums; }
.stat span { display: block; margin-top: 4px; font-size: 10.5px; color: var(--text-faint); }

.avatar-btn {
  width: 100%; margin-top: 16px;
  display: flex; align-items: center; justify-content: center; gap: 7px;
  height: 42px; border-radius: 12px; cursor: pointer;
  font-size: 12.5px; font-family: inherit; font-weight: 600;
  color: #b8e9e0;
  background: rgba(47, 143, 136, 0.12);
  border: 1px solid rgba(47, 143, 136, 0.3);
  transition: all 0.2s var(--ease);
}
.avatar-btn:hover:not(:disabled) { color: #fff; background: rgba(47, 143, 136, 0.28); }
.avatar-btn:disabled { opacity: 0.6; cursor: default; }
.file { display: none; }
/* ---------- 右侧卡片 ---------- */
.side { display: flex; flex-direction: column; gap: 16px; }
.card { padding: 20px 22px; animation: cardIn 0.55s var(--ease) both; }
.card-head { display: flex; gap: 12px; align-items: center; }
.card-icon {
  width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #b8e9e0;
  background: rgba(47, 143, 136, 0.13);
  border: 1px solid rgba(47, 143, 136, 0.28);
}
.card-head h3 { margin: 0; font-size: 14.5px; letter-spacing: -0.01em; }
.card-head p { margin: 5px 0 0; font-size: 11.5px; line-height: 1.65; color: var(--text-faint); }

.name-row { display: flex; gap: 10px; margin-top: 16px; }
.control {
  flex: 1; display: flex; align-items: center; gap: 9px;
  height: 46px; padding: 0 13px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--stroke);
  color: var(--text-faint);
  transition: border-color 0.22s, box-shadow 0.22s;
}
.control:focus-within { border-color: rgba(47, 143, 136, 0.55); box-shadow: 0 0 0 4px rgba(47, 143, 136, 0.1); }
.control.invalid { border-color: rgba(251, 113, 133, 0.6); }
.control input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--text); font-size: 13.5px; font-family: inherit; }
.control input::placeholder { color: var(--text-faint); }
.counter { font-size: 10.5px; color: var(--text-faint); font-variant-numeric: tabular-nums; }

.save {
  flex: 0 0 auto;
  padding: 0 22px; border-radius: 12px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.4);
  font-size: 13px; font-family: inherit; font-weight: 700; color: var(--cta-fg);
  background: var(--cta-bg);
  box-shadow: 0 14px 30px -18px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transition: transform 0.2s var(--ease), opacity 0.2s, background 0.2s, color 0.2s;
}
.save:hover:not(:disabled) { transform: translateY(-1px); }
.save:disabled {
  opacity: 1;
  cursor: not-allowed;
  color: var(--text-faint);
  background: rgba(255, 255, 255, 0.045);
  border-color: var(--stroke);
  box-shadow: none;
}

.kv { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.kv-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 12px; color: var(--text-faint); }
.kv-row strong { font-size: 12.5px; color: var(--text); font-weight: 600; }
.row-actions { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 18px; }
.ghost {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 15px; border-radius: 11px; cursor: pointer;
  font-size: 12px; font-family: inherit; font-weight: 500;
  color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--stroke);
  transition: all 0.2s;
}
.ghost:hover { color: var(--text); border-color: var(--stroke-2); background: var(--surface-2); }
.ghost.danger { color: #fda4af; border-color: rgba(251, 113, 133, 0.28); background: rgba(251, 113, 133, 0.08); }
.ghost.danger:hover { background: rgba(251, 113, 133, 0.16); }

.danger-zone .card-icon { color: #fda4af; background: rgba(251, 113, 133, 0.1); border-color: rgba(251, 113, 133, 0.26); }
.logout-btn {
  width: 100%; margin-top: 16px;
  display: flex; align-items: center; justify-content: center; gap: 7px;
  height: 44px; border-radius: 12px; cursor: pointer;
  font-size: 12.5px; font-family: inherit; font-weight: 600;
  color: #fda4af;
  background: rgba(251, 113, 133, 0.09);
  border: 1px solid rgba(251, 113, 133, 0.28);
  transition: all 0.2s;
}
.logout-btn:hover { background: rgba(251, 113, 133, 0.18); color: #fecdd3; }

.tip { margin: 10px 0 0; font-size: 11.5px; line-height: 1.55; }
.tip.ok { color: var(--ok); }
.tip.bad { color: var(--danger); }
.toast {
  position: fixed; left: 50%; bottom: 36px; transform: translateX(-50%);
  padding: 11px 20px; border-radius: 12px; z-index: 300;
  font-size: 13px; color: var(--text);
  background: rgba(16, 19, 32, 0.94);
  border: 1px solid var(--stroke-2);
  backdrop-filter: blur(18px);
  animation: fadeUp 0.28s var(--ease) both;
}

@media (max-width: 860px) {
  .p-grid { grid-template-columns: 1fr; gap: 16px; }
  .name-row { flex-direction: column; }
  .save { height: 44px; }
}
</style>
