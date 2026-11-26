<template>
  <div class="orders glass">
    <div class="orders-head">
      <div class="head-left">
        <div class="head-icon"><Icon name="receipt" :size="18" /></div>
        <div class="head-meta">
          <h2>我的订单</h2>
          <span>共 {{ orders.length }} 笔</span>
        </div>
      </div>
      <button class="refresh" :disabled="loading" @click="fetchOrders">
        <Icon name="refresh" :size="14" :class="{ spinning: loading }" />
        {{ loading ? '刷新中' : '刷新' }}
      </button>
    </div>

    <div v-if="error" class="state err">
      <p>{{ error }}</p>
      <button class="btn btn-ghost" @click="fetchOrders">重试</button>
    </div>

    <div v-else-if="!loading && orders.length === 0" class="state">
      <div class="state-icon"><Icon name="receipt" :size="26" /></div>
      <p>还没有订单</p>
      <span>去 AI 导购挑几本书，或在购物车结算</span>
    </div>

    <div v-else class="list">
      <div v-for="order in orders" :key="order.order_id" class="order">
        <div class="o-head">
          <div class="oid">
            <span class="label">订单号</span>
            <strong>#{{ order.order_id }}</strong>
          </div>
          <span :class="['status', order.status === '待支付' ? 'pending' : 'done']">
            <i></i>{{ order.status }}
          </span>
        </div>

        <div class="o-meta">
          <span><Icon name="clock" :size="12" />{{ order.created_at || '—' }}</span>
          <span>共 {{ order.item_count }} 件</span>
        </div>

        <div class="o-items">
          <div v-for="item in order.items" :key="item.book_id" class="o-item">
            <span class="it">{{ item.title }}</span>
            <span class="iq">￥{{ money(item.price) }} × {{ item.qty }}</span>
            <span class="is">￥{{ money(item.subtotal) }}</span>
          </div>
        </div>

        <div class="o-foot">
          <div class="amount">
            <s v-if="order.original_total > order.total">￥{{ money(order.original_total) }}</s>
            <strong>￥{{ money(order.total) }}</strong>
          </div>
          <div class="acts">
            <button
              v-if="order.status === '待支付'"
              class="pay"
              :disabled="payingId === order.order_id"
              @click="payOrder(order.order_id)"
            >
              <Icon name="check" :size="14" />
              {{ payingId === order.order_id ? '支付中…' : '模拟支付' }}
            </button>
            <button
              class="logi"
              :disabled="logLoadingId === order.order_id"
              @click="toggleLogistics(order.order_id)"
            >
              <Icon name="truck" :size="14" />
              {{ expanded[order.order_id] ? '收起物流' : '查看物流' }}
            </button>
          </div>
        </div>

        <div v-if="expanded[order.order_id]" class="logistics">
          <div v-if="logLoadingId === order.order_id" class="log-loading">
            <span class="spinner"></span> 物流查询中…
          </div>
          <div v-else-if="!logs[order.order_id] || logs[order.order_id].length === 0" class="log-empty">
            暂无物流轨迹，发货后可在这里查看
          </div>
          <div v-else class="timeline">
            <div v-for="(node, i) in logs[order.order_id]" :key="i" class="node">
              <div class="track">
                <span :class="['nd', { latest: i === 0 }]"></span>
                <span v-if="i < logs[order.order_id].length - 1" class="line"></span>
              </div>
              <div class="node-body">
                <div class="node-head">
                  <span class="node-name">{{ node.node }}</span>
                  <span class="node-time">{{ node.time }}</span>
                </div>
                <p class="node-desc">{{ node.desc }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from '../api'
import Icon from './Icon.vue'

const props = defineProps({
  userId: { type: Number, required: true }
})

const orders = ref([])
const loading = ref(false)
const error = ref('')
const expanded = ref({})
const logs = ref({})
const logLoadingId = ref(null)
const payingId = ref(null)

const money = (v) => Number(v || 0).toFixed(2)

const fetchOrders = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await api(`/api/orders/${props.userId}`)
    orders.value = data.data || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const toggleLogistics = async (orderId) => {
  if (expanded.value[orderId]) {
    expanded.value[orderId] = false
    return
  }
  expanded.value[orderId] = true
  if (logs.value[orderId]) return

  logLoadingId.value = orderId
  try {
    const data = await api(`/api/orders/${orderId}/logistics`)
    logs.value[orderId] = data.data || []
  } catch (e) {
    logs.value[orderId] = []
  } finally {
    logLoadingId.value = null
  }
}

const payOrder = async (orderId) => {
  payingId.value = orderId
  try {
    const data = await api(`/api/orders/${orderId}/pay`, { method: 'POST' })
    await fetchOrders()
    if (data && data.data && data.data.paid) {
      // 支付后直接展开物流，顺便清掉旧的空缓存
      delete logs.value[orderId]
      expanded.value[orderId] = false
      await toggleLogistics(orderId)
    }
  } catch (e) {
    alert(`支付失败：${e.message}`)
  } finally {
    payingId.value = null
  }
}

onMounted(fetchOrders)
watch(() => props.userId, fetchOrders)
</script>

<style scoped>
.orders { max-width: 880px; margin: 0 auto; overflow: hidden; }

.orders-head {
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
.refresh {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 16px; border-radius: 999px; cursor: pointer;
  font-size: 12.5px; font-family: inherit; font-weight: 500;
  color: var(--text-dim); background: var(--surface);
  border: 1px solid var(--stroke);
  transition: all 0.2s;
}
.refresh:hover { color: var(--text); border-color: var(--stroke-2); }
.refresh:disabled { opacity: 0.6; cursor: default; }
.spinning { animation: spin 0.8s linear infinite; }

.state { padding: 66px 24px; text-align: center; color: var(--text-dim); }
.state .state-icon {
  width: 62px; height: 62px; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 18px; color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--stroke);
}
.state p { margin: 0; font-size: 15px; font-weight: 600; color: var(--text); }
.state span { display: block; margin-top: 7px; font-size: 12.5px; color: var(--text-faint); }
.state.err p { color: var(--danger); font-size: 13.5px; font-weight: 400; margin-bottom: 16px; }

.list { padding: 18px 24px 24px; display: flex; flex-direction: column; gap: 16px; }
.order {
  border-radius: 16px; overflow: hidden;
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.025);
  transition: border-color 0.25s, box-shadow 0.25s;
  animation: fadeUp 0.4s var(--ease) both;
}
.order:hover { border-color: rgba(47, 143, 136, 0.32); box-shadow: 0 24px 50px -30px rgba(47, 143, 136, 0.6); }

.o-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 15px 18px;
  background: linear-gradient(90deg, rgba(47, 143, 136, 0.09), transparent 70%);
}
.oid { display: flex; align-items: baseline; gap: 9px; }
.label { font-size: 11px; color: var(--text-faint); letter-spacing: 0.06em; }
.oid strong { font-size: 16px; letter-spacing: -0.01em; font-variant-numeric: tabular-nums; }
.status {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600;
}
.status i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status.pending { color: #e3c893; background: rgba(227, 200, 147, 0.1); border: 1px solid rgba(227, 200, 147, 0.26); }
.status.done { color: #8fe7cd; background: rgba(95, 214, 180, 0.1); border: 1px solid rgba(95, 214, 180, 0.26); }

.o-meta {
  display: flex; gap: 20px; padding: 9px 18px;
  font-size: 11.5px; color: var(--text-faint);
  border-bottom: 1px solid rgba(255, 255, 255, 0.045);
}
.o-meta span { display: inline-flex; align-items: center; gap: 5px; }

.o-items { padding: 6px 18px; }
.o-item {
  display: flex; align-items: center; gap: 12px;
  padding: 9px 0; font-size: 12.8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.035);
}
.o-item:last-child { border-bottom: 0; }
.it { flex: 1; color: var(--text); font-weight: 500; min-width: 0; }
.iq { color: var(--text-faint); font-variant-numeric: tabular-nums; }
.is { width: 82px; text-align: right; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }

.o-foot {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px; padding: 13px 18px;
  border-top: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.02);
}
.amount { display: flex; align-items: baseline; gap: 11px; }
.amount s { font-size: 11.5px; color: var(--text-faint); }
.amount strong { font-size: 20px; font-weight: 800; letter-spacing: -0.02em; color: #fff; }
.acts { display: flex; gap: 9px; }

.pay {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 17px; border-radius: 999px; border: 1px solid rgba(255, 255, 255, 0.4); cursor: pointer;
  font-size: 12.5px; font-family: inherit; font-weight: 700; color: var(--cta-fg);
  background: var(--cta-bg);
  box-shadow: 0 14px 28px -18px rgba(2, 20, 22, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.7);
  transition: transform 0.2s var(--ease);
}
.pay:hover { transform: translateY(-1px); }
.pay:disabled { opacity: 0.65; cursor: default; transform: none; }

.logi {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 16px; border-radius: 999px; cursor: pointer;
  font-size: 12.5px; font-family: inherit; font-weight: 600;
  color: #b8e9e0;
  background: rgba(47, 143, 136, 0.12);
  border: 1px solid rgba(47, 143, 136, 0.3);
  transition: all 0.2s;
}
.logi:hover { background: rgba(47, 143, 136, 0.24); color: #fff; }
.logi:disabled { opacity: 0.6; cursor: default; }

.logistics { padding: 6px 18px 18px; border-top: 1px solid rgba(255, 255, 255, 0.045); }
.log-loading {
  display: flex; align-items: center; gap: 8px;
  padding: 18px 0; font-size: 12.5px; color: var(--text-faint);
}
.spinner {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid rgba(47, 143, 136, 0.28);
  border-top-color: #a78bfa;
  animation: spin 0.8s linear infinite;
}
.log-empty { padding: 18px 0; font-size: 12.5px; color: var(--text-faint); }

.timeline { padding-top: 14px; }
.node { display: flex; gap: 12px; }
.track { display: flex; flex-direction: column; align-items: center; width: 12px; padding-top: 4px; }
.nd { width: 9px; height: 9px; border-radius: 50%; background: rgba(255, 255, 255, 0.16); flex-shrink: 0; }
.nd.latest {
  background: var(--mark-bg);
  box-shadow: 0 0 0 4px rgba(167, 232, 222, 0.14), 0 0 0 1px rgba(255, 255, 255, 0.4);
}
.line { flex: 1; width: 1px; background: rgba(255, 255, 255, 0.12); margin: 5px 0; }
.node-body { padding-bottom: 16px; flex: 1; }
.node-head { display: flex; justify-content: space-between; gap: 12px; }
.node-name { font-size: 12.8px; font-weight: 600; color: var(--text); }
.node-time { font-size: 11px; color: var(--text-faint); font-variant-numeric: tabular-nums; }
.node-desc { margin: 4px 0 0; font-size: 12px; line-height: 1.6; color: var(--text-dim); }

@media (max-width: 640px) {
  .o-foot { flex-direction: column; align-items: stretch; }
  .acts { justify-content: flex-end; }
}
</style>
