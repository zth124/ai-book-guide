from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# ... 原来 Book 的代码保持不变 ...
class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    author = Column(String(100))
    publisher = Column(String(100))
    category = Column(String(50))
    level = Column(String(20))
    rating = Column(Numeric(2, 1))
    list_price = Column(Numeric(10, 2))
    description = Column(Text)
    tags = Column(String(200))

# 购物车表
class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    qty = Column(Integer, default=1)
    added_at = Column(DateTime, server_default=func.now())

    # 关联图书表，方便查购物车时直接带出书名和价格
    book = relationship("Book")

# 订单主表
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    original_total = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    coupon_id = Column(Integer, nullable=True)
    status = Column(String(20), default="待支付")
    created_at = Column(DateTime, server_default=func.now())

    # 关联订单明细
    items = relationship("OrderItem", back_populates="order")

# 订单明细表
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    qty = Column(Integer, default=1)

    order = relationship("Order", back_populates="items")
    book = relationship("Book")

 # 价格表（比价用）
class BookPrice(Base):
    __tablename__ = "book_prices"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    platform = Column(String(50))
    price = Column(Numeric(10, 2))

    # 库存表
class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), unique=True)
    stock = Column(Integer, default=0)

    # 评论表
class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    user_name = Column(String(50))
    rating = Column(Numeric(2, 1))
    content = Column(Text)

    # 优惠券表
class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    type = Column(String(20))
    threshold = Column(Numeric(10, 2))
    discount = Column(Numeric(10, 2))

    # 物流表
class Logistics(Base):
    __tablename__ = "logistics"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    node = Column(String(50))
    description = Column(String(200))
    time = Column(DateTime, server_default=func.now())


