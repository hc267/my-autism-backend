from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime, ForeignKey, Float, Boolean, Date, Text
from sqlalchemy.dialects.postgresql import JSONB # 杀手锏就位！
from database import Base
import datetime
import enum

# ==========================================
# 枚举定义区 (严格遵循 UI 规范)
# ==========================================
class UserRole(str, enum.Enum):
    child = "child"
    parent = "parent"
    therapist = "therapist"

class GenderType(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

# UI 规范第3条：严格锁定的7大情绪标签
class EmotionType(str, enum.Enum):
    happy = "happy"
    sad = "sad"
    angry = "angry"
    fearful = "fearful"
    disgusted = "disgusted"
    surprised = "surprised"
    neutral = "neutral"

# ==========================================
# 1. 用户表 (Users) - 存放家长和治疗师
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) 
    role = Column(SQLEnum(UserRole), default=UserRole.parent) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 扩展字段
    nickname = Column(String, nullable=True)     
    avatar_url = Column(String, nullable=True)   
    phone = Column(String, nullable=True)        
    vip_status = Column(Boolean, default=False)  
    remaining_times = Column(Integer, default=10)

# ==========================================
# 2. 儿童表 (Children) - 对齐 Figma 个人主页
# ==========================================
class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    # 【修改】：用 birth_date 替代 age，前端自动算年龄更准确
    birth_date = Column(Date, nullable=True) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # --- Figma 界面必须的字段 ---
    avatar_url = Column(String, nullable=True)        # 儿童专属头像（核心缺失已补）
    real_name = Column(String, nullable=True)         # 真实姓名
    gender = Column(SQLEnum(GenderType), nullable=True) # 性别
    guardian_name = Column(String, nullable=True)     # 监护人姓名
    guardian_relation = Column(String, nullable=True) # 监护人关系 (如: 妈妈)
    
    # --- 扩展/游戏化字段 ---
    diagnosis_level = Column(String, nullable=True)   
    star_count = Column(Integer, default=0)           # 星星/金币总量 (触发 UI 的星星动画后累加)
    continuous_days = Column(Integer, default=0)      
    last_training_date = Column(Date, nullable=True)  
    preferences = Column(JSONB, nullable=True)        # 强大的 JSONB 存偏好设置

# ==========================================
# 3. 绑定关系表 (Bindings)
# ==========================================
class Binding(Base):
    __tablename__ = "bindings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))     
    child_id = Column(Integer, ForeignKey("children.id")) 

# ==========================================
# 4. 勋章系统表 (Badges & ChildBadges) - 激励系统
# ==========================================
class Badge(Base):
    __tablename__ = "badges"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                 # 勋章名，如"情绪小雷达"
    description = Column(String)                      # 描述
    icon_url = Column(String)                         # 勋章图标

class ChildBadge(Base):
    __tablename__ = "child_badges"
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"))
    badge_id = Column(Integer, ForeignKey("badges.id"))
    earned_at = Column(DateTime, default=datetime.datetime.utcnow)

# ==========================================
# 5. 关卡配置表 (TrainingUnits) - 支撑 UI 第 1 条规范
# ==========================================
class TrainingUnit(Base):
    __tablename__ = "training_units"
    # 这个表专门给前端下发“关卡长啥样”的数据，实现动态配置
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                 # 如 "初级表情识别"
    theme_color = Column(String)                      # UI主题色：如 "#F2C879"
    target_emotions = Column(JSONB)                   # 本关目标情绪，如 ["happy", "surprised"]

# ==========================================
# 6. 训练报表 (Reports & Details) - 支撑 Figma 数据图表
# ==========================================
class TrainingReport(Base):
    __tablename__ = "training_reports"
    # 一次完整的闯关记录
    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id")) 
    unit_id = Column(Integer, ForeignKey("training_units.id")) # 玩的是哪个关卡
    duration_seconds = Column(Integer)    
    overall_accuracy = Column(Float)                  # 总体正确率 (如 0.85 代表 85%)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TrainingReportDetail(Base):
    __tablename__ = "training_report_details"
    # 灵魂表格！用于画出 UI 里的“各情绪折线图/饼图”
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("training_reports.id"))
    emotion_type = Column(SQLEnum(EmotionType))       # 严格限制 7 种情绪之一
    total_prompts = Column(Integer, default=0)        # 这局游戏里该情绪出现了几次
    correct_answers = Column(Integer, default=0)      # 孩子答对了几次 (UI 弹星星的次数)