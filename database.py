from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 这里的账号密码和我们在 docker-compose.yml 里写的一模一样
SQLALCHEMY_DATABASE_URL = "postgresql://admin:password123@localhost:5432/autism_db"

# 创建连接引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表的基类
Base = declarative_base()