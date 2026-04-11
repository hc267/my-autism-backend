from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone

import models
import database
import time

# 1. 初始化数据库
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# 2. 配置跨域通行证
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 安全配置核心区 (密码加密 & JWT通行证)
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "autism_project_super_secret_key" 
ALGORITHM = "HS256" 
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def check_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="闯入者警告：请先登录获取通行证！")
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return user_id  
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="通行证已过期，请重新登录！")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="伪造的通行证，抓起来！")


# -------------------------------------------
# 质检员区 (数据模型)
# -------------------------------------------
class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "parent"

class UserLogin(BaseModel):
    email: str
    password: str

class ChildCreate(BaseModel):
    name: str
    age: int
    parent_id: int
    notes: Optional[str] = None

class SessionCreate(BaseModel):
    child_id: int
    level: int
    duration_seconds: int
    score: float
    emotion_stats: Dict[str, Any]

# 👇👇👇 这是我们为了对接前端神仙队友，新加的 3 个模具 👇👇👇
class EmotionDistribution(BaseModel):
    happy: float
    sad: float
    angry: float
    fearful: float
    disgusted: float
    surprised: float
    neutral: float

class DeviceInfo(BaseModel):
    platform: str
    browser: str

class SessionUpload(BaseModel):
    userId: str
    childId: str
    sessionId: str
    levelId: int
    targetEmotion: str
    recognizedEmotion: str
    success: bool
    score: int
    durationMs: int
    attemptCount: int
    stableVoteFrames: int
    threshold: float
    dominantConfidenceAvg: float
    emotionDistribution: EmotionDistribution
    deviceInfo: DeviceInfo
    startedAt: str
    endedAt: str
# 👆👆👆 新加模具结束 👆👆👆


# -------------------------------------------
# 接口区 (业务逻辑)
# -------------------------------------------
@app.post("/api/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    hashed_pwd = pwd_context.hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pwd, role=user.role)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"status": "success", "user_id": new_user.id}

@app.post("/api/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    access_token = create_access_token(data={"sub": str(db_user.id), "role": db_user.role})
    return {"status": "success", "user_id": db_user.id, "role": db_user.role, "access_token": access_token, "token_type": "bearer"}

@app.post("/api/children")
def create_child_profile(child_data: ChildCreate, db: Session = Depends(get_db)):
    new_child = models.Child(name=child_data.name, age=child_data.age, notes=child_data.notes)
    db.add(new_child); db.commit(); db.refresh(new_child)
    new_binding = models.Binding(user_id=child_data.parent_id, child_id=new_child.id)
    db.add(new_binding); db.commit()
    return {"status": "success", "child_id": new_child.id, "parent_id": child_data.parent_id}

@app.post("/api/sessions")
def upload_training_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    child = db.query(models.Child).filter(models.Child.id == session_data.child_id).first()
    if not child: raise HTTPException(status_code=404, detail="找不到这个孩子")
    new_session = models.Session(child_id=session_data.child_id, level=session_data.level, duration_seconds=session_data.duration_seconds, score=session_data.score, emotion_stats=session_data.emotion_stats)
    db.add(new_session); db.commit(); db.refresh(new_session)
    return {"status": "success", "session_id": new_session.id}

@app.post("/api/sessions/upload", tags=["与前端对齐的接口"])
def upload_session_from_frontend(session_data: SessionUpload, db: Session = Depends(get_db)):
    # 1. 把前端发来的所有复杂数据，打包成一个字典，准备塞进我们的 JSONB 神器里
    stats_data = session_data.dict() 
    
    # 2. ⚠️ 小细节处理：前端示例给的 childId 是字符串 "c001"，但我们的数据库是整数(1, 2, 3)
    try:
        real_child_id = int(session_data.childId.replace("c", ""))
    except ValueError:
        real_child_id = 1 
        
    # 3. 实例化我们的一条数据库记录
    new_session = models.Session(
        child_id=real_child_id,
        level=session_data.levelId,
        duration_seconds=session_data.durationMs // 1000,
        score=session_data.score,
        emotion_stats=stats_data
    )
    
    # 4. 打开金库大门，把数据存进去，然后锁门！
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    print(f"🔥 太牛了！前端的数据已经成功存入 PostgreSQL！数据库生成的真实记录 ID 是: {new_session.id}")
    
    # 5. 给前端返回成功的结账单
    return {
        "code": 200, 
        "message": "后端大厨已收到！数据完美存入 PostgreSQL 金库！", 
        "data": {
            "received_sessionId": session_data.sessionId,
            "database_inserted_id": new_session.id
        }
    }

@app.get("/api/children/{child_id}/sessions")
def get_child_sessions(child_id: int, db: Session = Depends(get_db)):
    sessions = db.query(models.Session).filter(models.Session.child_id == child_id).all()
    return {"status": "success", "data": sessions}

@app.get("/api/analyze/{session_id}")
def analyze_session_emotions(session_id: int, db: Session = Depends(get_db)):
    session_record = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_record: raise HTTPException(status_code=404, detail="找不到这次记录")
    time.sleep(1) 
    focus_level = session_record.emotion_stats.get("focus", 0)
    if focus_level > 0.7: ai_advice = "专注度极高，建议保持。"
    elif focus_level > 0.4: ai_advice = "表现平稳，建议增加引导。"
    else: ai_advice = "专注度偏低，建议更换主题。"
    return {"status": "success", "session_id": session_id, "ai_analysis": {"focus_score": focus_level, "professional_advice": ai_advice}}

@app.get("/api/users/{user_id}/children")
def get_parent_children(user_id: int, db: Session = Depends(get_db)):
    bindings = db.query(models.Binding).filter(models.Binding.user_id == user_id).all()
    if not bindings: return {"status": "success", "message": "暂无绑定儿童", "data": []}
    child_ids = [binding.child_id for binding in bindings]
    children = db.query(models.Child).filter(models.Child.id.in_(child_ids)).all()
    return {"status": "success", "data": children}


# 👇👇👇 升级版：家长数据看板 (智能提炼 JSONB 数据) 👇👇👇
@app.get("/api/children/{child_id}/statistics", tags=["与前端对齐的接口"])
def get_child_statistics(child_id: int, db: Session = Depends(get_db)):
    # 1. 把这个孩子所有的训练记录从金库里搬出来
    sessions = db.query(models.Session).filter(models.Session.child_id == child_id).all()
    
    # 2. 如果这孩子还没训练过，直接告诉前端没数据
    if not sessions: 
        return {"code": 200, "message": "暂无数据", "data": None}
    
    # 3. 准备好我们 7 种情绪的“计算器”
    total_distribution = {
        "happy": 0.0, "sad": 0.0, "angry": 0.0, "fearful": 0.0, 
        "disgusted": 0.0, "surprised": 0.0, "neutral": 0.0
    }
    valid_sessions_count = 0
    
    # 4. 核心魔法：循环每一张账单，把 JSONB 里的零碎数据提炼出来加在一起
    for s in sessions:
        stats = s.emotion_stats # 这里直接取出了那个极其复杂的 JSON 字典！
        if isinstance(stats, dict) and "emotionDistribution" in stats:
            dist = stats["emotionDistribution"]
            # 累加 7 种情绪的数值
            for emotion in total_distribution.keys():
                total_distribution[emotion] += dist.get(emotion, 0.0)
            valid_sessions_count += 1
            
    # 5. 计算平均值（算出这个孩子各项情绪的平均表现，准备画雷达图）
    radar_data = {}
    if valid_sessions_count > 0:
        for emotion, total in total_distribution.items():
            radar_data[emotion] = round(total / valid_sessions_count, 2) # 保留两位小数
            
    # 6. 打包成前端最爱看的格式，直接端上桌！
    return {
        "code": 200, 
        "message": "数据统计成功！", 
        "data": {
            "overview": {
                "total_sessions": len(sessions),
                "highest_score": max([s.score for s in sessions]) if sessions else 0
            },
            "radar_chart_data": radar_data
        }
    }
# 👆👆👆 升级版看板代码结束 👆👆👆