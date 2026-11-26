import os
import re
import json
import time
from contextvars import ContextVar
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from database import SessionLocal
from models import Book, Inventory
import service

load_dotenv()

# 当前请求的用户 id。工具函数与 Graph 节点都从这里取，避免把 user_id 暴露给 LLM 去猜。
# 同步调用下 Graph 与 ToolNode 都在同一上下文执行，ContextVar 可安全传递。
_CURRENT_USER: ContextVar[int] = ContextVar("bookwise_user_id", default=1)

# ---------------------------------------------------------------------------
# 工具定义：把 service 层的纯函数包装成 LLM 可感知、可调用的 @tool
# 每个工具返回 JSON 字符串，便于 LLM 与后续节点解析
# ---------------------------------------------------------------------------

@tool
def search_books_tool(keyword: str = "", level: str = "", category: str = "", max_price: float = 0) -> str:
    """在图书数据库中检索图书。支持关键词(书名/作者/tags)、难度(入门/进阶/实战)、分类、最高价格过滤。
    返回候选图书列表的 JSON 数组，每项含 id/title/author/level/category/rating/price/tags。"""
    db = SessionLocal()
    try:
        books = service.search_books(db, keyword=keyword or None, level=level or None, category=category or None)
        result = []
        for b in books:
            price = float(b.list_price)
            if max_price and max_price > 0 and price > max_price:
                continue
            result.append({
                "id": b.id, "title": b.title, "author": b.author,
                "level": b.level, "category": b.category,
                "rating": float(b.rating) if b.rating else 0,
                "price": price, "tags": b.tags
            })
        return json.dumps(result, ensure_ascii=False)
    finally:
        db.close()


@tool
def check_stock_tool(book_id: int) -> str:
    """查询某本书的库存数量。入参 book_id 为图书 id，返回 JSON 含 book_id 与 stock。"""
    db = SessionLocal()
    try:
        return json.dumps(service.check_stock(db, book_id), ensure_ascii=False)
    finally:
        db.close()


@tool
def compare_price_tool(book_id: int) -> str:
    """比价：查询某本书在不同平台(京东/当当/淘宝)的价格。返回 JSON 数组。"""
    db = SessionLocal()
    try:
        return json.dumps(service.compare_price(db, book_id), ensure_ascii=False)
    finally:
        db.close()


@tool
def query_coupons_tool(total_amount: float = 0) -> str:
    """根据当前购物车/方案总价查询可用优惠券。total_amount 为 0 时返回全部券。返回 JSON 数组。"""
    db = SessionLocal()
    try:
        return json.dumps(service.query_coupons(db, total_amount), ensure_ascii=False)
    finally:
        db.close()


@tool
def get_reviews_tool(book_id: int) -> str:
    """查询某本书的用户评论列表(用于生成评论摘要)。返回 JSON 数组，每项含 user/rating/content。"""
    db = SessionLocal()
    try:
        return json.dumps(service.get_reviews(db, book_id), ensure_ascii=False)
    finally:
        db.close()


@tool
def calc_budget_tool(books_total: float, coupon_id: int = 0) -> str:
    """预算计算：给定书籍总价与可选优惠券 id，计算优惠后实付金额。返回 JSON 含 original 与 final。"""
    db = SessionLocal()
    try:
        return json.dumps(service.calc_budget(books_total, coupon_id or None, db), ensure_ascii=False)
    finally:
        db.close()


@tool
def add_to_cart_tool(book_id: int, qty: int = 1) -> str:
    """把指定图书加入当前用户的购物车。book_id 为图书 id，qty 为数量(默认 1)。
    返回 JSON 含 status 与 message；用户明确说"加购物车/就要这几本"时才调用。"""
    db = SessionLocal()
    try:
        return json.dumps(service.add_to_cart(db, _CURRENT_USER.get(), book_id, qty), ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"status": "failed", "message": str(e)}, ensure_ascii=False)
    finally:
        db.close()


@tool
def query_orders_tool() -> str:
    """查询当前用户的订单列表(新的在前)。返回 JSON 数组，每项含 order_id/status/total/created_at/item_count/items。
    用户问"我买过什么/我的订单"时调用。"""
    db = SessionLocal()
    try:
        return json.dumps(service.list_orders(db, _CURRENT_USER.get()), ensure_ascii=False)
    finally:
        db.close()


@tool
def query_logistics_tool(order_id: int) -> str:
    """查询某笔订单的物流轨迹。order_id 为订单号，返回 JSON 数组，每项含 node/desc/time。
    用户问"货到哪了/物流进度"时调用；不知道订单号就先调 query_orders_tool。"""
    db = SessionLocal()
    try:
        return json.dumps(service.query_logistics(db, order_id), ensure_ascii=False)
    finally:
        db.close()


TOOLS = [
    search_books_tool,
    check_stock_tool,
    compare_price_tool,
    query_coupons_tool,
    get_reviews_tool,
    calc_budget_tool,
    add_to_cart_tool,
    query_orders_tool,
    query_logistics_tool,
]

TOOL_NODE = ToolNode(TOOLS)


# ---------------------------------------------------------------------------
# Graph 状态定义
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # 对话历史(本轮会临时放入工具消息)
    user_id: int                               # 当前用户 id(加购/查订单/查物流要用)
    profile: dict                              # 用户画像：{level, target, budget, preference}
    direct_answer: str                         # 纯查询类指令(订单/物流/加购)的直接回答，非空则不进入选书流程
    last_plan: dict                            # 上一轮方案(用于多轮微调)
    need_clarify: bool                         # 是否需要追问
    clarify_question: str                      # 追问内容
    candidates: list                           # 检索/工具收集到的候选图书
    plan: dict                                 # 最终结构化方案


# ---------------------------------------------------------------------------
# 会话存储：一个进程内字典保存多轮对话状态(答辩 demo 够用，可替换为 Redis)
# ---------------------------------------------------------------------------

_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": [],     # 只存 Human/AI 对话(不含工具消息)
            "profile": {},
            "last_plan": None,
        }
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# LLM 构造与 JSON 稳健解析
# ---------------------------------------------------------------------------

def _build_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=temperature,
    )


def _parse_json(text, default):
    if not text:
        return default
    t = text.strip()
    # 去掉可能的 markdown 代码块包裹
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}|\[.*\]", t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return default
    return default


def _clean_history(messages):
    """只保留 Human 与不含 tool_calls 的 AIMessage，过滤掉工具调用/工具结果消息。
    否则把带 tool_calls 的 AIMessage 直接喂给 LLM 会被 DeepSeek 拒绝。"""
    out = []
    for m in messages:
        if isinstance(m, ToolMessage):
            continue
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            continue
        out.append(m)
    return out


# ---------------------------------------------------------------------------
# 节点 1：clarify —— 提取用户画像，判断是否需要追问补全信息
# ---------------------------------------------------------------------------

CLARIFY_PROMPT = """你是图书商城导购智能体的"信息补全"模块。

任务：从用户的最新消息中提取购书画像，并判断信息是否足够。

需要提取的画像字段(能提取多少就提取多少，没提到的留空字符串/0)：
- level: 用户的编程基础水平，如"零基础/只有Java基础/有Python基础"等
- target: 想学习的方向/技术，如"Spring Boot/前端/算法/机器学习"
- budget: 预算数字(单位元，只填数字，如 200)
- preference: 偏好，如"要实战类/评分更高/只要一本/便宜些"

判断规则：
1. 用户是首次明确表达需求时，如果 level、target、budget 这三项有缺失，需要追问(need_clarify=true)。
2. 如果用户是在"微调"上一个方案(例如"第二本换成实战书""总价压到150""只要一本""换评分更高的")，则信息通常已足够，need_clarify=false，并把偏好更新到 preference。
3. 如果用户是在查询订单、物流、购物车，或明确要求把已推荐的书加入购物车(例如"我的订单到哪了""我买过什么""把这几个加到购物车")，
   这属于直接执行类指令，need_clarify=false，画像保持不变，交给后续工具处理，不要追问购书需求。
4. 追问尽量一次把缺的信息问全，问题要自然、口语化。

严格只返回一个 JSON 对象，不要任何多余文字，不要加 ```json：
{{"need_clarify": true/false, "question": "追问内容或空字符串", "profile": {{"level":"...", "target":"...", "budget":0, "preference":"..."}}}}

当前已记录的用户画像(可被新消息更新)：
{profile}

上一轮推荐方案(用于识别"微调"意图)：
{last_plan}
"""


def clarify_node(state: AgentState) -> dict:
    llm = _build_llm(temperature=0.2)
    profile = state.get("profile") or {}
    last_plan = state.get("last_plan")
    # 只把干净对话历史传给信息补全模块
    history = _clean_history(state["messages"])

    prompt = CLARIFY_PROMPT.format(
        profile=json.dumps(profile, ensure_ascii=False),
        last_plan=json.dumps(last_plan, ensure_ascii=False) if last_plan else "无",
    )
    msgs = [SystemMessage(content=prompt)] + history
    try:
        raw = llm.invoke(msgs)
        data = _parse_json(raw.content, {})
    except Exception as e:
        print(f"[clarify] LLM 调用失败: {e}")
        data = {}

    merged_profile = dict(profile)
    patch = data.get("profile") or {}
    merged_profile.update({k: v for k, v in patch.items() if v not in (None, "", 0)})

    return {
        "profile": merged_profile,
        "need_clarify": bool(data.get("need_clarify", False)),
        "clarify_question": data.get("question", ""),
    }


# ---------------------------------------------------------------------------
# 节点 2：agent —— 带工具调用的 LLM，自主决定调用哪些工具收集信息
# ---------------------------------------------------------------------------

AGENT_PROMPT = """你是图书商城导购智能体，负责根据用户需求调用工具收集信息、并执行加购与订单类动作。

你可以调用的工具共 9 类：
1. search_books_tool 图书检索：按关键词(书名/作者/tags)、难度(入门/进阶/实战)、分类、最高价检索候选图书，可一次并行发多个条件。
2. check_stock_tool 库存查询：对候选图书查库存；缺货的书不要放进推荐清单。
3. compare_price_tool 比价：查候选图书在京东/当当/淘宝的价格，用于回答"哪里更便宜/划算吗"。
4. query_coupons_tool 优惠券查询：按当前方案总价查可用优惠券。
5. get_reviews_tool 评论查询：查某本书的评论，用于生成评论摘要。
6. calc_budget_tool 预算计算：给定书价与券，算优惠后实付金额。
7. add_to_cart_tool 加入购物车：用户明确说"帮我加购物车/就要这几本"时调用。
8. query_orders_tool 订单查询：用户问"我买过什么/我的订单/订单到哪了"时调用。
9. query_logistics_tool 物流查询：用户问物流进度时调用；不知道订单号就先调 query_orders_tool。

工作方式：
- 先用图书检索拿到候选书单，再对候选书并行查库存、评论，涉及价格问题时并行查比价与优惠券。
- 价格、券、预算这类问题必须真实调用工具，不要凭猜测或心算回答。
- 用户明确的加购、查订单、查物流指令，直接调用对应工具执行，不要只做口头承诺。
- 收集到足够信息后，用一句话说明"信息已收集完成"，然后停止调用工具。

注意：不要编造图书、价格、库存、优惠券、订单和物流信息，一切都以工具返回结果为准。

当前用户ID：{userId}
上一轮推荐方案中的图书：{lastBooks}
（用户说"就把这几本/加到购物车"时，直接用上面这些 id 调 add_to_cart_tool，不要重新检索）
当前用户画像：
{profile}
"""


def agent_node(state: AgentState) -> dict:
    llm = _build_llm(temperature=0.2)
    llm_with_tools = llm.bind_tools(TOOLS)
    # 把上一轮方案的图书 id 告诉模型，"这些都加到购物车"才不用重新检索、也不会编 id
    last_plan = state.get("last_plan") or {}
    last_books = "无"
    if last_plan.get("books"):
        last_books = "，".join(
            f"《{b.get('title')}》(id={b.get('id')}，￥{b.get('price')}）"
            for b in last_plan["books"]
        )
    prompt = AGENT_PROMPT.format(
        userId=state.get("user_id", 1),
        lastBooks=last_books,
        profile=json.dumps(state.get("profile") or {}, ensure_ascii=False),
    )
    msgs = [SystemMessage(content=prompt)] + state["messages"]
    resp = llm_with_tools.invoke(msgs)
    return {"messages": [resp]}


# ---------------------------------------------------------------------------
# 节点 3：collect —— 从工具结果中汇聚候选图书(无工具结果时做兜底检索)
# ---------------------------------------------------------------------------

def _tool_results(state: AgentState):
    """提取本轮所有工具返回的内容，返回 {tool_name: [parsed,...]}"""
    out = {}
    for m in state["messages"]:
        if isinstance(m, ToolMessage):
            parsed = _parse_json(m.content, None)
            out.setdefault(m.name, []).append(parsed)
    return out


# 用户目标里的口语词，兜底检索前先剥掉，避免“想学Vue3原理”整串拿去 like 匹配
_TARGET_STOPWORDS = (
    "想学", "想系统学习", "系统学习", "我想", "帮我", "推荐", "几本", "一下",
    "系统", "学习", "入门", "原理", "实战", "基础", "进阶", "的书", "书",
)


def _fallback_terms(target) -> list:
    """把用户目标拆成可用于关键词检索的词，最多 3 个。"""
    t = target or ""
    for w in _TARGET_STOPWORDS:
        t = t.replace(w, " ")
    parts = [p.strip() for p in re.split(r"[\s,，、/|]+", t) if p.strip()]
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:3]


def _term_variants(term) -> list:
    """关键词变体：去掉版本号数字后再查一次。
    库里 tags 写的是“Vue”，用户说的是“Vue3”，不去掉数字就永远匹配不到。"""
    out = [term]
    stripped = re.sub(r"\d+(\.\d+)*", "", term).strip()
    if stripped and stripped != term:
        out.append(stripped)
    return out


def _book_to_dict(b: Book, stock: int = None) -> dict:
    return {
        "id": b.id, "title": b.title, "author": b.author,
        "level": b.level, "category": b.category,
        "rating": float(b.rating) if b.rating else 0,
        "price": float(b.list_price),
        "stock": stock,
        "tags": b.tags,
    }


_ORDER_TOOLS = {"add_to_cart_tool", "query_orders_tool", "query_logistics_tool"}


def _direct_answer_from_tools(tool_results):
    """本轮工具只涉及购物车/订单/物流、没产生候选图书时，直接把工具结果串成人话。
    这类指令（"我的订单到哪了""把这几本加购"）不该走选书流程，否则会回一句"没找到合适的书"。"""
    parts = []
    for name, results in tool_results.items():
        if name not in _ORDER_TOOLS:
            continue
        for r in results:
            if r is None:
                continue
            if name == "add_to_cart_tool":
                parts.append(f"购物车：{(r or {}).get('message') or '操作完成'}")
            elif name == "query_orders_tool":
                if not isinstance(r, list) or not r:
                    parts.append("订单：名下还没有订单记录")
                else:
                    brief = []
                    for o in r[:5]:
                        brief.append(f"#{o.get('order_id')}（{o.get('status')}，￥{o.get('total')}，{o.get('item_count')} 件）")
                    parts.append("最近的订单：" + "；".join(brief))
            elif name == "query_logistics_tool":
                if not isinstance(r, list) or not r:
                    parts.append("物流：该订单暂无物流轨迹，发货后可再查")
                else:
                    latest = r[0]
                    parts.append(f"物流最新状态：{latest.get('node')} — {latest.get('desc')}（{latest.get('time')}）")
    return "；".join(parts)


def collect_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        tool_results = _tool_results(state)
        found = {}  # id -> dict

        # 1) 优先使用 search_books_tool 的结果
        book_lists = tool_results.get("search_books_tool", [])
        for lst in book_lists:
            if isinstance(lst, list):
                for b in lst:
                    if isinstance(b, dict) and b.get("id"):
                        found[b["id"]] = b

        # 2) 兜底：模型没调工具时，把用户目标拆成关键词再查一遍。
        #    注意不再按 level 精确匹配——用户说的“有前端基础”不等于库里的“入门/进阶/实战”，
        #    加上这个条件会一条都查不到，导致方案为空。
        if not found:
            profile = state.get("profile") or {}
            terms = _fallback_terms(profile.get("target")) or _fallback_terms(profile.get("preference"))
            for term in terms:
                for kw in _term_variants(term):
                    for b in service.search_books(db, keyword=kw):
                        found[b.id] = _book_to_dict(b)
                if found:
                    break

        # 3) 补库存信息(工具没查到的，直接查库)
        candidates = []
        for bid, d in found.items():
            if d.get("stock") is None:
                inv = db.query(Inventory).filter(Inventory.book_id == bid).first()
                d["stock"] = inv.stock if inv else 0
            candidates.append(d)

        # 4) 纯查询类指令（订单/物流/加购）没有候选图书时，直接给结论，不进入选书流程
        direct_answer = "" if candidates else _direct_answer_from_tools(tool_results)
        return {"candidates": candidates, "direct_answer": direct_answer}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 节点 4：planner —— 从候选中挑选图书，生成理由/学习路线/备选方案
# ---------------------------------------------------------------------------

PLANNER_PROMPT = """你是图书导购智能体的"方案规划"模块。

请根据用户的原始需求、当前画像、以及下方候选图书列表，生成一份最优购书方案。

要求：
1. 从候选列表中挑选最合适的书(通常 1~3 本)，严格控制总价不超过用户预算。
2. 尊重用户偏好：如"实战类""评分更高""只要一本""第二本换成实战书"等。
3. 如果这是对上一轮方案的"微调"，请基于上一轮方案做最小改动，而不是推翻重来。
4. 学习路线(path)按由浅入深给出 2~4 个阶段标签。
5. 给出 1~2 个备选书本(title + 简短理由)，作为 alternatives。
6. reason 只写选书思路和每本书的定位。**禁止出现具体金额、总价、优惠券名称，
   也不要用"第一本/第二本"这类序号**——金额和优惠由系统统一计算，序号顺序可能被调整，
   你写了就会和最终清单对不上。同样不要写"共几本/两本"这类数量描述。
7. 候选里带 stock 字段。**只把有库存(stock > 0)的书放进 selected_ids**；
   确实想推荐但缺货的书，放进 alternatives 并注明"暂时缺货"，不要塞进清单。

候选图书列表(JSON)：
{candidates}

当前画像：
{profile}

上一轮方案(为空表示首次规划)：
{last_plan}

严格只返回一个 JSON 对象，不要任何多余文字，不要加 ```json：
{{
  "reason": "150字以内的推荐理由",
  "path": ["阶段1", "阶段2", "阶段3"],
  "selected_ids": [选中的图书id],
  "alternatives": [{{"title": "备选书名", "reason": "简短理由"}}]
}}
"""


def planner_node(state: AgentState) -> dict:
    llm = _build_llm(temperature=0.4)
    candidates = state.get("candidates") or []
    profile = state.get("profile") or {}
    last_plan = state.get("last_plan")

    prompt = PLANNER_PROMPT.format(
        candidates=json.dumps(candidates, ensure_ascii=False),
        profile=json.dumps(profile, ensure_ascii=False),
        last_plan=json.dumps(last_plan, ensure_ascii=False) if last_plan else "无",
    )
    history = _clean_history(state["messages"])
    msgs = [SystemMessage(content=prompt)] + history

    try:
        raw = llm.invoke(msgs)
        data = _parse_json(raw.content, {})
    except Exception as e:
        print(f"[planner] LLM 调用失败: {e}")
        data = {}

    if not data.get("selected_ids"):
        # 兜底：若 LLM 未给出选择，则按评分从高到低贪心挑书，同时保证总价不超预算
        budget = float((state.get("profile") or {}).get("budget") or 0)
        pool = sorted(candidates, key=lambda c: c.get("rating", 0), reverse=True)
        selected = []
        total = 0.0
        for c in pool:
            if len(selected) >= 2:
                break
            if budget > 0 and total + c.get("price", 0) > budget:
                continue
            selected.append(c)
            total += c.get("price", 0)
        # 若一本都放不下预算，退回评分最高的一本
        if not selected and pool:
            selected = [pool[0]]
        data = {
            "reason": "综合评分与预算推荐",
            "path": ["入门", "进阶"],
            "selected_ids": [c["id"] for c in selected],
            "alternatives": [],
        }

    return {"plan": data}


# ---------------------------------------------------------------------------
# 节点 5：finalize —— 组装最终结构化方案(预算/优惠券/库存/评论摘要做确定性计算)
# ---------------------------------------------------------------------------

# 选券与算钱逻辑已统一收敛到 service.pick_best_coupon / service.apply_coupon，
# 方案卡片、购物车页、创建订单共用同一套规则，避免出现多种口径。


def _review_summary(db, book_id: int) -> str:
    reviews = service.get_reviews(db, book_id)
    if not reviews:
        return "暂无评论"
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    top = max(reviews, key=lambda r: r["rating"])
    low = min(reviews, key=lambda r: r["rating"])
    return f"平均 {avg:.1f} 分({len(reviews)} 条)。好评：“{top['content'][:30]}…” 差评：“{low['content'][:30]}…”"


def finalize_node(state: AgentState) -> dict:
    db = SessionLocal()
    try:
        plan = state.get("plan") or {}
        candidates = {c["id"]: c for c in (state.get("candidates") or [])}
        selected_ids = plan.get("selected_ids", [])
        profile = state.get("profile") or {}
        budget = float(profile.get("budget") or 0)

        # 1) 组装选中的图书
        books = []
        for bid in selected_ids:
            c = candidates.get(bid)
            if not c:
                b = db.query(Book).filter(Book.id == bid).first()
                if not b:
                    continue
                c = _book_to_dict(b)
            books.append({
                "id": c["id"],
                "title": c["title"],
                "author": c.get("author", ""),
                "level": c.get("level", ""),
                "rating": c.get("rating", 0),
                "price": c["price"],
                "stock": c.get("stock", 0),
                "review_summary": _review_summary(db, c["id"]),
            })

        # 2) 预算校验：按方案里的学习顺序逐本纳入，放不下的书转入备选方案，
        #    同时重写推荐理由，保证“文字描述”与“图书清单”始终一致
        reason = plan.get("reason") or "为你推荐"
        dropped = []   # [{"book": 书, "reason": 移出清单的原因}]
        if budget > 0 and books:
            picked, spent = [], 0.0
            for bk in books:
                if spent + bk["price"] <= budget:
                    picked.append(bk)
                    spent += bk["price"]
                else:
                    dropped.append({"book": bk, "reason": f"超出 {budget:g} 元预算，本次未纳入清单"})
            if not picked:
                keep = max(books, key=lambda x: x["rating"])
                dropped = [{"book": b, "reason": f"超出 {budget:g} 元预算，本次未纳入清单"}
                           for b in books if b["id"] != keep["id"]]
                picked = [keep]
                reason = (f"你的预算是 {budget:g} 元，低于清单中每本书的单价，"
                          f"先为你保留评分最高的《{keep['title']}》，其余书已移入备选方案。")
            else:
                if dropped:
                    kept_names = "、".join(f"《{b['title']}》" for b in picked)
                    lost_names = "、".join(f"《{d['book']['title']}》" for d in dropped)
                    reason = (f"按 {budget:g} 元的预算，本次保留 {len(picked)} 本：{kept_names}；"
                              f"{lost_names} 超出预算，已移入备选方案。")
            books = picked

        # 3) 库存过滤：缺货的书不放进推荐清单
        out_of_stock = [b for b in books if (b.get("stock") or 0) <= 0]
        if out_of_stock:
            names = "、".join(f"《{b['title']}》" for b in out_of_stock)
            if len(out_of_stock) < len(books):
                books = [b for b in books if (b.get("stock") or 0) > 0]
                reason = reason + f"（{names} 暂时缺货，已移入备选方案）"
                for b in out_of_stock:
                    dropped.append({"book": b, "reason": "暂时缺货，到货后可再考虑"})
            else:
                reason = reason + f"（{names} 当前缺货，下单前请留意）"

        original_total = round(sum(b["price"] for b in books), 2)
        coupon, final_decimal, saved_decimal = service.pick_best_coupon(db, original_total)
        final_price = float(final_decimal)
        saved_amount = float(saved_decimal)

        # 备选方案的书籍信息(若备选在候选/库中存在则补价格，否则仅保留 title)
        # 已入选清单的书不再重复出现在备选里
        alternatives = []
        selected_titles = {b["title"] for b in books}
        for alt in plan.get("alternatives", [])[:2]:
            if alt.get("title") in selected_titles:
                continue
            matched = None
            for c in candidates.values():
                if c["title"] == alt.get("title"):
                    matched = c
                    break
            if matched:
                alternatives.append({"title": matched["title"], "price": matched["price"], "reason": alt.get("reason", "")})
            else:
                alternatives.append({"title": alt.get("title", ""), "reason": alt.get("reason", "")})

        # 被预算挤出去的书写进备选方案，信息不丢失，也和推荐理由的措辞对得上
        existing_titles = {a["title"] for a in alternatives}
        for d in dropped:
            b = d["book"]
            if len(alternatives) >= 3:
                break
            if b["title"] in existing_titles:
                continue
            alternatives.append({
                "title": b["title"],
                "price": b["price"],
                "reason": d["reason"],
            })
            existing_titles.add(b["title"])

        # 兜底：模型没给备选（或给的备选都在清单里）时，从候选里挑评分较高的补上，
        # 保证“备选方案”这一栏始终有内容且不与清单重复
        if not alternatives:
            pool = [c for c in candidates.values() if c["title"] not in selected_titles]
            pool.sort(key=lambda c: c.get("rating", 0), reverse=True)
            for c in pool[:2]:
                alternatives.append({
                    "title": c["title"],
                    "price": c["price"],
                    "reason": "同类中评分较高，可作为替代选择",
                })

        structured = {
            "reason": reason,
            "path": plan.get("path", []),
            "books": books,
            "original_total": original_total,
            "total": final_price,
            "coupon": {
                "applied": coupon is not None,
                "id": coupon.id if coupon else None,
                "name": coupon.name if coupon else None,
                "saved": saved_amount,
            },
            "budget": {
                "original": original_total,
                "final": final_price,
                "saved": saved_amount,
            },
            "alternatives": alternatives,
        }
        return {"plan": structured}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 组装 StateGraph
# ---------------------------------------------------------------------------

def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("clarify", clarify_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", TOOL_NODE)
    g.add_node("collect", collect_node)
    g.add_node("planner", planner_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "clarify")

    # clarify 之后：信息不足 -> 结束(返回追问)；信息足够 -> 进入工具调用
    def route_after_clarify(state):
        return "ask" if state.get("need_clarify") else "agent"

    g.add_conditional_edges("clarify", route_after_clarify, {"ask": END, "agent": "agent"})

    # agent 之后：有工具调用 -> 执行工具；无工具调用 -> 直接汇总裁体方案
    def route_after_agent(state):
        last = state["messages"][-1] if state["messages"] else None
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "collect"

    g.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "collect": "collect"})
    g.add_edge("tools", "collect")

    # collect 之后：纯查询类指令已拿到直接回答 -> 结束；否则进入选书规划
    def route_after_collect(state):
        return "answer" if state.get("direct_answer") else "planner"

    g.add_conditional_edges("collect", route_after_collect, {"answer": END, "planner": "planner"})
    g.add_edge("planner", "finalize")
    g.add_edge("finalize", END)

    return g.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# 对外入口：多轮对话的主函数
# ---------------------------------------------------------------------------

def _compose_result(session: dict, result: dict) -> dict:
    """把 Graph 跑完的最终状态转成前端响应，同时写回会话历史。"""
    # 更新画像
    session["profile"] = result.get("profile") or {}

    # 信息不足 -> 返回追问
    if result.get("need_clarify"):
        question = result.get("clarify_question") or "能否再补充一下你的基础、目标和预算？"
        session["messages"].append(AIMessage(content=question))
        return {"type": "clarify", "message": question}

    # 订单/物流/加购这类直接回答，原样返回文本
    if result.get("direct_answer"):
        text = result["direct_answer"]
        session["messages"].append(AIMessage(content=text))
        return {"type": "text", "message": text}

    # 生成方案
    plan = result.get("plan")
    if not plan or not plan.get("books"):
        msg = "抱歉，暂时没有找到合适的新书推荐，试试换个方向或放宽预算。"
        session["messages"].append(AIMessage(content=msg))
        return {"type": "text", "message": msg}

    session["last_plan"] = plan
    summary = f"已为你推荐 {len(plan['books'])} 本书，优惠后合计 ￥{plan['total']}。可继续微调，例如“换一本评分更高的”。"
    session["messages"].append(AIMessage(content=summary))

    return {"type": "plan", "data": plan}


def generate_plan(session_id: str, user_message: str, user_id: int = 1) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件！")
        return {"type": "error", "message": "AI 服务未配置，请联系管理员。"}

    _CURRENT_USER.set(int(user_id or 1))
    session = _get_session(session_id)
    session["messages"].append(HumanMessage(content=user_message))

    initial_state: AgentState = {
        "messages": list(session["messages"]),
        "user_id": int(user_id or 1),
        "profile": dict(session.get("profile") or {}),
        "last_plan": session.get("last_plan"),
        "need_clarify": False,
        "clarify_question": "",
        "candidates": [],
        "direct_answer": "",
        "plan": None,
    }

    try:
        result = _graph.invoke(initial_state, config={"recursion_limit": 15})
    except Exception as e:
        print(f"[graph] 执行失败: {e}")
        # 出错时也尽量保留对话，返回友好提示
        session["messages"].append(AIMessage(content="抱歉，AI 执行出错了，请换个说法试试。"))
        return {"type": "error", "message": "AI 大脑开小差了，请重试。"}

    return _compose_result(session, result)


# ---------------------------------------------------------------------------
# 流式入口：把 Graph 每个节点的真实执行情况逐步推给前端（即“思考过程”）
# ---------------------------------------------------------------------------

_NODE_STEP = {
    "clarify": "理解需求",
    "agent": "规划检索",
    "tools": "调用工具",
    "collect": "召回候选",
    "planner": "制定方案",
    "finalize": "核算金额",
}


def _step_detail(node: str, output: dict) -> str:
    """给每个节点的执行结果写一句人话，前端直接展示成思考步骤。"""
    if node == "clarify":
        if output.get("need_clarify"):
            q = (output.get("clarify_question") or "").strip()
            return f"信息不足，准备追问：{q[:40]}" if q else "信息不足，准备追问"
        p = output.get("profile") or {}
        bits = [f"{k}={p[k]}" for k in ("level", "target", "budget") if p.get(k)]
        return ("已识别 " + "，".join(bits)) if bits else "需求已明确，进入选书"

    if node == "agent":
        msgs = output.get("messages") or []
        calls = getattr(msgs[-1], "tool_calls", None) if msgs else None
        if calls:
            return "决定调用 " + "、".join(c.get("name", "?") for c in calls)
        return "信息已够，准备汇总"

    if node == "tools":
        msgs = output.get("messages") or []
        parts = []
        for m in msgs:
            name = (getattr(m, "name", "") or "工具").replace("_tool", "")
            n = None
            try:
                data = json.loads(getattr(m, "content", "") or "null")
                if isinstance(data, list):
                    n = len(data)
            except Exception:
                pass
            parts.append(name + (f" {n} 条" if n is not None else ""))
        return f"执行 {len(msgs)} 次查询：" + "、".join(parts)

    if node == "collect":
        return f"整理出 {len(output.get('candidates') or [])} 本候选"

    if node == "planner":
        plan = output.get("plan") or {}
        n = len(plan.get("selected_ids") or plan.get("books") or [])
        return f"选定 {n} 本，准备核算" if n else "选书完成，准备核算"

    if node == "finalize":
        plan = output.get("plan") or {}
        total = plan.get("total")
        books = plan.get("books") or []
        head = f"预算内保留 {len(books)} 本"
        c = plan.get("coupon") or {}
        if c.get("applied"):
            return f"{head}，套用「{c.get('name')}」，实付 ￥{float(total):.2f}，省 ￥{float(c.get('saved') or 0):.2f}"
        return f"{head}，暂无可用优惠券，实付 ￥{float(total):.2f}"

    return ""


def generate_plan_stream(session_id: str, user_message: str, user_id: int = 1):
    """流式版 generate_plan，逐步产出 (kind, payload)：
    kind=step   —— 一个真实执行步骤（label/detail/ms）
    kind=result —— 最终响应，结构同 generate_plan 的返回值
    kind=error  —— 出错
    """
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件！")
        yield ("error", {"message": "AI 服务未配置，请联系管理员。"})
        return

    _CURRENT_USER.set(int(user_id or 1))
    session = _get_session(session_id)
    session["messages"].append(HumanMessage(content=user_message))

    initial_state: AgentState = {
        "messages": list(session["messages"]),
        "user_id": int(user_id or 1),
        "profile": dict(session.get("profile") or {}),
        "last_plan": session.get("last_plan"),
        "need_clarify": False,
        "clarify_question": "",
        "candidates": [],
        "direct_answer": "",
        "plan": None,
    }

    state = dict(initial_state)
    last = time.time()

    try:
        for chunk in _graph.stream(initial_state, config={"recursion_limit": 15}, stream_mode="updates"):
            for node, output in chunk.items():
                if not isinstance(output, dict):
                    continue
                # 累积节点更新，等价于 invoke 跑完后的最终状态
                for k, v in output.items():
                    if k == "messages":
                        state["messages"] = list(state["messages"]) + list(v)
                    else:
                        state[k] = v

                now = time.time()
                yield ("step", {
                    "node": node,
                    "label": _NODE_STEP.get(node, node),
                    "detail": _step_detail(node, output),
                    "ms": int((now - last) * 1000),
                })
                last = now
    except Exception as e:
        print(f"[graph:stream] 执行失败: {e}")
        session["messages"].append(AIMessage(content="抱歉，AI 执行出错了，请换个说法试试。"))
        yield ("error", {"message": "AI 大脑开小差了，请重试。"})
        return

    yield ("result", _compose_result(session, state))