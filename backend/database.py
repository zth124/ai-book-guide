import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 加载 .env 文件中的配置
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# 拼接数据库连接地址 (格式: mysql+pymysql://用户:密码@地址:端口/库名)
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 创建数据库引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)
# 创建会话工厂，用于后续每次请求时操作数据库
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 创建基类，用来定义数据表模型
Base = declarative_base()

# 获取数据库会话的工具函数，用在 FastAPI 接口里
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()