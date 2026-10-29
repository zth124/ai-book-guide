<template>
  <div class="cart-container">
    <h2>🛒 我的购物车</h2>
    <div v-if="cartItems.length === 0" class="empty">购物车空空如也~</div>

    <div v-else>
      <div v-for="item in cartItems" :key="item.cart_item_id" class="cart-item">
        <span class="title">{{ item.title }}</span>
        <span class="qty">x {{ item.qty }}</span>
        <span class="price">￥{{ item.subtotal }}</span>
      </div>

      <div class="footer">
        <h3>总价: ￥{{ totalPrice }}</h3>
        <button @click="checkout">去结算 (创建订单)</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const cartItems = ref([])

// 获取购物车数据
const fetchCart = async () => {
  const res = await fetch('/api/cart/1') // 固定用户1
  const data = await res.json()
  cartItems.value = data.data
}

// 计算总价
const totalPrice = computed(() => {
  return cartItems.value.reduce((sum, item) => sum + item.subtotal, 0).toFixed(2)
})

// 提交订单
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
      localStorage.removeItem('pending_coupon_id') // 用完后清除
      fetchCart() // 刷新购物车（清空）
    }
  } catch (error) {
    alert("下单失败")
  }
}


onMounted(() => {
  fetchCart()
})
</script>

<style scoped>
.cart-container { max-width: 800px; margin: 0 auto; padding: 20px; }
.cart-item { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #eee; }
.title { flex: 1; font-weight: bold; }
.price { color: #e53935; width: 80px; text-align: right; }
.footer { margin-top: 30px; text-align: right; }
.footer h3 { color: #e53935; }
.footer button { padding: 10px 20px; background: #42b883; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;}
.empty { text-align: center; color: #999; margin-top: 50px; }
</style>