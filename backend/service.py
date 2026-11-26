from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Book, CartItem, Order, OrderItem,BookPrice, Inventory, Review, Coupon, Logistics, User
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime


# 纯函数：根据关键词、难度、分类查书
def search_books(db: Session, keyword: str = None, level: str = None, category: str = None):
    query = db.query(Book)

    if keyword:
        # 模糊搜索书名、作者或 tags（前端搜索框提示的是"书名、作者、标签"，这里必须三处都覆盖）
        like = f"%{keyword}%"
        query = query.filter((Book.title.like(like)) | (Book.author.like(like)) | (Book.tags.like(like)))
    if level:
        query = query.filter(Book.level == level)
    if category:
        query = query.filter(Book.category == category)

    # 限制最多返回 10 本
    return query.limit(10).all()


# 纯函数：加入购物车
def add_to_cart(db: Session, user_id: int, book_id: int, qty: int = 1):
    # 先校验：用户和图书都存在，数量合法。否则直接给业务错误，而不是让外键抛 500
    if not db.query(User).filter(User.id == user_id).first():
        raise ValueError(f"用户 {user_id} 不存在")
    if not db.query(Book).filter(Book.id == book_id).first():
        raise ValueError(f"图书 {book_id} 不存在")
    if qty is None or qty <= 0:
        raise ValueError("购买数量必须大于 0")

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


# 纯函数：查看购物车（item_ids 为空表示全部）
def get_cart(db: Session, user_id: int, item_ids=None):
    q = db.query(CartItem).filter(CartItem.user_id == user_id)
    if item_ids:
        q = q.filter(CartItem.id.in_(item_ids))
    items = q.all()
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


# 纯函数：创建订单（可按选中的购物车条目结算）
def create_order(db: Session, user_id: int, coupon_id: int = None, item_ids=None):
    # 1. 获取要结算的购物车条目（item_ids 为空则整车结算）
    q = db.query(CartItem).filter(CartItem.user_id == user_id)
    if item_ids:
        q = q.filter(CartItem.id.in_(item_ids))
    cart_items = q.all()
    if not cart_items:
        raise ValueError("未选择要结算的图书" if item_ids else "购物车为空")

    # 2. 库存校验：任意一本不够就整单拒绝，且在写库之前检查，避免产生半张订单。
    #    用 with_for_update() 对库存行加锁，把"先查再减"变成原子操作，防止并发下单超卖。
    locked_inv = {}
    for item in cart_items:
        inv = (db.query(Inventory)
               .filter(Inventory.book_id == item.book_id)
               .with_for_update()
               .first())
        locked_inv[item.book_id] = inv
        stock = inv.stock if inv else 0
        if stock < item.qty:
            raise ValueError(f"《{item.book.title}》库存不足（仅剩 {stock} 本）")

    # 3. 计算总价
    total_amount = sum([item.book.list_price * item.qty for item in cart_items])

    # 4. 应用优惠券（与购物车结算页共用 apply_coupon，过期券在里面会被判为不可用）
    final_total = total_amount
    applied_coupon_id = None
    if coupon_id:
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        final_total, saved = apply_coupon(total_amount, coupon)
        applied_coupon_id = coupon_id if saved > 0 else None

    # 5. 创建订单主表
    new_order = Order(
        user_id=user_id,
        original_total=total_amount,
        total=final_total,
        coupon_id=applied_coupon_id,
        status="待支付"
    )
    db.add(new_order)
    db.flush()  # 获取新生成的订单 ID

    # 6. 创建订单明细、扣减库存、清空购物车
    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            book_id=item.book_id,
            price=item.book.list_price,
            qty=item.qty
        )
        db.add(order_item)
        # 复用第 2 步已加锁的库存行，避免二次查询拿到旧值
        inv = locked_inv.get(item.book_id)
        if inv:
            inv.stock = inv.stock - item.qty
        db.delete(item)  # 从购物车删掉

    db.commit()
    return {"status": "success", "order_id": new_order.id, "original_total": float(total_amount), "total": float(final_total)}
# 1. 库存查询（exists 用于区分“书不存在”和“库存为 0”）
def check_stock(db: Session, book_id: int):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return {"book_id": book_id, "exists": False, "stock": 0}
    inv = db.query(Inventory).filter(Inventory.book_id == book_id).first()
    return {"book_id": book_id, "exists": True, "stock": inv.stock if inv else 0}

# 2. 价格比价
def compare_price(db: Session, book_id: int):
    prices = db.query(BookPrice).filter(BookPrice.book_id == book_id).all()
    return [{"platform": p.platform, "price": float(p.price)} for p in prices]

# 3. 优惠券查询（传入当前总价，返回可用的券；过期券不返回）
def query_coupons(db: Session, total_amount: float):
    coupons = db.query(Coupon).all()
    available = []
    for c in coupons:
        if not is_coupon_valid(c):
            continue
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


# ---------------------------------------------------------------------------
# 7. 优惠券计算（全项目唯一的算钱口径）
#    AI 方案卡片、购物车结算页、创建订单三处都用这里的函数，
#    避免出现“页面显示一个价、下单又是另一个价”。
# ---------------------------------------------------------------------------

def is_coupon_valid(coupon, on=None):
    """券是否在有效期内。expire 是到期日（含当天），空值视为不限期。"""
    if coupon is None:
        return False
    expire = getattr(coupon, "expire", None)
    if expire is None:
        return True
    return expire >= (on or date.today())


def apply_coupon(total, coupon):
    """按券规则算实付，返回 (实付金额, 优惠金额)，都是 Decimal。过期券不生效。"""
    total = Decimal(str(total))
    if coupon is None or not is_coupon_valid(coupon) or total < Decimal(str(coupon.threshold)):
        return total, Decimal("0.00")
    if coupon.type == "满减":
        final = total - Decimal(str(coupon.discount))
    elif coupon.type == "折扣":
        final = total * Decimal(str(coupon.discount))
    else:
        final = total
    final = final.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if final < 0:
        final = Decimal("0.00")
    return final, (total - final).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pick_best_coupon(db: Session, total):
    """在满足门槛的券里挑最省钱的一张，返回 (券, 实付, 优惠)"""
    total = Decimal(str(total))
    best, best_final, best_saved = None, total, Decimal("0.00")
    for c in db.query(Coupon).all():
        final, saved = apply_coupon(total, c)
        if final < best_final:
            best, best_final, best_saved = c, final, saved
    return best, best_final, best_saved


def cart_summary(db: Session, user_id: int, coupon_id: int = None, item_ids=None):
    """购物车金额汇总（只算选中的条目）。传了 coupon_id 就严格按该券计算，
    不传就是不用券。优惠的“选哪张”只在 AI 方案阶段由 pick_best_coupon 决定，
    购物车只负责如实展示，不再自己挑券、自己算优惠。"""
    items = get_cart(db, user_id, item_ids)
    original = sum((Decimal(str(i["subtotal"])) for i in items), Decimal("0.00"))
    original = original.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if original <= 0:
        return {"items": items, "original_total": 0.0, "total": 0.0,
                "saved": 0.0, "coupon": None}

    coupon = None
    final, saved = original, Decimal("0.00")
    if coupon_id:
        candidate = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if candidate is not None and is_coupon_valid(candidate):
            final, saved = apply_coupon(original, candidate)
            # 即使当前所选金额没达到门槛，也把券信息带回去（applicable=false），
            # 前端据此保留券，而不是误以为券失效把它清掉
            coupon = {
                "id": candidate.id, "name": candidate.name,
                "type": candidate.type, "discount": float(candidate.discount),
                "applicable": saved > 0,
            }

    return {
        "items": items,
        "original_total": float(original),
        "total": float(final),
        "saved": float(saved),
        "coupon": coupon,
    }


# ---------------------------------------------------------------------------
# 8. 用户：注册 / 登录 / 资料修改 / 头像
# ---------------------------------------------------------------------------

import base64
import hashlib
import hmac
import os
import secrets

# 头像保存目录：backend/uploads/avatars（容器里由 volume 或镜像目录承载）
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "avatars")
MAX_AVATAR_BYTES = 1_200_000   # 单张头像上限 ~1.2MB，前端已压到 512px，正常远小于此


def _hash_password(password: str, salt: str = None):
    """PBKDF2-SHA256 加盐哈希，返回 "盐$哈希"。不存明文密码。"""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def _check_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, expect = stored.split("$", 1)
    calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return hmac.compare_digest(calc, expect)


def _validate_name(name: str) -> str:
    name = (name or "").strip()
    if len(name) < 2:
        raise ValueError("用户名至少 2 个字")
    if len(name) > 20:
        raise ValueError("用户名不能超过 20 个字")
    return name


def _validate_password(password: str):
    password = password or ""
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    if len(password) > 32:
        raise ValueError("密码不能超过 32 位")
    return password


def _user_payload(user: User, db: Session = None):
    """统一的用户出参；带 db 时顺带统计订单/购物车/累计消费，供"我的"页展示。"""
    data = {
        "id": user.id,
        "name": user.name,
        "avatar": user.avatar or "",
        "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else "",
    }
    if db is not None:
        order_count = db.query(Order).filter(Order.user_id == user.id).count()
        cart_qty = (db.query(CartItem)
                    .filter(CartItem.user_id == user.id)
                    .with_entities(func.coalesce(func.sum(CartItem.qty), 0))
                    .scalar() or 0)
        spent = (db.query(Order)
                 .filter(Order.user_id == user.id, Order.status == "已支付")
                 .with_entities(func.coalesce(func.sum(Order.total), 0))
                 .scalar() or 0)
        data.update({
            "order_count": int(order_count),
            "cart_qty": int(cart_qty),
            "spent": float(spent),
        })
    return data


def register_user(db: Session, name: str, password: str):
    """注册：用户名唯一，密码加盐哈希后入库。"""
    name = _validate_name(name)
    password = _validate_password(password)
    if db.query(User).filter(User.name == name).first():
        raise ValueError("这个用户名已经被注册了，换一个吧")

    user = User(name=name, password_hash=_hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_payload(user)


def login_user(db: Session, name: str, password: str = ""):
    """登录：校验密码。
    历史账号（password_hash 为空，例如初始化脚本里的"测试用户"）第一次登录时绑定本次输入的密码。"""
    name = (name or "").strip()
    if not name:
        raise ValueError("请输入用户名")
    password = password or ""
    if not password:
        raise ValueError("请输入密码")

    user = db.query(User).filter(User.name == name).first()
    if not user:
        raise ValueError("账号不存在，请先注册")

    if not user.password_hash:
        # 老账号首次登录：把这次输入的密码设为账号密码
        user.password_hash = _hash_password(_validate_password(password))
        db.commit()
        db.refresh(user)
        return _user_payload(user)

    if not _check_password(password, user.password_hash):
        raise ValueError("密码不正确")
    return _user_payload(user)


def get_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    return _user_payload(user, db)


def update_user_name(db: Session, user_id: int, name: str):
    """改用户名：仍要求唯一。购物车/订单都按 user_id 关联，改名不影响已有数据。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    name = _validate_name(name)
    if name == user.name:
        return _user_payload(user, db)
    if db.query(User).filter(User.name == name).first():
        raise ValueError("这个用户名已经被占用了")
    user.name = name
    db.commit()
    db.refresh(user)
    return _user_payload(user, db)


def save_avatar(db: Session, user_id: int, data_url: str):
    """保存头像：前端把图片压成 512px 的 JPEG dataURL 传上来，这里解码落盘。
    返回文件名，文件由 /api/users/{id}/avatar 这个接口读出来给 <img> 用。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if not data_url or "base64," not in data_url:
        raise ValueError("图片数据不合法")

    header, payload = data_url.split("base64,", 1)
    if "image/" not in header:
        raise ValueError("只支持 JPG / PNG 等图片格式")
    try:
        raw = base64.b64decode(payload, validate=True)
    except Exception:
        raise ValueError("图片解析失败，请换一张试试")
    if len(raw) > MAX_AVATAR_BYTES:
        raise ValueError("图片太大，请选择 2MB 以内的图片")
    if not raw:
        raise ValueError("图片内容为空")

    os.makedirs(AVATAR_DIR, exist_ok=True)
    # 文件名带时间戳：同一个人换头像后 URL 也随之变化，浏览器不会拿旧图缓存
    filename = f"{user_id}_{int(datetime.now().timestamp() * 1000)}.jpg"
    with open(os.path.join(AVATAR_DIR, filename), "wb") as f:
        f.write(raw)

    # 删掉上一张，避免目录里越堆越多
    if user.avatar:
        old = os.path.join(AVATAR_DIR, user.avatar)
        if os.path.exists(old):
            try:
                os.remove(old)
            except OSError:
                pass

    user.avatar = filename
    db.commit()
    db.refresh(user)
    return _user_payload(user, db)


def clear_avatar(db: Session, user_id: int):
    """恢复默认头像（首字母）：删文件并清空字段。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("用户不存在")
    if user.avatar:
        path = os.path.join(AVATAR_DIR, user.avatar)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    user.avatar = None
    db.commit()
    db.refresh(user)
    return _user_payload(user, db)


def avatar_file(db: Session, user_id: int):
    """返回该用户头像的磁盘路径；没设置时返回 None。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar:
        return None
    return os.path.join(AVATAR_DIR, user.avatar)


def list_orders(db: Session, user_id: int):
    """查询某用户的全部订单（新单在前），带上明细与状态，供订单页展示。"""
    orders = (db.query(Order)
              .filter(Order.user_id == user_id)
              .order_by(Order.id.desc())
              .all())
    result = []
    for o in orders:
        items = []
        for it in o.items:
            items.append({
                "book_id": it.book_id,
                "title": it.book.title if it.book else f"图书 {it.book_id}",
                "price": float(it.price),
                "qty": it.qty,
                "subtotal": float(it.price) * it.qty,
            })
        result.append({
            "order_id": o.id,
            "status": o.status,
            "original_total": float(o.original_total),
            "total": float(o.total),
            "coupon_id": o.coupon_id,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S") if o.created_at else "",
            "items": items,
            "item_count": sum(i["qty"] for i in items),
        })
    return result


# ---------------------------------------------------------------------------
# 9. 模拟支付：把待支付订单置为已支付，并写入物流节点
#    真实项目里这一步是第三方支付回调；课程项目里由用户在订单页点"去支付"触发
# ---------------------------------------------------------------------------

def pay_order(db: Session, order_id: int):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError(f"订单 {order_id} 不存在")
    if order.status != "待支付":
        # 幂等：重复点击不报错，也不重复写物流
        return {"order_id": order.id, "status": order.status, "paid": False,
                "message": f"订单当前状态为「{order.status}」，无需重复支付"}

    # 物流时间线起点：先用订单创建时间补一条"已下单"
    if db.query(Logistics).filter(Logistics.order_id == order_id).count() == 0:
        db.add(Logistics(
            order_id=order_id,
            node="已下单",
            description="订单创建成功，等待支付",
            time=order.created_at or datetime.now(),
        ))

    order.status = "已支付"
    db.add(Logistics(
        order_id=order_id,
        node="已支付",
        description="支付成功，商家将尽快接单发货",
        time=datetime.now(),
    ))
    db.commit()
    return {"order_id": order.id, "status": order.status, "paid": True, "message": "支付成功"}