<template>
  <div class="cart glass">
    <div class="cart-head">
      <div class="head-left">
        <div class="head-icon"><Icon name="cart" :size="18" /></div>
        <div class="head-meta">
          <h2>购物车</h2>
          <span>{{ cartItems.length }} 件商品 · 已选 {{ selected.length }}</span>
        </div>
      </div>
      <button class="orders-link" @click="emit('orders')">
        我的订单 <Icon name="arrow" :size="14" />
      </button>
    </div>

    <div v-if="errMsg" class="cart-err">{{ errMsg }}</div>

    <div v-if="cartItems.length === 0" class="empty">
      <div class="empty-icon"><Icon name="cart" :size="26" /></div>
      <p>购物车还是空的</p>
      <span>去 AI 导购说一句需求，让它帮你配一套书单</span>
    </div>

    <template v-else>
      <div class="selectbar">
        <label class="check">
          <input type="checkbox" :checked="allSelected" @change="toggleAll($event.target.checked)" />
          <span class="box"><Icon name="check" :size="11" /></span>
          <span class="check-label">全选</span>
        </label>
      </div>

      <div class="rows">
        <div v-for="item in cartItems" :key="item.cart_item_id" class="row">
          <label class="check">
            <input type="checkbox" :value="item.cart_item_id" v-model="selected" @change="onSelectChange" />
            <span class="box"><Icon name="check" :size="11" /></span>
          </label>
          <div class="cover"><Icon name="book" :size="17" /></div>
          <div class="info">
            <span class="title">{{ item.title }}</span>
            <span class="sub">数量 × {{ item.qty }}</span>
          </div>
          <span class="subtotal">￥{{ money(item.subtotal) }}</span>
        </div>
      </div>

      <div v-if="summary.coupon" class="coupon">
        <Icon name="tag" :size="14" />
        <span>{{ summary.coupon.applicable ? '已使用' : '未达使用门槛' }}：{{ summary.coupon.name }}</span>
        <button class="coupon-x" @click="clearCoupon">不使用</button>
      </div>

      <div class="foot">
        <div class="sum">
          <div class="line"><span>商品合计</span><span>￥{{ money(summary.original_total) }}</span></div>
          <div v-if="summary.saved > 0" class="line saved"><span>优惠券</span><span>-￥{{ money(summary.saved) }}</span></div>
          <div class="line total"><span>实付</span><strong>￥{{ money(summary.total) }}</strong></div>
        </div>
        <button class="btn btn-primary checkout" :disabled="selected.length === 0" @click="checkout">
          结算 {{ selected.length }} 件 <Icon name="arrow" :size="15" />
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import Icon from './Icon.vue'

const props = defineProps({
  userId: { type: Number, required: true }
})
const emit = defineEmits(['orders'])

const cartItems = ref([])
const selected = ref([])
const errMsg = ref('')
const summary = ref({ original_total: 0, total: 0, saved: 0, coupon: null })

const money = (v) => Number(v || 0).toFixed(2)
const pendingCouponId = () => localStorage.getItem('pending_coupon_id')

const allSelected = computed(() =>
  cartItems.value.length > 0 && selected.value.length === cartItems.value.length)

const fetchSummary = async () => {
  // 一件都没勾选：金额直接归零，不去打扰后端
  if (selected.value.length === 0) {
    summary.value = { original_total: 0, total: 0, saved: 0, coupon: null }
    return
  }
  const couponId = pendingCouponId()
  const q = []
  if (couponId) q.push(`coupon_id=${couponId}`)
  q.push(`item_ids=${selected.value.join(',')}`)
  try {
    const data = await api(`/api/cart/${props.userId}/summary?${q.join('&')}`)
    summary.value = data.data
    // 只有券彻底不存在/已过期才清本地标记；仅仅这次勾选金额没到门槛时保留券
    if (!summary.value.coupon) localStorage.removeItem('pending_coupon_id')
  } catch (e) {
    errMsg.value = e.message
  }
}

const onSelectChange = () => { fetchSummary() }

const toggleAll = (checked) => {
  selected.value = checked ? cartItems.value.map(i => i.cart_item_id) : []
  fetchSummary()
}

const fetchCart = async () => {
  errMsg.value = ''
  try {
    const data = await api(`/api/cart/${props.userId}`)
    cartItems.value = data.data || []
  } catch (e) {
    errMsg.value = e.message
    cartItems.value = []
  }
  // 默认全选；下单后购物车变化，重新对齐一次
  selected.value = cartItems.value.map(i => i.cart_item_id)
  await fetchSummary()
}

const clearCoupon = async () => {
  localStorage.removeItem('pending_coupon_id')
  await fetchSummary()
}

const checkout = async () => {
  if (selected.value.length === 0) {
    alert('请先勾选要结算的图书')
    return
  }
  try {
    const couponId = pendingCouponId()
    const url = couponId
      ? `/api/orders/create/${props.userId}?coupon_id=${couponId}`
      : `/api/orders/create/${props.userId}`
    const data = await api(url, {
      method: 'POST',
      body: JSON.stringify({ item_ids: selected.value })
    })
    const d = data.data
    localStorage.removeItem('pending_coupon_id')
    await fetchCart()
    alert(`订单创建成功！订单号 #${d.order_id}，实付 ￥${money(d.total)}。支付环节由你完成。`)
    emit('orders')
  } catch (e) {
    alert(`下单失败：${e.message}`)
  }
}

onMounted(() => { fetchCart() })
</script>

<style scoped>
.cart {
  max-width: 860px;
  margin: 0 auto;
  overflow: hidden;
}

.cart-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 20px 24px;
  border-bottom: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.025);
}
.head-left { display: flex; align-items: center; gap: 13px; }
.head-icon {
  width: 38px; height: 38px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--mark-bg);
  color: #06282b;
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 12px 26px -16px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.head-meta h2 { margin: 0; font-size: 18px; letter-spacing: -0.02em; }
.head-meta span { font-size: 11.5px; color: var(--text-faint); }
.orders-link {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 16px; border-radius: 999px; cursor: pointer;
  font-size: 12.5px; font-family: inherit; font-weight: 600;
  color: #b8e9e0;
  background: rgba(47, 143, 136, 0.12);
  border: 1px solid rgba(47, 143, 136, 0.3);
  transition: all 0.2s var(--ease);
}
.orders-link:hover { color: #fff; background: rgba(47, 143, 136, 0.28); }

.cart-err {
  margin: 14px 24px 0; padding: 10px 14px; border-radius: 10px;
  font-size: 12.5px; color: var(--danger);
  background: rgba(251, 113, 133, 0.1);
  border: 1px solid rgba(251, 113, 133, 0.3);
}

.empty { padding: 70px 24px 80px; text-align: center; }
.empty-icon {
  width: 64px; height: 64px; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 18px; color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--stroke);
}
.empty p { margin: 0; font-size: 15px; font-weight: 600; }
.empty span { display: block; margin-top: 7px; font-size: 12.5px; color: var(--text-faint); }

.selectbar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px; padding: 14px 24px;
  border-bottom: 1px solid var(--stroke);
  font-size: 12px; color: var(--text-faint);
}

/* 自定义勾选框 */
.check { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.check input { position: absolute; opacity: 0; width: 0; height: 0; }
.check .box {
  width: 18px; height: 18px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--stroke-2);
  background: rgba(255, 255, 255, 0.04);
  color: transparent;
  transition: all 0.18s var(--ease);
}
.check input:checked + .box {
  border-color: rgba(255, 255, 255, 0.4);
  background: var(--mark-bg);
  color: #06282b;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
}
.check-label { font-size: 12.5px; color: var(--text-dim); font-weight: 500; }

.rows { padding: 4px 0; }
.row {
  display: flex; align-items: center; gap: 14px;
  padding: 15px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.045);
  transition: background 0.2s;
}
.row:hover { background: rgba(255, 255, 255, 0.025); }
.cover {
  width: 42px; height: 54px; border-radius: 8px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #06282b;
  background: var(--mark-bg);
  border: 1px solid rgba(255, 255, 255, 0.34);
  box-shadow: 0 12px 24px -16px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.5);
}
.info { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.title { font-size: 13.5px; font-weight: 600; }
.sub { font-size: 11.5px; color: var(--text-faint); }
.subtotal { font-size: 14.5px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }

.coupon {
  display: flex; align-items: center; gap: 8px;
  margin: 14px 24px; padding: 10px 14px;
  border-radius: 11px; font-size: 12px; color: #f0d5ce;
  background: linear-gradient(90deg, rgba(223, 182, 174, 0.14), rgba(223, 182, 174, 0.03));
  border: 1px solid rgba(223, 182, 174, 0.26);
}
.coupon-x {
  margin-left: auto; padding: 3px 9px; border-radius: 8px; cursor: pointer;
  font-size: 11px; font-family: inherit;
  color: #f6e3dd; background: transparent;
  border: 1px solid rgba(223, 182, 174, 0.3);
}
.coupon-x:hover { background: rgba(223, 182, 174, 0.16); }

.foot {
  display: flex; align-items: flex-end; justify-content: flex-end;
  gap: 30px; padding: 20px 24px 22px;
  background: rgba(255, 255, 255, 0.03);
  border-top: 1px solid var(--stroke);
}
.sum { display: flex; flex-direction: column; gap: 7px; flex: 0 0 auto; align-items: flex-end; }
.line {
  display: flex; justify-content: flex-end; gap: 22px; align-items: baseline;
  font-size: 12.5px; color: var(--text-dim);
}
.line.saved { color: var(--ok); }
.line.total { align-items: baseline; margin-top: 3px; }
.line.total span { font-size: 12.5px; }
.line.total strong { font-size: 23px; font-weight: 700; letter-spacing: -0.02em; color: #fff; }
.checkout { padding: 14px 26px; border-radius: 14px; }
.checkout:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }

@media (max-width: 640px) {
  .foot { flex-direction: column; align-items: stretch; }
  .checkout { width: 100%; }
}
</style>
