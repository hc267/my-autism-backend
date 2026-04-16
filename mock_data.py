import requests
import random
import time

# 你的线上服务器地址
BASE_URL = "https://autism-api-test.onrender.com/api/sessions/upload"

# 你的专属通行证 (Token) —— 请确保这是你刚才登录拿到的最新 Token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6InBhcmVudCIsImV4cCI6MTc3NjkyNDYwOX0.a_70xL80GulDSDX1H8lRs-9YqSCt2ZqVoUy9o8knWIw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

emotions = ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]

print("🚀 时光机启动，开始向云端注入测试数据...")

# 循环生成 30 条历史记录
for i in range(1, 31):
    details = []
    total_correct = 0
    total_prompts_all = 0
    
    for emotion in emotions:
        prompts = random.randint(2, 10) 
        correct = random.randint(0, prompts) 
        
        total_prompts_all += prompts
        total_correct += correct
        
        details.append({
            "emotion_type": emotion,
            "total_prompts": prompts,
            "correct_answers": correct
        })
    
    if total_prompts_all > 0:
        overall_accuracy = round(total_correct / total_prompts_all, 2)
    else:
        overall_accuracy = 0.0
    
    # ==========================================
    # 👇 这里就是修改 ID 的地方！ 👇
    # ==========================================
    payload = {
        "child_id": 4,  # ✅ 1. 改成 4 (因为你现在的宝宝 ID 是 4)
        "unit_id": random.randint(1, 2),  # ✅ 2. 必须改！改成 (1, 2)，因为我们只初始化了 1和2 关
        "duration_seconds": random.randint(60, 300), 
        "overall_accuracy": overall_accuracy,
        "details": details
    }
    # ==========================================
    
    response = requests.post(BASE_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ 第 {i} 条记录注入成功！(准确率: {overall_accuracy})")
    else:
        # 如果还是报错，这里会打印出具体的错误原因
        print(f"❌ 第 {i} 条记录失败: {response.status_code} - {response.text}")
        
    time.sleep(0.5)

print("🎉 注入完成！快去统计接口看看丰满的图表数据吧！")