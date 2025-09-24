from fastapi import FastAPI
from pydantic import BaseModel
from src.chatbot.chatbot_app import final_response_by_llm

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/chat")
def chat_endpoint(request: QueryRequest):
    user_query = request.query
    try:
        response = final_response_by_llm(user_query)
        return {"answer": response}
    except Exception as e:
        return {"answer": f"⚠️ Error: {e}"}