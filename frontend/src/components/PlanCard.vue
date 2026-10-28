<template>
  <div class="plan-card">
    <div class="plan-header">
      <h3>📋 专属购书方案</h3>
      <div class="price-box">
        <span v-if="plan.coupon && plan.coupon.applied" class="original">￥{{ plan.original_total }}</span>
        <span class="budget">实付 ￥{{ plan.total }}</span>
      </div>
    </div>

    <div v-if="plan.coupon && plan.coupon.applied" class="coupon-tip">
      🎟️ 已用券「{{ plan.coupon.name }}」，优惠 ￥{{ plan.coupon.saved }}
    </div>

    <div class="plan-section">
      <h4>💡 推荐理由 & 学习路线</h4>
      <p class="reason">{{ plan.reason }}</p>
      <div class="path-tags">
        <span v-for="(step, index) in plan.path" :key="index" class="tag">{{ step }}</span>
      </div>
    </div>

    <div class="plan-section">
      <h4>📚 图书清单</h4>
      <div class="book-list">
        <div v-for="book in plan.books" :key="book.id" class="book-item">
          <div class="book-main">
            <span class="title">{{ book.title }}</span>
            <div class="meta">
              <span class="rating">⭐ {{ book.rating }}</span>
              <span class="level">{{ book.level }}</span>
              <span :class="book.stock > 0 ? 'stock ok' : 'stock none'">{{ book.stock > 0 ? '有货' : '缺货' }}</span>
            </div>
            <p v-if="book.review_summary" class="review">{{ book.review_summary }}</p>
          </div>
          <span class="price">￥{{ book.price }}</span>
        </div>
      </div>
    </div>

    <div v-if="plan.alternatives && plan.alternatives.length" class="plan-section">
      <h4>🔁 备选方案</h4>
      <div v-for="(alt, i) in plan.alternatives" :key="i" class="alt-item">
        <span class="alt-title">{{ alt.title }}</span>
        <span v-if="alt.price" class="alt-price">￥{{ alt.price }}</span>
        <span class="alt-reason">{{ alt.reason }}</span>
      </div>
    </div>

    <div class="plan-actions">
      <button class="confirm-btn" @click="emit('confirm')">✅ 确认并加入购物车</button>
      <button class="adjust-btn" @click="emit('adjust')">🔄 微调方案</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  plan: {
    type: Object,
    required: true
  }
})
// 定义向父组件发送的事件
const emit = defineEmits(['confirm', 'adjust'])
</script>

<style scoped>
.plan-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  margin: 10px 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  max-width: 500px;
}
.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 15px;
}
.plan-header h3 { margin: 0; color: #35495e; }
.price-box { display: flex; flex-direction: column; align-items: flex-end; }
.budget { color: #e53935; font-weight: bold; font-size: 18px; }
.original { color: #999; font-size: 13px; text-decoration: line-through; }
.coupon-tip {
  background: #fff3e0; color: #e65100; border-radius: 6px;
  padding: 8px 10px; margin-bottom: 12px; font-size: 13px;
}
.plan-section { margin-bottom: 15px; }
.plan-section h4 { margin: 0 0 8px 0; color: #666; font-size: 14px; }
.reason { font-size: 14px; line-height: 1.5; color: #333; margin: 0 0 10px 0; }
.path-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.tag { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
.book-list { background: #f9f9f9; border-radius: 8px; padding: 10px; }
.book-item { display: flex; justify-content: space-between; gap: 10px; padding: 8px 0; border-bottom: 1px dashed #ddd; }
.book-item:last-child { border-bottom: none; }
.book-main { flex: 1; }
.title { font-weight: bold; font-size: 14px; }
.meta { display: flex; gap: 8px; align-items: center; margin-top: 4px; font-size: 12px; color: #666; }
.rating { color: #f57c00; }
.stock.ok { color: #2e7d32; }
.stock.none { color: #c62828; }
.review { font-size: 12px; color: #888; margin: 6px 0 0; line-height: 1.4; }
.price { color: #e53935; font-weight: bold; white-space: nowrap; }
.alt-item { display: flex; gap: 8px; align-items: baseline; padding: 5px 0; font-size: 13px; }
.alt-title { font-weight: bold; }
.alt-price { color: #e53935; }
.alt-reason { color: #888; font-size: 12px; }
.plan-actions { display: flex; gap: 10px; margin-top: 20px; }
button { flex: 1; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.confirm-btn { background: #42b883; color: white; }
.adjust-btn { background: #f0f2f5; color: #333; }
button:hover { opacity: 0.9; }
</style>