import os  # 导入系统模块，用来读取云端的环境变量
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 1. 获取数据库连接字符串 ---
# 逻辑：优先读取云端环境变量，本地运行则兜底使用 localhost
SQLALCHEMY_DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL", 
    "postgresql://admin:password123@localhost:5432/autism_db"
)

# --- 2. 兼容性处理 ---
# 修复 Render 或某些云平台提供的 postgres:// 前缀，统一转为 SQLAlchemy 要求的 postgresql://
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- 3. 创建连接引擎 (重点优化部分) ---
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # 🌟 核心修复：
    # pool_pre_ping=True 会在每次执行 SQL 之前先检查连接是否还有效（Ping一下）
    # 如果连接被 Render 踢掉了，它会自动创建新连接，避免报错 "server closed connection"
    pool_pre_ping=True,
    # 每 1800 秒（30分钟）重置连接池，防止连接因长时间闲置被云端强制断开
    pool_recycle=1800
)

# --- 4. 创建会话工厂 ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 5. 创建所有表的基类 ---
Base = declarative_base()