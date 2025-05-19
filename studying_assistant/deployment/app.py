from studying_assistant.building.build_agent import build_agent
from hydra import initialize, compose
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import uuid

client = MongoClient("mongodb://localhost:27017/")
db = client["study_agent"]
sessions_collection = db["sessions"]
messages_collection = db["messages"]


app = FastAPI()
app.mount("/static", StaticFiles(directory="studying_assistant/deployment/frontend/static"), name="static")
templates = Jinja2Templates(directory="studying_assistant/deployment/frontend/templates")

class Question(BaseModel):
    input: str
    session_id: str = None

@app.get("/styles.css")
async def get_css():
    return FileResponse("studying_assistant/deployment/frontend/static/css/style.css")

# Load the agent once at startup
@app.on_event("startup")
def load_agent():
    global agent
    config_path = Path(__file__).resolve().parent.parent.parent / "configs"
    with initialize(version_base=None, config_path="../../configs"):
        cfg = compose(config_name="config")
        agent = build_agent(cfg)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    sessions = list(sessions_collection.find({}, {"_id": 0}).sort("time_created", -1))
    return templates.TemplateResponse("index.html", {"request": request, "sessions": sessions})

@app.get("/sessions")
def list_sessions():
    sessions = list(sessions_collection.find({}, {"_id": 0}).sort("time_created", -1))  # -1 for descending
    return sessions

@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: str):
    return list(messages_collection.find({"session_id": session_id}, {"_id": 0}))

@app.post("/sessions/new")
def create_new_session():
    session_id = str(uuid.uuid4())
    sessions_collection.insert_one({
        "session_id": session_id,
        "time_created": datetime.utcnow()
    })
    return {"session_id": session_id}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    try:
        sessions_collection.delete_one({"session_id": session_id})
        messages_collection.delete_many({"session_id": session_id})
        
        return {"status": "success", "message": "Session deleted successfully"}
    except Exception as e:
        print("Error deleting session:", e)
        return {"status": "error", "message": "Failed to delete session"}

@app.post("/chat")
def chat(q: Question):
    try:
        session_id = q.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            sessions_collection.insert_one({
                "session_id": session_id,
                "time_created": datetime.utcnow()
            })

        # Get last 5 messages from chat history
        chat_history = list(messages_collection.find(
            {"session_id": session_id},
            {"_id": 0, "user_message": 1, "agent_message": 1}
        ).sort("timestamp", -1).limit(5))  # Get 5 most recent messages

        # Reverse to maintain chronological order
        chat_history.reverse()

        # Format the chat history for the prompt
        history_prompt = ""
        for message in chat_history:
            history_prompt += f"User: {message['user_message']}\n"
            history_prompt += f"Assistant: {message['agent_message']}\n"

        # Create the full prompt with history
        full_prompt = f"""Here's our recent conversation:
                        {history_prompt}
                        Now respond to this:
                        User: {q.input}
                        Assistant: """

        response = agent.invoke({"input": full_prompt})
        agent_message = response.get("output", "I'm not sure how to respond to that.")

        messages_collection.insert_one({
            "session_id": session_id,
            "user_message": q.input,
            "agent_message": agent_message,
            "timestamp": datetime.utcnow()
        })

        return {"response": agent_message, "session_id": session_id}

    except Exception as e:
        print("Agent error:", e)
        return {"response": "I'm not sure how to respond to that."}
