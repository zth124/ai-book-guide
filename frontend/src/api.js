// 统一请求封装：集中处理 user_id、错误提示与 JSON 解析（后端 4xx 时 detail 在 body 里）
const USER_KEY = 'bookwise_user_id'
const NAME_KEY = 'bookwise_user_name'
const AVATAR_KEY = 'bookwise_user_avatar'

export function loadUser() {
  const id = Number(localStorage.getItem(USER_KEY))
  if (!id || id <= 0) return null
  return {
    id,
    name: localStorage.getItem(NAME_KEY) || `书友${id}`,
    avatar: localStorage.getItem(AVATAR_KEY) || ''
  }
}

export function saveUser(user) {
  if (!user) return
  localStorage.setItem(USER_KEY, String(user.id))
  localStorage.setItem(NAME_KEY, user.name || '')
  localStorage.setItem(AVATAR_KEY, user.avatar || '')
}

export function clearUser() {
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(NAME_KEY)
  localStorage.removeItem(AVATAR_KEY)
}

// 头像地址：文件名本身带时间戳，换头像后 URL 自然变化，不会命中旧缓存
export function avatarUrl(user) {
  if (!user || !user.avatar) return ''
  return `/api/users/${user.id}/avatar?v=${user.avatar}`
}

export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  let res
  try {
    res = await fetch(path, { ...options, headers })
  } catch (e) {
    throw new Error('无法连接服务器，请确认后端已启动')
  }

  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch (e) { data = null }

  if (!res.ok) {
    const detail = data && (data.detail || data.message)
    throw new Error(typeof detail === 'string' ? detail : `请求失败（${res.status}）`)
  }
  if (data && typeof data.code === 'number' && data.code !== 200) {
    throw new Error(data.message || data.detail || '请求失败')
  }
  return data
}
