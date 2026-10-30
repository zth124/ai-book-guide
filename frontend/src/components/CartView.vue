<template>
  <div class="cart-container">
    <div class="cart-header">
      <h2>🛒 购物车</h2>
      <span class="count">{{ cartItems.length }} 件商品</span>
    </div>

    <div v-if="cartItems.length === 0" class="empty">
      <div class="empty-icon">🛒</div>
      <p>购物车空空如也~</p>
    </div>

    <div v-else class="cart-body">
      <div v-for="item in cartItems" :key="item.cart_item_id" class="cart-item">
        <div class="item-left">
          <div class="item-book">📖</div>
          <div class="item-info">
            <span class="item-title">{{ item.title }}</span>
            <span class="item-sub">数量 × {{ item.qty }}</span>
          </div>
        </div>
        <span class="item-price">￥{{ item.subtotal }}</span>
      </div>

      <!-- 优惠券提示 -->
      <div v-if="pendingCoupon" class="coupon-row">
        <span class="coupon-info">🎟️ 待使用优惠券：满减券</span>
        <span class="coupon-remove" @click="clearCoupon">✕ 清除</span>
      </div>

      <!-- 结算区 -->
      <div class="cart-footer">
        <div class="price-summary">
          <div class="line"><span>商品合计</span><span>￥{{ originalSum }}</span></div>
          <div v-if="pendingCoupon" class="line saved"><span>优惠券</span><span>-￥{{ savedAmount }}</span></div>
          <div class="line total"><span>实付</span><span>￥{{ totalPrice }}</span></div>
        </div>
        <button class="checkout-btn" @click="checkout">去结算 →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const cartItems = ref([])
const pendingCoupon = ref(false)

const fetchCart = async () => {
  const res = await fetch('/api/cart/1')
  const data = await res.json()
  cartItems.value = data.data
  const couponId = localStorage.getItem('pending_coupon_id')
  pendingCoupon.value = !!couponId
}

const originalSum = computed(() => {
  return cartItems.value.reduce((sum, item) => sum + item.subtotal, 0).toFixed(2)
})

// 简易优惠计算显示（满100减20 / 满150减30）
const savedAmount = computed(() => {
  if (!pendingCoupon.value) return '0.00'
  const sum = parseFloat(originalSum.value)
  if (sum >= 150) return '30.00'
  if (sum >= 100) return '20.00'
  return '0.00'
})

const totalPrice = computed(() => {
  const sum = parseFloat(originalSum.value) - parseFloat(savedAmount.value)
  return sum.toFixed(2)
})

const clearCoupon = () => {
  localStorage.removeItem('pending_coupon_id')
  pendingCoupon.value = false
}

const checkout = async () => {
  if (cartItems.value.length === 0) return
  try {
    const couponId = localStorage.getItem('pending_coupon_id')
    const url = couponId
      ? `/api/orders/create/1?coupon_id=${couponId}`
      : '/api/orders/create/1'
    const res = await fetch(url, { method: 'POST' })
    const data = await res.json()
    if (data.status === 'success') {
      alert(`🎉 订单创建成功！订单号: ${data.order_id}，优惠后金额: ￥${data.total}`)
      localStorage.removeItem('pending_coupon_id')
      pendingCoupon.value = false
      fetchCart()
    }
  } catch (error) {
    alert("下单失败")
  }
}

onMounted(() => { fetchCart() })
</script>

<style scoped>
.cart-container {
  max-width: 780px; margin: 0 auto; padding: 20px;
  background: white; border-radius: 20px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  overflow: hidden;
}
.cart-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid #f3f4f6;
}
.cart-header h2 { margin: 0; font-size: 20px; font-weight: 700; }
.count { font-size: 13px; color: #9ca3af; }

/* 空态 */
.empty {
  text-align: center; padding: 60px 20px; color: #9ca3af;
}
.empty-icon { font-size: 48px; margin-bottom: 14px; }
.empty p { margin: 0; font-size: 14px; }

/* 购物车条目 */
.cart-body { padding: 8px 0 0; }
.cart-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; border-bottom: 1px solid #f3f4f6;
  transition: background .15s;
}
.cart-item:hover { background: #fafafa; }
.item-left { display: flex; gap: 14px; align-items: center; }
.item-book {
  width: 44px; height: 56px; border-radius: 6px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  display: flex; align-items: center; justify-content: center; font-size: 20px;
  flex-shrink: 0;
}
.item-info { display: flex; flex-direction: column; gap: 4px; }
.item-title { font-weight: 600; font-size: 14px; color: #1f2937; }
.item-sub { font-size: 12px; color: #9ca3af; }
.item-price { font-weight: 700; color: #dc2626; font-size: 16px; }

/* 优惠券提示 */
.coupon-row {
  display: flex; justify-content: space-between; align-items: center;
  margin: 12px 24px; padding: 12px 16px;
  background: linear-gradient(90deg, #fef3c7, #fde68a);
  border-radius: 10px; font-size: 13px;
}
.coupon-info { color: #92400e; font-weight: 600; }
.coupon-remove { color: #b45309; cursor: pointer; font-size: 12px; }
.coupon-remove:hover { text-decoration: underline; }

/* 结算 */
.cart-footer {
  display: flex; justify-content: space-between; align-items: flex-end;
  padding: 24px; margin-top: 8px; background: #f9fafb;
  border-top: 1px solid #f3f4f6;
}
.price-summary { display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
.line { display: flex; justify-content: space-between; gap: 30px; color: #6b7280; }
.line.saved { color: #059669; }
.line.total { font-size: 18px; font-weight: 800; color: #dc2626; padding-top: 6px; border-top: 1px dashed #e5e7eb; margin-top: 4px; }
.checkout-btn {
  padding: 14px 32px; border: none; border-radius: 12px; cursor: pointer;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
  font-size: 15px; font-weight: 600;
  box-shadow: 0 4px 16px rgba(99,102,241,0.35);
  transition: transform .15s;
}
.checkout-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
</style>