from sqlalchemy.orm import Session
from models import Book, CartItem, Order, OrderItem,BookPrice, Inventory, Review, Coupon, Logistics
from decimal import Decimal


# 纯函数：根据关键词、难度、分类查书
def search_books(db: Session, keyword: str = None, level: str = None, category: str = None):
    query = db.query(Book)

    if keyword:
        # 模糊搜索书名或 tags
        query = query.filter((Book.title.like(f"%{keyword}%")) | (Book.tags.like(f"%{keyword}%")))
    if level:
        query = query.filter(Book.level == level)
    if category:
        query = query.filter(Book.category == category)

    # 限制最多返回 10 本
    return query.limit(10).all()


# 纯函数：加入购物车
def add_to_cart(db: Session, user_id: int, book_id: int, qty: int = 1):
    # 查一下购物车里是不是已经有这本书了
    existing_item = db.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.book_id == book_id
    ).first()

    if existing_item:
        existing_item.qty += qty
    else:
        new_item = CartItem(user_id=user_id, book_id=book_id, qty=qty)
        db.add(new_item)

    db.commit()
    return {"status": "success", "message": "已加入购物车"}


# 纯函数：查看购物车
def get_cart(db: Session, user_id: int):
    items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    result = []
    for item in items:
        result.append({
            "cart_item_id": item.id,
            "book_id": item.book_id,
            "title": item.book.title,
            "price": float(item.book.list_price),
            "qty": item.qty,
            "subtotal": float(item.book.list_price) * item.qty
        })
    return result


# 纯函数：创建订单（简化版，先不扣库存和算优惠券）
def create_order(db: Session, user_id: int, coupon_id: int = None):
    # 1. 获取购物车
    cart_items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    if not cart_items:
        raise ValueError("购物车为空")

    # 2. 计算总价
    total_amount = sum([item.book.list_price * item.qty for item in cart_items])

    # 3. 应用优惠券
    final_total = total_amount
    if coupon_id:
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if coupon and total_amount >= coupon.threshold:
            if coupon.type == "满减":
                final_total = total_amount - coupon.discount
            elif coupon.type == "折扣":
                final_total = total_amount * coupon.discount

    # 4. 创建订单主表
    new_order = Order(
        user_id=user_id,
        original_total=total_amount,
        total=final_total,
        coupon_id=coupon_id,
        status="待支付"
    )
    db.add(new_order)
    db.flush()  # 获取新生成的订单 ID

    # 5. 创建订单明细并清空购物车
    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            book_id=item.book_id,
            price=item.book.list_price,
            qty=item.qty
        )
        db.add(order_item)
        db.delete(item)  # 从购物车删掉

    db.commit()
    return {"status": "success", "order_id": new_order.id, "original_total": float(total_amount), "total": float(final_total)}
# 1. 库存查询
def check_stock(db: Session, book_id: int):
    inv = db.query(Inventory).filter(Inventory.book_id == book_id).first()
    return {"book_id": book_id, "stock": inv.stock if inv else 0}

# 2. 价格比价
def compare_price(db: Session, book_id: int):
    prices = db.query(BookPrice).filter(BookPrice.book_id == book_id).all()
    return [{"platform": p.platform, "price": float(p.price)} for p in prices]

# 3. 优惠券查询（传入当前总价，返回可用的券）
def query_coupons(db: Session, total_amount: float):
    coupons = db.query(Coupon).all()
    available = []
    for c in coupons:
        if total_amount >= float(c.threshold):
            available.append({
                "id": c.id, "name": c.name, "type": c.type,
                "threshold": float(c.threshold), "discount": float(c.discount)
            })
    return available

# 4. 评论查询（AI 阶段会在这里接大模型做摘要）
def get_reviews(db: Session, book_id: int):
    reviews = db.query(Review).filter(Review.book_id == book_id).all()
    return [{"user": r.user_name, "rating": float(r.rating), "content": r.content} for r in reviews]

# 5. 预算计算（纯数学逻辑，不需要查库，但可以查券）
def calc_budget(books_price: float, coupon_id: int = None, db: Session = None):
    final_price = books_price
    if coupon_id and db:
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if coupon and books_price >= float(coupon.threshold):
            if coupon.type == "满减":
                final_price -= float(coupon.discount)
            elif coupon.type == "折扣":
                final_price *= float(coupon.discount)
    return {"original": books_price, "final": round(final_price, 2)}

# 6. 物流查询
def query_logistics(db: Session, order_id: int):
    logs = db.query(Logistics).filter(Logistics.order_id == order_id).order_by(Logistics.time.desc()).all()
    return [{"node": l.node, "desc": l.description, "time": l.time.strftime("%Y-%m-%d %H:%M:%S")} for l in logs]