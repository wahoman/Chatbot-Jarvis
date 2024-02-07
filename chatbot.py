from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
import openai
import requests
from dotenv import load_dotenv  # 추가
import os  # 추가
import uvicorn

# .env 파일에서 환경 변수 로드
load_dotenv()

# MySQL 및 OpenAI API 설정
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv('DB_PORT', 3306))
)

##
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: str
    message: str

def create_chat_completion(prompt):
    url = "https://api.openai.com/v1/chat/completions"  # OpenAI 챗 API URL
    headers = {
        "Authorization": f"Bearer {openai.api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "gpt-4-1106-preview",  # 사용할 모델 지정
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

@app.post("/chat/")
async def chat(request: ChatRequest):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT user_message, bot_response FROM conversations WHERE user_id = %s ORDER BY id", (request.user_id,))
    records = cursor.fetchall()

    # 전체 대화 맥락 구축
    context = "\n".join([f"User: {record['user_message']}\nAI: {record['bot_response']}" for record in records])

    # 대화 스타일 명시 및 프롬프트 생성
    prompt_style = "챗봇은 친절하고 자연스러운 대화를 지향합니다."
    prompt = f"{context}\n{prompt_style}\nUser: {request.message}\nAI:"

    # OpenAI 챗 API를 이용한 대화 생성
    response = create_chat_completion(prompt)
    message_response = response.get("choices", [{}])[0].get("message", {}).get('content') if response.get("choices") else None

    if message_response:
        cursor.execute("INSERT INTO conversations (user_id, user_message, bot_response) VALUES (%s, %s, %s)", (request.user_id, request.message, message_response))
        db.commit()

    cursor.close()
    return {"response": message_response or "죄송합니다, 대답을 찾을 수 없습니다."}


host = os.getenv('HOST', '127.0.0.1')  # 기본값을 제공할 수 있습니다.
port = int(os.getenv('PORT', 8000))    # 기본값을 제공할 수 있습니다.

# FastAPI 앱 정의 및 기타 설정 ...

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)