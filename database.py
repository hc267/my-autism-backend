import os  # 导入系统模块，用来读取云端的环境变量
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 核心修改开始 ---
# 这里的逻辑是：
# 1. 优先尝试读取名为 "SQLALCHEMY_DATABASE_URL" 的环境变量（Render 云端会提供这个）
# 2. 如果找不到（比如在你自己的电脑上运行），就自动使用后面那个 localhost 的默认值
SQLALCHEMY_DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL", 
    "postgresql://admin:password123@localhost:5432/autism_db"
)
# --- 核心修改结束 ---

# 创建连接引擎
# 注意：对于 PostgreSQL，有时在云端需要处理连接协议头，SQLAlchemy 1.4+ 推荐确保是 postgresql:// 开头
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表的基类
Base = declarative_base()