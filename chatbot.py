from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
import openai

# MySQL 연결 설정
db = mysql.connector.connect(
    host="192.168.0.31",
    user="root",
    password="dugudrn12!",
    database="wahoman",
    port=3306
)

app = FastAPI()

# OpenAI API 설정
openai.api_key = ""

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/chat/")
async def chat(request: ChatRequest):
    cursor = db.cursor(dictionary=True)
    
    # 이전 대화 맥락 가져오기
    cursor.execute("SELECT context FROM conversations WHERE user_id = %s", (request.user_id,))
    record = cursor.fetchone()
    context = record['context'] if record else ""
    
    # OpenAI를 이용한 대화 생성
    prompt = f"{context}\nUser: {request.message}\nAI:"
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",  # 사용 모델명 업데이트
      messages=[
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user", "content": request.message}
      ]
    )
    message_response = response.choices[0].message['content'] if response.choices else "죄송합니다, 대답을 찾을 수 없습니다."
    
    # 새 대화 맥락 저장
    new_context = context + "\nUser: " + request.message + "\nAI: " + message_response
    if record:
        cursor.execute("UPDATE conversations SET context = %s WHERE user_id = %s", (new_context, request.user_id))
    else:
        cursor.execute("INSERT INTO conversations (user_id, context) VALUES (%s, %s)", (request.user_id, new_context))
    
    db.commit()
    cursor.close()
    
    return {"response": message_response}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8401)
