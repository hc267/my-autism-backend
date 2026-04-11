from database import engine, Base
import models # 把咱们刚刚画好的新图纸拿过来

print("🚨 施工队已进入金库，正在拆除旧柜子...")
# 这行代码会把数据库里现有的表全部清空（开发初期必备，上线后千万别乱用哦！）
Base.metadata.drop_all(bind=engine)

print("🏗️ 正在根据最新的 models.py 重新打造带新字段的柜子...")
# 这行代码会严格按照你写的新字段，重新建表
Base.metadata.create_all(bind=engine)

print("✅ 恭喜！金库翻新成功！所有新字段已生效！")