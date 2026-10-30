<template>
  <div class="plan-card">
    <!-- 顶部 header -->
    <div class="plan-header">
      <div class="header-left">
        <div class="header-badge">✨</div>
        <div>
          <h3>专属购书方案</h3>
          <span class="header-sub">根据你的画像智能推荐</span>
        </div>
      </div>
      <div class="price-box">
        <span v-if="plan.coupon && plan.coupon.applied" class="original">￥{{ plan.original_total }}</span>
        <span class="final">￥{{ plan.total }}</span>
      </div>
    </div>

    <!-- 优惠券提示 -->
    <div v-if="plan.coupon && plan.coupon.applied" class="coupon-tip">
      <span class="coupon-tag">🎟️ 已用券</span>
      <span class="coupon-name">{{ plan.coupon.name }}</span>
      <span class="coupon-save">省 ￥{{ plan.coupon.saved }}</span>
    </div>

    <!-- 推荐理由 & 学习路线 -->
    <div class="plan-section">
      <h4>💡 推荐理由 & 学习路线</h4>
      <p class="reason">{{ plan.reason }}</p>
      <div class="path-tags">
        <template v-for="(step, index) in plan.path" :key="index">
          <span class="step-tag">{{ step }}</span>
          <span v-if="index < plan.path.length - 1" class="step-arrow">→</span>
        </template>
      </div>
    </div>

    <!-- 图书清单 -->
    <div class="plan-section">
      <h4>📚 图书清单（{{ plan.books.length }} 本）</h4>
      <div class="book-list">
        <div v-for="(book, idx) in plan.books" :key="book.id" class="book-item">
          <div class="book-num">{{ idx + 1 }}</div>
          <div class="book-main">
            <div class="book-title-row">
              <span class="title">{{ book.title }}</span>
              <span class="price">￥{{ book.price }}</span>
            </div>
            <div class="meta">
              <span class="rating">★ {{ book.rating }}</span>
              <span class="level">{{ book.level }}</span>
              <span :class="book.stock > 0 ? 'stock ok' : 'stock none'">
                {{ book.stock > 0 ? `有货(${book.stock})` : '缺货' }}
              </span>
            </div>
            <p v-if="book.review_summary" class="review">{{ book.review_summary }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 备选方案 -->
    <div v-if="plan.alternatives && plan.alternatives.length" class="plan-section">
      <h4>🔁 备选方案</h4>
      <div class="alts-row">
        <div v-for="(alt, i) in plan.alternatives" :key="i" class="alt-item">
          <span class="alt-title">{{ alt.title }}</span>
          <span class="alt-sub">
            <span v-if="alt.price" class="alt-price">￥{{ alt.price }}</span>
            <span class="alt-reason">{{ alt.reason }}</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="plan-actions">
      <button class="adjust-btn" @click="emit('adjust')">🔄 微调方案</button>
      <button class="confirm-btn" @click="emit('confirm')">
        <span>确认并加入购物车</span>
        <span class="btn-arrow">→</span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  plan: { type: Object, required: true }
})
const emit = defineEmits(['confirm', 'adjust'])
</script>

<style scoped>
.plan-card {
  background: white; border-radius: 18px; padding: 0;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  overflow: hidden; width: 100%; max-width: 520px;
  animation: cardIn .4s ease both;
}

/* 顶部 header */
.plan-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 22px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
}
.header-left { display: flex; gap: 12px; align-items: center; }
.header-badge {
  width: 40px; height: 40px; border-radius: 12px;
  background: rgba(255,255,255,0.2); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center; font-size: 18px;
}
.header-left h3 { margin: 0; font-size: 17px; font-weight: 700; }
.header-sub { font-size: 12px; opacity: 0.85; }

.price-box { text-align: right; }
.original { display: block; font-size: 12px; opacity: 0.7; text-decoration: line-through; }
.final { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; }

/* 优惠券 */
.coupon-tip {
  display: flex; align-items: center; gap: 10px;
  background: linear-gradient(90deg, #fef3c7, #fde68a);
  border-left: 4px solid #f59e0b;
  padding: 10px 18px; font-size: 13px;
}
.coupon-tag { background: #f59e0b; color: white; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.coupon-name { font-weight: 600; color: #92400e; }
.coupon-save { margin-left: auto; color: #b45309; font-weight: 700; }

/* 各 section */
.plan-section { padding: 18px 22px 0; }
.plan-section h4 { margin: 0 0 10px; font-size: 13px; font-weight: 700; color: #6b7280; letter-spacing: 0.02em; }
.reason { margin: 0 0 12px; font-size: 14px; line-height: 1.6; color: #1f2937; }

.path-tags { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.step-tag {
  background: linear-gradient(135deg, #eef2ff, #ede9fe);
  color: #4f46e5; padding: 4px 12px; border-radius: 14px;
  font-size: 12px; font-weight: 600;
}
.step-arrow { color: #c7d2fe; font-weight: 700; }

/* 图书条目 */
.book-list {
  background: #f9fafb; border-radius: 14px; padding: 4px 14px;
}
.book-item {
  display: flex; gap: 14px; padding: 14px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.book-item:last-child { border-bottom: none; }
.book-num {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  background: #1f2937; color: white; font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.book-main { flex: 1; min-width: 0; }
.book-title-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.title { font-weight: 700; font-size: 14px; line-height: 1.35; }
.price { color: #dc2626; font-weight: 700; font-size: 15px; flex-shrink: 0; }
.meta { display: flex; gap: 10px; align-items: center; margin-top: 6px; font-size: 11px; color: #6b7280; }
.rating { color: #d97706; font-weight: 600; }
.level { background: #e0e7ff; color: #4338ca; padding: 1px 8px; border-radius: 10px; }
.stock.ok { color: #059669; font-weight: 600; }
.stock.none { color: #dc2626; font-weight: 600; }
.review {
  font-size: 12px; color: #6b7280; margin: 8px 0 0; line-height: 1.5;
  background: white; padding: 8px 12px; border-radius: 8px;
  border-left: 3px solid #e5e7eb;
}

/* 备选 */
.alts-row { display: flex; flex-direction: column; gap: 8px; }
.alt-item {
  background: #f3f4f6; border-radius: 10px; padding: 10px 14px;
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
}
.alt-title { font-weight: 600; font-size: 13px; color: #374151; }
.alt-sub { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 12px; color: #6b7280; }
.alt-price { color: #dc2626; font-weight: 600; }
.alt-reason { color: #9ca3af; }

/* 按钮 */
.plan-actions {
  display: flex; gap: 10px; padding: 18px 22px 22px;
}
.plan-actions button {
  flex: 1; border: none; border-radius: 12px; cursor: pointer;
  padding: 13px 18px; font-size: 14px; font-weight: 600;
  transition: all .15s;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.confirm-btn {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}
.confirm-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(99,102,241,0.4); }
.btn-arrow { font-size: 16px; }
.adjust-btn { background: #f3f4f6; color: #374151; }
.adjust-btn:hover { background: #e5e7eb; }

@keyframes cardIn {
  from { opacity: 0; transform: translateY(12px) scale(.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>