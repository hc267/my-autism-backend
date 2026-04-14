from database import engine, Base
import models 
from sqlalchemy import text

print("🚨 施工队遇到顽固钢筋，正在申请使用 C4 炸药 (CASCADE 级联爆破)...")

# 1. 终极爆破：不一个一个拆表了，直接把整个数据库的 public 空间炸掉并重建
with engine.begin() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))

print("🏗️ 爆破完毕！正在根据最新的 models.py 重新打造柜子...")

# 2. 重新按照图纸建表
Base.metadata.create_all(bind=engine)

print("✅ 恭喜！金库翻新成功！所有新字段已生效！")