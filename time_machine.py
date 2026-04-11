import random
from datetime import datetime, timedelta, timezone
import models
import database
from passlib.context import CryptContext

# 确保数据库表都已经建好
models.Base.metadata.create_all(bind=database.engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run_time_machine():
    db = database.SessionLocal()
    try:
        print("\n⏳ 时光机启动！正在穿越回过去 30 天...\n")

        # 1. 保安检查：确保有 1 号家长和 1 号孩子 (防弹设计)
        user = db.query(models.User).filter(models.User.id == 1).first()
        if not user:
            user = models.User(email="test@test.com", hashed_password=pwd_context.hash("123"), role="parent")
            db.add(user); db.commit(); db.refresh(user)
            print("👨‍👩‍👦 自动创建了默认测试家长 (ID: 1)")

        child = db.query(models.Child).filter(models.Child.id == 1).first()
        if not child:
            child = models.Child(name="测试宝宝", age=5, notes="时光机自动生成的宝宝")
            db.add(child); db.commit(); db.refresh(child)
            binding = models.Binding(user_id=user.id, child_id=child.id)
            db.add(binding); db.commit()
            print("👶 自动创建了默认测试宝宝 (ID: 1)")

        # 2. 核心魔法：生成过去 30 天的 30 条模拟数据
        now = datetime.now(timezone.utc)
        inserted_count = 0
        
        for i in range(30):
            # 随机穿越到过去 1-30 天里的某一天
            days_ago = random.randint(1, 30)
            simulated_time = now - timedelta(days=days_ago)
            time_str = simulated_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            # 随机生成极其逼真的情绪分布 (让数据看起来有起伏)
            base_happy = random.uniform(0.4, 0.8) # 快乐占主导
            remain = 1.0 - base_happy
            
            dist = {
                "happy": round(base_happy, 2),
                "sad": round(remain * 0.2, 2),
                "angry": round(remain * 0.1, 2),
                "fearful": round(remain * 0.1, 2),
                "disgusted": round(remain * 0.1, 2),
                "surprised": round(remain * 0.3, 2),
                "neutral": round(remain * 0.2, 2)
            }

            # 拼装逼真的 JSONB 账单
            stats_data = {
                "userId": "u001",
                "childId": "c001",
                "sessionId": f"mock_session_{random.randint(1000, 9999)}",
                "levelId": random.randint(1, 5), # 随机 1-5 关
                "targetEmotion": random.choice(["happy", "surprised", "neutral"]),
                "recognizedEmotion": random.choice(["happy", "sad", "neutral"]),
                "success": random.choice([True, True, True, False]), # 75% 胜率
                "score": random.randint(50, 100),
                "durationMs": random.randint(10000, 60000),
                "attemptCount": random.randint(1, 3),
                "stableVoteFrames": 6,
                "threshold": 0.3,
                "dominantConfidenceAvg": round(random.uniform(0.5, 0.95), 2),
                "emotionDistribution": dist,
                "deviceInfo": {"platform": "ios", "browser": "safari"},
                "startedAt": time_str,
                "endedAt": time_str
            }

            # 存入 PostgreSQL
            new_session = models.Session(
                child_id=1,
                level=stats_data["levelId"],
                duration_seconds=stats_data["durationMs"] // 1000,
                score=stats_data["score"],
                emotion_stats=stats_data
            )
            db.add(new_session)
            inserted_count += 1
        
        # 关上金库门
        db.commit()
        print(f"🎉 轰！时光机运行完毕！")
        print(f"✨ 成功为 1 号宝宝注入了 {inserted_count} 条跨越 30 天的精美历史训练记录！")
        
    except Exception as e:
        print(f"❌ 时光机发生故障: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_time_machine()