from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Float, Boolean, Date
from sqlalchemy.dialects.postgresql import JSONB # 重新请回杀手锏 JSONB！
from database import Base
import datetime
import enum

# ==========================================
# 角色枚举定义
# ==========================================
class UserRole(str, enum.Enum):
    child = "child"
    parent = "parent"
    therapist = "therapist"

# ==========================================
# 1. 用户表 (Users) - 存放家长和治疗师的登录账号
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) 
    role = Column(Enum(UserRole), default=UserRole.parent) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # --- 根据 Figma 规范新增字段 ---
    nickname = Column(String, nullable=True)     # 昵称
    avatar_url = Column(String, nullable=True)   # 头像链接
    phone = Column(String, nullable=True)        # 手机号
    vip_status = Column(Boolean, default=False)  # 是否是VIP
    remaining_times = Column(Integer, default=10)# 剩余训练次数

# ==========================================
# 2. 儿童表 (Children) - 存放自闭症儿童的基础信息
# ==========================================
class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    notes = Column(String, nullable=True) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # --- 根据 Figma 规范新增字段 ---
    gender = Column(String, nullable=True)            # 性别
    diagnosis_level = Column(String, nullable=True)   # 确诊程度：轻度/中度/重度
    interest_tags = Column(String, nullable=True)     # 兴趣标签（如：恐龙, 绘画）
    star_count = Column(Integer, default=0)           # 获得的星星/金币总量
    continuous_days = Column(Integer, default=0)      # 连续打卡天数
    last_training_date = Column(Date, nullable=True)  # 最后训练日期，用于计算打卡
    preferences = Column(JSONB, nullable=True)        # 偏好设置：使用强大的 JSONB

# ==========================================
# 3. 绑定关系表 (Bindings) - 连结家长/治疗师与儿童
# ==========================================
class Binding(Base):
    __tablename__ = "bindings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))     
    child_id = Column(Integer, ForeignKey("children.id")) 

# ==========================================
# 4. 训练记录表 (Sessions) - 核心业务表
# ==========================================
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id")) 
    level = Column(Integer)               
    duration_seconds = Column(Integer)    
    score = Column(Float)                 
    emotion_stats = Column(JSONB)         # 情绪数据：使用强大的 JSONB
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # --- 根据 Figma 规范新增字段 ---
    game_name = Column(String, default="未定义游戏") # 游戏关卡名称