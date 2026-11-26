<template>
  <div class="plan">
    <div class="plan-head">
      <div class="badge"><Icon name="sparkles" :size="16" /></div>
      <div class="head-meta">
        <strong>专属购书方案</strong>
        <span>按你的需求整理</span>
      </div>
      <div class="price-box">
        <span v-if="plan.coupon && plan.coupon.applied" class="orig">￥{{ plan.original_total }}</span>
        <span class="final">￥{{ plan.total }}</span>
      </div>
    </div>

    <div v-if="plan.coupon && plan.coupon.applied" class="coupon">
      <Icon name="tag" :size="14" />
      <span>{{ plan.coupon.name }}</span>
      <em>省 ￥{{ plan.coupon.saved }}</em>
    </div>

    <div class="section">
      <h4>推荐理由</h4>
      <p class="reason">{{ plan.reason }}</p>
      <div v-if="plan.path && plan.path.length" class="path">
        <template v-for="(p, i) in plan.path" :key="i">
          <span class="path-step">{{ p }}</span>
          <span v-if="i < plan.path.length - 1" class="path-arrow">→</span>
        </template>
      </div>
    </div>

    <div class="section">
      <h4>图书清单 <em>{{ plan.books.length }}</em></h4>
      <div class="books">
        <div v-for="(book, idx) in plan.books" :key="book.id" class="row">
          <span class="idx">{{ String(idx + 1).padStart(2, '0') }}</span>
          <div class="row-main">
            <div class="row-top">
              <span class="t">{{ book.title }}</span>
              <span class="p">￥{{ book.price }}</span>
            </div>
            <div class="meta">
              <span class="m"><Icon name="star" :size="11" />{{ book.rating }}</span>
              <span class="m">{{ book.level }}</span>
              <span :class="['m', 'stock', book.stock > 0 ? 'ok' : 'none']">
                <Icon :name="book.stock > 0 ? 'check' : 'close'" :size="11" />
                {{ book.stock > 0 ? `有货 ${book.stock}` : '缺货' }}
              </span>
            </div>
            <p v-if="book.review_summary" class="review">{{ book.review_summary }}</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="plan.alternatives && plan.alternatives.length" class="section">
      <h4>备选方案</h4>
      <div class="alts">
        <div v-for="(a, i) in plan.alternatives" :key="i" class="alt">
          <span class="alt-title">{{ a.title }}</span>
          <span class="alt-meta">
            <span v-if="a.price" class="alt-price">￥{{ a.price }}</span>
            {{ a.reason }}
          </span>
        </div>
      </div>
    </div>

    <div class="plan-actions">
      <button class="ghost" @click="emit('adjust')">
        <Icon name="refresh" :size="14" /> 微调方案
      </button>
      <button class="primary" @click="emit('confirm')">
        确认并加购 <Icon name="arrow" :size="15" />
      </button>
    </div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({
  plan: { type: Object, required: true }
})
const emit = defineEmits(['confirm', 'adjust'])
</script>

<style scoped>
.plan {
  width: min(560px, 100%);
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(214, 242, 239, 0.24);
  background:
    linear-gradient(180deg, rgba(167, 232, 222, 0.1), rgba(255, 255, 255, 0.02) 36%),
    rgba(9, 26, 30, 0.74);
  backdrop-filter: blur(18px);
  box-shadow: 0 30px 70px -40px rgba(2, 20, 22, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.14);
  animation: cardIn 0.5s var(--ease) both;
}

.plan-head {
  display: flex; align-items: center; gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--stroke);
}
.badge {
  width: 38px; height: 38px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--mark-bg);
  color: #06282b;
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 12px 26px -16px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.head-meta { display: flex; flex-direction: column; gap: 3px; }
.head-meta strong { font-size: 15px; letter-spacing: -0.01em; }
.head-meta span { font-size: 11.5px; color: var(--text-faint); }
.price-box { margin-left: auto; text-align: right; }
.orig { display: block; font-size: 11.5px; color: var(--text-faint); text-decoration: line-through; }
.final {
  font-size: 24px; font-weight: 800; letter-spacing: -0.02em;
  background: linear-gradient(120deg, #fff, #b8e9e0 60%, #a7e8de);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}

.coupon {
  display: flex; align-items: center; gap: 7px;
  margin: 14px 20px 0; padding: 9px 13px;
  border-radius: 11px;
  font-size: 12px; color: #f0d5ce;
  background: linear-gradient(90deg, rgba(223, 182, 174, 0.14), rgba(223, 182, 174, 0.03));
  border: 1px solid rgba(223, 182, 174, 0.26);
}
.coupon em { margin-left: auto; font-style: normal; color: #f6e3dd; font-weight: 700; }

.section { padding: 16px 20px 0; }
.section h4 {
  margin: 0 0 9px;
  display: flex; align-items: center; gap: 7px;
  font-size: 12px; font-weight: 600;
  color: var(--text-faint); letter-spacing: 0.08em; text-transform: uppercase;
}
.section h4 em {
  font-style: normal; padding: 1px 7px; border-radius: 6px;
  font-size: 10.5px; color: #b8e9e0;
  background: rgba(47, 143, 136, 0.16);
}
.reason { margin: 0; font-size: 13.2px; line-height: 1.75; color: var(--text-dim); }

.path { display: flex; align-items: center; gap: 7px; margin-top: 13px; flex-wrap: wrap; }
.path-step {
  padding: 5px 12px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600; color: #b8e9e0;
  background: rgba(47, 143, 136, 0.12);
  border: 1px solid rgba(47, 143, 136, 0.26);
}
.path-arrow { color: var(--text-faint); font-size: 11px; }

.books { display: flex; flex-direction: column; gap: 8px; }
.row {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 12px 13px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--stroke);
  transition: border-color 0.2s, background 0.2s, transform 0.2s var(--ease);
}
.row:hover {
  border-color: rgba(47, 143, 136, 0.35);
  background: rgba(47, 143, 136, 0.07);
  transform: translateX(3px);
}
.idx {
  font-size: 11px; font-weight: 700; color: var(--text-faint);
  font-variant-numeric: tabular-nums;
  padding-top: 2px;
}
.row-main { flex: 1; min-width: 0; }
.row-top { display: flex; align-items: baseline; gap: 10px; }
.t {
  flex: 1; font-size: 13.5px; font-weight: 600; line-height: 1.45;
}
.p { font-size: 13.5px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }
.meta { display: flex; align-items: center; gap: 10px; margin-top: 6px; flex-wrap: wrap; }
.m { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--text-faint); }
.stock.ok { color: var(--ok); }
.stock.none { color: var(--danger); }
.review {
  margin: 8px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--text-faint);
  padding-left: 8px; border-left: 2px solid rgba(47, 143, 136, 0.3);
}

.alts { display: flex; flex-direction: column; gap: 8px; }
.alt {
  display: flex; flex-direction: column; gap: 4px;
  padding: 11px 13px; border-radius: 12px;
  border: 1px dashed var(--stroke-2);
  background: rgba(255, 255, 255, 0.02);
}
.alt-title { font-size: 13px; font-weight: 600; color: var(--text); }
.alt-meta { font-size: 11.5px; color: var(--text-faint); line-height: 1.55; }
.alt-price { color: #b8e9e0; font-weight: 600; margin-right: 8px; }

.plan-actions {
  display: flex; gap: 10px;
  padding: 18px 20px 20px;
}
.ghost {
  flex: 0 0 auto;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 12px 18px; border-radius: 13px; cursor: pointer;
  font-size: 13px; font-family: inherit; font-weight: 500;
  color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--stroke);
  transition: all 0.22s var(--ease);
}
.ghost:hover { color: var(--text); border-color: var(--stroke-2); background: var(--surface-2); }
.primary {
  flex: 1;
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  padding: 12px 18px; border-radius: 13px; border: 1px solid rgba(255, 255, 255, 0.4); cursor: pointer;
  font-size: 13.5px; font-family: inherit; font-weight: 700; color: var(--cta-fg);
  background: var(--cta-bg);
  box-shadow: 0 16px 34px -20px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transition: transform 0.2s var(--ease), box-shadow 0.2s;
}
.primary:hover { transform: translateY(-2px); box-shadow: 0 22px 42px -20px rgba(2, 20, 22, 1), inset 0 1px 0 rgba(255, 255, 255, 0.8); }
</style>
