from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # 🔥 新增：Swagger 绿锁召唤术
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone, date
from sqlalchemy import text  

import models
import database
import time

# 1. 初始化数据库 (确保表结构存在)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# 👇 新增：专门给 Render 机器人准备的健康检查门铃 👇
@app.get("/", tags=["系统检测"])
def health_check():
    return {"status": "ok", "message": "Render 你好，我的服务器活得很好，请不要杀我！"}

# 👇 终极后门：云端起爆按钮 👇
@app.get("/api/dev/reset-db", tags=["系统检测"])
def reset_database_from_cloud():
    try:
        with database.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
        
        # 重新按照图纸建表
        models.Base.metadata.create_all(bind=database.engine)
        return {"status": "success", "message": "💣 轰！云端数据库已彻底重置，所有新字段已生效！"}
    except Exception as e:
        return {"status": "error", "message": f"爆破失败: {str(e)}"}


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

# 🔥 告诉 Swagger 我们使用的是标准的 Bearer Token 鉴权体系
security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 🔥 修复：使用 HTTPBearer 接收前端的凭证，这样 Swagger 才会画出绿色小锁
def check_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return user_id  
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="通行证已过期，请重新登录！")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="伪造的通行证，抓起来！")

# ==========================================
# 质检员区 (Pydantic 数据模型)
# ==========================================
class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "parent"

class UserLogin(BaseModel):
    email: str
    password: str

class ChildCreate(BaseModel):
    name: str
    birth_date: date  
    parent_id: int
    avatar_url: Optional[str] = None     
    real_name: Optional[str] = None      
    gender: Optional[str] = None         
    notes: Optional[str] = None

class EmotionDetail(BaseModel):
    emotion_type: str       
    total_prompts: int      
    correct_answers: int    

class SessionUploadNew(BaseModel):
    child_id: int           
    unit_id: int            
    duration_seconds: int   
    overall_accuracy: float 
    details: List[EmotionDetail] 

# ==========================================
# 接口区 (业务逻辑)
# ==========================================

@app.get("/api/dev/init-units", tags=["系统检测"])
def init_units(db: DBSession = Depends(get_db)):
    try:
        db.query(models.TrainingUnit).delete()
        unit1 = models.TrainingUnit(id=1, name="第一关")
        unit2 = models.TrainingUnit(id=2, name="第二关")
        db.add(unit1); db.add(unit2); db.commit()
        return {"status": "success", "message": "✅ 关卡数据（Unit 1 & 2）已极简初始化成功！"}
    except Exception as e:
        return {"status": "error", "message": f"初始化失败: {str(e)}"}
    
@app.post("/api/register", tags=["账号权限"])
def register_user(user: UserCreate, db: DBSession = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
        
    safe_password = user.password.strip().encode('utf-8')[:72].decode('utf-8', 'ignore')
    hashed_pwd = pwd_context.hash(safe_password)
    
    new_user = models.User(email=user.email, hashed_password=hashed_pwd, role=user.role)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"status": "success", "user_id": new_user.id}

@app.post("/api/login", tags=["账号权限"])
def login_user(user: UserLogin, db: DBSession = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    safe_password = user.password.strip().encode('utf-8')[:72].decode('utf-8', 'ignore')
    
    if not db_user or not pwd_context.verify(safe_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
        
    access_token = create_access_token(data={"sub": str(db_user.id), "role": db_user.role})
    return {"status": "success", "user_id": db_user.id, "role": db_user.role, "access_token": access_token, "token_type": "bearer"}

# 🔒 注意：这里加了 current_user_id = Depends(check_token)，意味着必须带 Token 才能访问！
@app.get("/api/users/{user_id}/children", tags=["儿童管理"])
def get_parent_children(user_id: int, db: DBSession = Depends(get_db), current_user_id: str = Depends(check_token)):
    bindings = db.query(models.Binding).filter(models.Binding.user_id == user_id).all()
    if not bindings: return {"status": "success", "message": "暂无绑定儿童", "data": []}
    child_ids = [binding.child_id for binding in bindings]
    children = db.query(models.Child).filter(models.Child.id.in_(child_ids)).all()
    return {"status": "success", "data": children}

# 🔓 公开接口：获取题库不需要鉴权
@app.get("/api/training-units", tags=["与前端对齐的接口"])
def get_training_units(db: DBSession = Depends(get_db)):
    units = db.query(models.TrainingUnit).all()
    return {"code": 200, "message": "关卡配置获取成功", "data": units}

# 🔒 必须带 Token
@app.post("/api/children", tags=["儿童管理"])
def create_child_profile(child_data: ChildCreate, db: DBSession = Depends(get_db), current_user_id: str = Depends(check_token)):
    new_child = models.Child(
        name=child_data.name, 
        birth_date=child_data.birth_date,
        avatar_url=child_data.avatar_url,
        real_name=child_data.real_name,
        gender=child_data.gender
    )
    db.add(new_child); db.commit(); db.refresh(new_child)
    
    new_binding = models.Binding(user_id=child_data.parent_id, child_id=new_child.id)
    db.add(new_binding); db.commit()
    return {"code": 200, "message": "儿童档案创建成功！", "child_id": new_child.id}

# 🔒 必须带 Token
@app.post("/api/sessions/upload", tags=["与前端对齐的接口"])
def upload_session_from_frontend(session_data: SessionUploadNew, db: DBSession = Depends(get_db), current_user_id: str = Depends(check_token)):
    new_report = models.TrainingReport(
        child_id=session_data.child_id,
        unit_id=session_data.unit_id,
        duration_seconds=session_data.duration_seconds,
        overall_accuracy=session_data.overall_accuracy
    )
    db.add(new_report); db.commit(); db.refresh(new_report)

    for detail in session_data.details:
        new_detail = models.TrainingReportDetail(
            report_id=new_report.id,
            emotion_type=detail.emotion_type,
            total_prompts=detail.total_prompts,
            correct_answers=detail.correct_answers
        )
        db.add(new_detail)
    db.commit()

    return {"code": 200, "message": "成绩单已完美拆分存入金库！", "data": {"report_id": new_report.id}}

# 🔒 必须带 Token
@app.get("/api/children/{child_id}/sessions", tags=["数据分析"])
def get_child_sessions(child_id: int, db: DBSession = Depends(get_db), current_user_id: str = Depends(check_token)):
    reports = db.query(models.TrainingReport).filter(models.TrainingReport.child_id == child_id).all()
    return {"status": "success", "data": reports}

# 🔒 必须带 Token
@app.get("/api/analyze/{report_id}", tags=["数据分析"])
def analyze_session_emotions(report_id: int, db: DBSession = Depends(get_db), current_user_id: str = Depends(check_token)):
    report = db.query(models.TrainingReport).filter(models.TrainingReport.id == report_id).first()
    if not report: raise HTTPException(status_code=404, detail="找不到这次记录")
    
    accuracy = report.overall_accuracy
    if accuracy > 0.8: ai_advice = "表现非常棒，准确率极高，建议保持目前的训练难度。"
    elif accuracy > 0.5: ai_advice = "表现平稳，部分情绪容易混淆，建议多做针对性巩固。"
    else: ai_advice = "准确率偏低，可能是不在状态，建议更换轻松的主题或稍作休息。"
    
    return {"status": "success", "report_id": report_id, "ai_analysis": {"overall_accuracy": accuracy, "professional_advice": ai_advice}}

# 🔓 故事接口不需要 token
@app.get("/api/ai/story", tags=["AI 互动 (Mock)"])
def get_mock_ai_story(target_emotion: str = "happy"):
    mock_stories = {
        "happy": "今天在幼儿园，老师奖励了一朵小红花，小朋友感到非常高兴！",
        "sad": "心爱的玩具不小心掉在地上摔坏了，小朋友觉得很难过。",
        "angry": "搭好的积木被别人碰倒了，小朋友感到有些生气。",
        "fearful": "突然听到好大一声雷响，小朋友觉得有点害怕。",
        "disgusted": "闻到了垃圾桶里散发出的怪味，小朋友觉得很难受。",
        "surprised": "一推开门，发现大家准备了生日惊喜，小朋友感到好惊讶！",
        "neutral": "小朋友安静地坐在桌子前，正在认真地画画。"
    }
    story_text = mock_stories.get(target_emotion, "遇到了一件意想不到的事情，小朋友展现出了特别的情绪。")
    return {"status": "success", "data": {"target_emotion": target_emotion, "story_content": story_text, "difficulty": "easy"}}

# 🔒 必须带 Token
@app.get("/api/children/{child_id}/statistics", tags=["与前端对齐的接口"])
def get_child_statistics(child_id: int, db: DBSession = Depends(get_db), current_user_id: str = Depends(check_token)):
    reports = db.query(models.TrainingReport).filter(models.TrainingReport.child_id == child_id).all()
    if not reports: return {"code": 200, "message": "暂无数据", "data": None}
    
    report_ids = [r.id for r in reports]
    details = db.query(models.TrainingReportDetail).filter(models.TrainingReportDetail.report_id.in_(report_ids)).all()
    
    emotion_stats = {em: {"correct": 0, "total": 0} for em in ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]}
    for d in details:
        if d.emotion_type in emotion_stats:
            emotion_stats[d.emotion_type]["correct"] += d.correct_answers
            emotion_stats[d.emotion_type]["total"] += d.total_prompts
            
    radar_data = {}
    for em, stats in emotion_stats.items():
        if stats["total"] > 0:
            radar_data[em] = round(stats["correct"] / stats["total"], 2)
        else:
            radar_data[em] = 0.0

    highest_score = max([r.overall_accuracy for r in reports]) if reports else 0

    return {
        "code": 200, 
        "message": "数据统计成功！", 
        "data": {
            "overview": {
                "total_sessions": len(reports),
                "highest_accuracy": highest_score
            },
            "radar_chart_data": radar_data
        }
    }