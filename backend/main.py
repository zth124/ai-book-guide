from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import os
from database import engine, Base, get_db
import models
import service
from agent import generate_plan, generate_plan_stream
# 创建数据库表（如果你的 init.sql 已经建好了，这一步会自动跳过）
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 图书导购系统 API")


# 测试接口
@app.get("/")
def read_root():
    return {"message": "后端运行正常"}


# 核心接口：获取图书列表（对接前端）
@app.get("/api/books")
def api_get_books(
        keyword: str = "",
        level: str = "",
        db: Session = Depends(get_db)  # FastAPI 自动注入数据库连接
):
    # 1. 调用纯函数查数据库
    books = service.search_books(db, keyword=keyword, level=level)

    # 2. 把结果转换成字典返回给前端 (FastAPI 会自动转成 JSON)
    result = []
    for book in books:
        result.append({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "publisher": book.publisher,
            "category": book.category,
            "level": book.level,
            "rating": float(book.rating) if book.rating else 0,
            "list_price": float(book.list_price),
            "description": book.description,
            "tags": book.tags
        })
    return {"code": 200, "data": result}

# 定义前端传过来的数据格式
class CartAddReq(BaseModel):
    user_id: int
    book_id: int
    qty: int = 1


# 账号体系：注册 / 登录 / 资料修改 / 头像
class UserRegisterReq(BaseModel):
    name: str
    password: str


class UserLoginReq(BaseModel):
    name: str
    password: str = ""


class UserRenameReq(BaseModel):
    name: str


class UserAvatarReq(BaseModel):
    # 前端把本地图片压成 512px JPEG 后以 dataURL 形式提交
    avatar: str


@app.post("/api/users/register")
def api_register(req: UserRegisterReq, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.register_user(db, req.name, req.password)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/users/login")
def api_login(req: UserLoginReq, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.login_user(db, req.name, req.password)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/users/{user_id}")
def api_get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.get_user(db, user_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.patch("/api/users/{user_id}")
def api_rename_user(user_id: int, req: UserRenameReq, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.update_user_name(db, user_id, req.name)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/users/{user_id}/avatar")
def api_upload_avatar(user_id: int, req: UserAvatarReq, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.save_avatar(db, user_id, req.avatar)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/users/{user_id}/avatar")
def api_get_avatar(user_id: int, db: Session = Depends(get_db)):
    # 头像文件读出来直接返回图片字节；前端用 <img src> 展示，文件名带时间戳天然免缓存
    path = service.avatar_file(db, user_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="还没有设置头像")
    return FileResponse(path, media_type="image/jpeg")


@app.delete("/api/users/{user_id}/avatar")
def api_clear_avatar(user_id: int, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.clear_avatar(db, user_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 接口：加入购物车
@app.post("/api/cart/add")
def api_add_cart(req: CartAddReq, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.add_to_cart(db, req.user_id, req.book_id, req.qty)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 接口：查看购物车
@app.get("/api/cart/{user_id}")
def api_get_cart(user_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.get_cart(db, user_id)}

# 接口：购物车金额汇总（含优惠券）。item_ids 传逗号分隔的条目 id，只算选中项
@app.get("/api/cart/{user_id}/summary")
def api_cart_summary(user_id: int, coupon_id: int = None, item_ids: str = "", db: Session = Depends(get_db)):
    ids = [int(x) for x in item_ids.split(",") if x.strip().isdigit()] if item_ids else None
    return {"code": 200, "data": service.cart_summary(db, user_id, coupon_id, ids)}

# 接口：查询某个用户的订单列表（订单页用）
@app.get("/api/orders/{user_id}")
def api_list_orders(user_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.list_orders(db, user_id)}


# 接口：模拟支付（支付环节在真实场景由第三方完成，这里由用户在订单页触发）
@app.post("/api/orders/{order_id}/pay")
def api_pay_order(order_id: int, db: Session = Depends(get_db)):
    try:
        return {"code": 200, "data": service.pay_order(db, order_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 接口：创建订单（body 里带 item_ids 表示只结算选中的条目）
class CheckoutReq(BaseModel):
    item_ids: list[int] = []

@app.post("/api/orders/create/{user_id}")
def api_create_order(user_id: int, req: CheckoutReq = Body(default=None),
                     coupon_id: int = None, db: Session = Depends(get_db)):
    item_ids = (req.item_ids or None) if req else None
    try:
        return {"code": 200, "data": service.create_order(db, user_id, coupon_id, item_ids)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 库存接口（书不存在返回 404，库存为 0 是正常结果）
@app.get("/api/books/{book_id}/stock")
def api_check_stock(book_id: int, db: Session = Depends(get_db)):
    data = service.check_stock(db, book_id)
    if not data["exists"]:
        raise HTTPException(status_code=404, detail=f"图书 {book_id} 不存在")
    return {"code": 200, "data": data}

# 比价接口
@app.get("/api/books/{book_id}/prices")
def api_compare_price(book_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.compare_price(db, book_id)}

# 优惠券接口
@app.get("/api/coupons")
def api_query_coupons(total_amount: float = 0, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.query_coupons(db, total_amount)}

# 评论接口
@app.get("/api/books/{book_id}/reviews")
def api_get_reviews(book_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.get_reviews(db, book_id)}

# 物流接口
@app.get("/api/orders/{order_id}/logistics")
def api_query_logistics(order_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.query_logistics(db, order_id)}

# AI 导购对话接口（支持多轮：通过 session_id 维持上下文）
class ChatReq(BaseModel):
    message: str
    session_id: str = "default"
    user_id: int = 1

@app.post("/api/chat")
def api_chat(req: ChatReq):
    result = generate_plan(req.session_id, req.message, req.user_id)
    t = result.get("type")
    if t == "plan":
        return {"code": 200, "type": "plan", "data": result["data"]}
    elif t == "clarify":
        return {"code": 200, "type": "clarify", "message": result["message"]}
    elif t == "text":
        return {"code": 200, "type": "text", "message": result["message"]}
    else:
        return {"code": 500, "type": "error", "message": result.get("message", "AI大脑开小差了，请重试。")}


@app.post("/api/chat/stream")
def api_chat_stream(req: ChatReq):
    """SSE 流式对话：先把 Graph 每个节点的真实执行情况推给前端（即“思考过程”），
    最后再推最终结果。前端用 fetch + ReadableStream 读取。"""
    def event_gen():
        for kind, payload in generate_plan_stream(req.session_id, req.message, req.user_id):
            yield f"data: {json.dumps({'kind': kind, 'payload': payload}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )