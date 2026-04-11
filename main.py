from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone, date

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

# 👇 终极升级版：儿童档案模具
class ChildCreate(BaseModel):
    name: str
    birth_date: date  # 使用出生日期计算年龄更专业
    parent_id: int
    avatar_url: Optional[str] = None     
    real_name: Optional[str] = None      
    gender: Optional[str] = None         
    notes: Optional[str] = None

# 👇 终极升级版：七大情绪得分明细模具
class EmotionDetail(BaseModel):
    emotion_type: str       # 必须是 happy, sad, angry 等 7 种之一
    total_prompts: int      # 出现了几次
    correct_answers: int    # 答对了几次

# 👇 终极升级版：游戏结算大礼包模具
class SessionUploadNew(BaseModel):
    child_id: int           
    unit_id: int            
    duration_seconds: int   
    overall_accuracy: float 
    details: List[EmotionDetail] # 灵魂数据：成绩明细列表

# ==========================================
# 接口区 (业务逻辑)
# ==========================================

@app.post("/api/register")
def register_user(user: UserCreate, db: DBSession = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    hashed_pwd = pwd_context.hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pwd, role=user.role)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"status": "success", "user_id": new_user.id}

@app.post("/api/login")
def login_user(user: UserLogin, db: DBSession = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    access_token = create_access_token(data={"sub": str(db_user.id), "role": db_user.role})
    return {"status": "success", "user_id": db_user.id, "role": db_user.role, "access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/{user_id}/children")
def get_parent_children(user_id: int, db: DBSession = Depends(get_db)):
    bindings = db.query(models.Binding).filter(models.Binding.user_id == user_id).all()
    if not bindings: return {"status": "success", "message": "暂无绑定儿童", "data": []}
    child_ids = [binding.child_id for binding in bindings]
    children = db.query(models.Child).filter(models.Child.id.in_(child_ids)).all()
    return {"status": "success", "data": children}

# 🌟 新增：下发关卡配置
@app.get("/api/training-units", tags=["与前端对齐的接口"])
def get_training_units(db: DBSession = Depends(get_db)):
    units = db.query(models.TrainingUnit).all()
    return {"code": 200, "message": "关卡配置获取成功", "data": units}

# 🌟 升级：创建儿童档案
@app.post("/api/children", tags=["儿童管理"])
def create_child_profile(child_data: ChildCreate, db: DBSession = Depends(get_db)):
    new_child = models.Child(
        name=child_data.name, 
        birth_date=child_data.birth_date,
        avatar_url=child_data.avatar_url,
        real_name=child_data.real_name,
        gender=child_data.gender,
        notes=child_data.notes
    )
    db.add(new_child); db.commit(); db.refresh(new_child)
    
    new_binding = models.Binding(user_id=child_data.parent_id, child_id=new_child.id)
    db.add(new_binding); db.commit()
    return {"code": 200, "message": "儿童档案创建成功！", "child_id": new_child.id}

# 🌟 升级：终极训练成绩上传 (拆表存入)
@app.post("/api/sessions/upload", tags=["与前端对齐的接口"])
def upload_session_from_frontend(session_data: SessionUploadNew, db: DBSession = Depends(get_db)):
    # 1. 存主表 (总成绩单)
    new_report = models.TrainingReport(
        child_id=session_data.child_id,
        unit_id=session_data.unit_id,
        duration_seconds=session_data.duration_seconds,
        overall_accuracy=session_data.overall_accuracy
    )
    db.add(new_report); db.commit(); db.refresh(new_report)

    # 2. 存分表 (各情绪详细得分)
    for detail in session_data.details:
        new_detail = models.TrainingReportDetail(
            report_id=new_report.id,
            emotion_type=detail.emotion_type,
            total_prompts=detail.total_prompts,
            correct_answers=detail.correct_answers
        )
        db.add(new_detail)
    db.commit()

    print(f"🔥 成绩单拆分成功！总单ID: {new_report.id}，明细 {len(session_data.details)} 条！")
    return {"code": 200, "message": "成绩单已完美拆分存入金库！", "data": {"report_id": new_report.id}}

# 🌟 升级：获取孩子的所有总成绩单
@app.get("/api/children/{child_id}/sessions")
def get_child_sessions(child_id: int, db: DBSession = Depends(get_db)):
    reports = db.query(models.TrainingReport).filter(models.TrainingReport.child_id == child_id).all()
    return {"status": "success", "data": reports}

# 🌟 升级：简单版 AI 分析
@app.get("/api/analyze/{report_id}")
def analyze_session_emotions(report_id: int, db: DBSession = Depends(get_db)):
    report = db.query(models.TrainingReport).filter(models.TrainingReport.id == report_id).first()
    if not report: raise HTTPException(status_code=404, detail="找不到这次记录")
    time.sleep(1) 
    
    accuracy = report.overall_accuracy
    if accuracy > 0.8: ai_advice = "表现非常棒，准确率极高，建议保持目前的训练难度。"
    elif accuracy > 0.5: ai_advice = "表现平稳，部分情绪容易混淆，建议多做针对性巩固。"
    else: ai_advice = "准确率偏低，可能是不在状态，建议更换轻松的主题或稍作休息。"
    
    return {"status": "success", "report_id": report_id, "ai_analysis": {"overall_accuracy": accuracy, "professional_advice": ai_advice}}

# 🌟 终极升级：家长看板雷达图数据计算
@app.get("/api/children/{child_id}/statistics", tags=["与前端对齐的接口"])
def get_child_statistics(child_id: int, db: DBSession = Depends(get_db)):
    # 1. 查出所有主单
    reports = db.query(models.TrainingReport).filter(models.TrainingReport.child_id == child_id).all()
    if not reports: return {"code": 200, "message": "暂无数据", "data": None}
    
    # 2. 查出所有明细单
    report_ids = [r.id for r in reports]
    details = db.query(models.TrainingReportDetail).filter(models.TrainingReportDetail.report_id.in_(report_ids)).all()
    
    # 3. 统计 7 大情绪的累积答对次数和出现次数
    emotion_stats = {em: {"correct": 0, "total": 0} for em in ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]}
    for d in details:
        if d.emotion_type in emotion_stats:
            emotion_stats[d.emotion_type]["correct"] += d.correct_answers
            emotion_stats[d.emotion_type]["total"] += d.total_prompts
            
    # 4. 计算最终的雷达图胜率
    radar_data = {}
    for em, stats in emotion_stats.items():
        if stats["total"] > 0:
            radar_data[em] = round(stats["correct"] / stats["total"], 2) # 如 0.85
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