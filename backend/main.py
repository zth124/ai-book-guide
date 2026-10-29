from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import engine, Base, get_db
import models
import service
from agent import generate_plan
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
            "level": book.level,
            "rating": float(book.rating) if book.rating else 0,
            "list_price": float(book.list_price),
            "tags": book.tags
        })
    return {"code": 200, "data": result}

# 定义前端传过来的数据格式
class CartAddReq(BaseModel):
    user_id: int
    book_id: int
    qty: int = 1

# 接口：加入购物车
@app.post("/api/cart/add")
def api_add_cart(req: CartAddReq, db: Session = Depends(get_db)):
    return service.add_to_cart(db, req.user_id, req.book_id, req.qty)

# 接口：查看购物车
@app.get("/api/cart/{user_id}")
def api_get_cart(user_id: int, db: Session = Depends(get_db)):
    return {"code": 200, "data": service.get_cart(db, user_id)}

# 接口：创建订单
@app.post("/api/orders/create/{user_id}")
def api_create_order(user_id: int, coupon_id: int = None, db: Session = Depends(get_db)):
    try:
        return service.create_order(db, user_id, coupon_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 库存接口
@app.get("/api/books/{book_id}/stock")
def api_check_stock(book_id: int, db: Session = Depends(get_db)):
    return service.check_stock(db, book_id)

# 比价接口
@app.get("/api/books/{book_id}/prices")
def api_compare_price(book_id: int, db: Session = Depends(get_db)):
    return service.compare_price(db, book_id)

# 优惠券接口
@app.get("/api/coupons")
def api_query_coupons(total_amount: float, db: Session = Depends(get_db)):
    return service.query_coupons(db, total_amount)

# 评论接口
@app.get("/api/books/{book_id}/reviews")
def api_get_reviews(book_id: int, db: Session = Depends(get_db)):
    return service.get_reviews(db, book_id)

# 物流接口
@app.get("/api/orders/{order_id}/logistics")
def api_query_logistics(order_id: int, db: Session = Depends(get_db)):
    return service.query_logistics(db, order_id)

# AI 导购对话接口（支持多轮：通过 session_id 维持上下文）
class ChatReq(BaseModel):
    message: str
    session_id: str = "default"

@app.post("/api/chat")
def api_chat(req: ChatReq):
    result = generate_plan(req.session_id, req.message)
    t = result.get("type")
    if t == "plan":
        return {"code": 200, "type": "plan", "data": result["data"]}
    elif t == "clarify":
        return {"code": 200, "type": "clarify", "message": result["message"]}
    elif t == "text":
        return {"code": 200, "type": "text", "message": result["message"]}
    else:
        return {"code": 500, "type": "error", "message": result.get("message", "AI大脑开小差了，请重试。")}