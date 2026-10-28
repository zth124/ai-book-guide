import os
import re
import json
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from database import SessionLocal
from models import Book, Inventory, Coupon
import service

load_dotenv()

# ---------------------------------------------------------------------------
# 工具定义：把 service 层的纯函数包装成 LLM 可感知、可调用的 @tool
# 每个工具返回 JSON 字符串，便于 LLM 与后续节点解析
# ---------------------------------------------------------------------------

@tool
def search_books_tool(keyword: str = "", level: str = "", category: str = "", max_price: float = 0) -> str:
    """在图书数据库中检索图书。支持关键词(书名/tags)、难度(入门/进阶/实战)、分类、最高价格过滤。
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


TOOLS = [
    search_books_tool,
    check_stock_tool,
    compare_price_tool,
    query_coupons_tool,
    get_reviews_tool,
    calc_budget_tool,
]

TOOL_NODE = ToolNode(TOOLS)


# ---------------------------------------------------------------------------
# Graph 状态定义
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # 对话历史(本轮会临时放入工具消息)
    profile: dict                              # 用户画像：{level, target, budget, preference}
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
3. 追问尽量一次把缺的信息问全，问题要自然、口语化。

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

AGENT_PROMPT = """你是图书商城导购智能体，负责根据用户需求调用工具收集购书所需信息。

你可以调用以下工具：
- search_books_tool: 检索图书(关键词/难度/分类/最高价)
- check_stock_tool: 查库存
- compare_price_tool: 比价
- query_coupons_tool: 查优惠券
- get_reviews_tool: 查评论
- calc_budget_tool: 计算预算

工作方式：
1. 根据用户需求与画像，调用 search_books_tool 检索相关图书(可同时用多个关键词/难度)。
2. 必要时再查库存、优惠券、评论。
3. 收集到足够信息后，用一句话说明"信息已收集完成"，然后停止(不要再调用工具)。

注意：尽量在一次回复里并行调用多个工具以提升效率。不要编造图书信息，一切都以工具返回结果为准。

当前用户画像：
{profile}
"""


def agent_node(state: AgentState) -> dict:
    llm = _build_llm(temperature=0.2)
    llm_with_tools = llm.bind_tools(TOOLS)
    prompt = AGENT_PROMPT.format(profile=json.dumps(state.get("profile") or {}, ensure_ascii=False))
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


def _book_to_dict(b: Book, stock: int = None) -> dict:
    return {
        "id": b.id, "title": b.title, "author": b.author,
        "level": b.level, "category": b.category,
        "rating": float(b.rating) if b.rating else 0,
        "price": float(b.list_price),
        "stock": stock,
        "tags": b.tags,
    }


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

        # 2) 兜底：按画像确定性再检索一次，保证总能拿到候选
        if not found:
            profile = state.get("profile") or {}
            books = service.search_books(
                db,
                keyword=profile.get("target") or None,
                level=profile.get("level") or None,
            )
            for b in books:
                found[b.id] = _book_to_dict(b)

        # 3) 补库存信息(工具没查到的，直接查库)
        candidates = []
        for bid, d in found.items():
            if d.get("stock") is None:
                inv = db.query(Inventory).filter(Inventory.book_id == bid).first()
                d["stock"] = inv.stock if inv else 0
            candidates.append(d)

        return {"candidates": candidates}
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
        # 兜底：若 LLM 未给出选择，则在预算内按评分从高到低挑 2 本
        budget = float((state.get("profile") or {}).get("budget") or 0)
        pool = [c for c in candidates]
        if budget > 0:
            under = [c for c in pool if c.get("price", 0) <= budget]
            if under:
                pool = under
        pool = sorted(pool, key=lambda c: c.get("rating", 0), reverse=True)
        selected = pool[:2]
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

def _best_coupon(db, total: float):
    """从所有可用券中选择优惠力度最大的一张，返回 (coupon, 最终价)"""
    coupons = db.query(Coupon).all()
    best = None
    best_price = total
    for c in coupons:
        if total < float(c.threshold):
            continue
        if c.type == "满减":
            final = total - float(c.discount)
        elif c.type == "折扣":
            final = total * float(c.discount)
        else:
            final = total
        if final < best_price:
            best_price = final
            best = c
    return best, round(best_price, 2)


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

        books = []
        original_total = 0.0
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
            original_total += c["price"]

        original_total = round(original_total, 2)
        coupon, final_price = _best_coupon(db, original_total)

        # 备选方案的书籍信息(若备选在候选/库中存在则补价格，否则仅保留 title)
        alternatives = []
        for alt in plan.get("alternatives", [])[:2]:
            matched = None
            for c in candidates.values():
                if c["title"] == alt.get("title"):
                    matched = c
                    break
            if matched:
                alternatives.append({"title": matched["title"], "price": matched["price"], "reason": alt.get("reason", "")})
            else:
                alternatives.append({"title": alt.get("title", ""), "reason": alt.get("reason", "")})

        structured = {
            "reason": plan.get("reason", "为你推荐"),
            "path": plan.get("path", []),
            "books": books,
            "original_total": original_total,
            "total": final_price,
            "coupon": {
                "applied": coupon is not None,
                "name": coupon.name if coupon else None,
                "saved": round(original_total - final_price, 2),
            },
            "budget": {
                "original": original_total,
                "final": final_price,
                "saved": round(original_total - final_price, 2),
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
    g.add_edge("collect", "planner")
    g.add_edge("planner", "finalize")
    g.add_edge("finalize", END)

    return g.compile()


_graph = _build_graph()


# ---------------------------------------------------------------------------
# 对外入口：多轮对话的主函数
# ---------------------------------------------------------------------------

def generate_plan(session_id: str, user_message: str) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件！")
        return {"type": "error", "message": "AI 服务未配置，请联系管理员。"}

    session = _get_session(session_id)
    session["messages"].append(HumanMessage(content=user_message))

    initial_state: AgentState = {
        "messages": list(session["messages"]),
        "profile": dict(session.get("profile") or {}),
        "last_plan": session.get("last_plan"),
        "need_clarify": False,
        "clarify_question": "",
        "candidates": [],
        "plan": None,
    }

    try:
        result = _graph.invoke(initial_state, config={"recursion_limit": 15})
    except Exception as e:
        print(f"[graph] 执行失败: {e}")
        # 出错时也尽量保留对话，返回友好提示
        session["messages"].append(AIMessage(content="抱歉，AI 执行出错了，请换个说法试试。"))
        return {"type": "error", "message": "AI 大脑开小差了，请重试。"}

    # 更新画像
    session["profile"] = result.get("profile") or {}

    # 信息不足 -> 返回追问
    if result.get("need_clarify"):
        question = result.get("clarify_question") or "能否再补充一下你的基础、目标和预算？"
        session["messages"].append(AIMessage(content=question))
        return {"type": "clarify", "message": question}

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