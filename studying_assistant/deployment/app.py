from studying_assistant.building.build_agent import build_agent
from hydra import initialize, compose
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import uuid

client = MongoClient("mongodb://localhost:27017/")
db = client["study_agent"]
sessions_collection = db["sessions"]
messages_collection = db["messages"]

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="studying_assistant/deployment/static"), name="static")
templates = Jinja2Templates(directory="studying_assistant/deployment/templates")

class Question(BaseModel):
    input: str

# Load the agent once at startup
@app.on_event("startup")
def load_agent():
    global agent
    try:
        config_path = Path(__file__).resolve().parent.parent.parent / "configs"
        with initialize(version_base=None, config_path="../../configs"):
            cfg = compose(config_name="config")
            agent = build_agent(cfg)
        print("Agent loaded successfully!")
    except Exception as e:
        print(f"Error loading agent: {e}")
        agent = None

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    sessions = list(sessions_collection.find({}, {"_id": 0}).sort("time_created", -1))
    for session in sessions:
        utc_time = session['time_created'].replace(tzinfo=pytz.utc)
        session['time_created'] = utc_time.astimezone(pytz.timezone('Africa/Cairo'))
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "sessions": sessions,
        "current_session_id": sessions[0]["session_id"] if sessions else None,
        "messages": []
    })

@app.get("/chat/{session_id}", response_class=HTMLResponse)
def chat_session(request: Request, session_id: str):
    # Check if session exists
    session = sessions_collection.find_one({"session_id": session_id})
    if not session:
        return RedirectResponse(url="/", status_code=302)
    
    # Get all sessions for sidebar
    sessions = list(sessions_collection.find({}, {"_id": 0}).sort("time_created", -1))
    for session in sessions:
        utc_time = session['time_created'].replace(tzinfo=pytz.utc)
        session['time_created'] = utc_time.astimezone(pytz.timezone('Africa/Cairo'))
    
    # Get messages for current session
    messages = list(messages_collection.find(
        {"session_id": session_id}, 
        {"_id": 0}
    ).sort("timestamp", 1))
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "sessions": sessions,
        "current_session_id": session_id,
        "messages": messages
    })

@app.get("/sessions")
def list_sessions():
    try:
        sessions = list(sessions_collection.find({}, {"_id": 0}).sort("time_created", -1))
        return sessions
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return []

@app.post("/sessions/new")
def create_new_session():
    try:
        session_id = str(uuid.uuid4())
        sessions_collection.insert_one({
            "session_id": session_id,
            "time_created": datetime.utcnow()
        })
        return {"session_id": session_id}
    except Exception as e:
        print(f"Error creating new session: {e}")
        return {"error": "Failed to create session"}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    try:
        sessions_collection.delete_one({"session_id": session_id})
        messages_collection.delete_many({"session_id": session_id})
        
        return {"status": "success", "message": "Session deleted successfully"}
    except Exception as e:
        print("Error deleting session:", e)
        return {"status": "error", "message": "Failed to delete session"}

@app.post("/chat/{session_id}")
def chat_with_session(session_id: str, q: Question):
    try:
        if agent is None:
            return {"response": "Agent is not loaded. Please check server logs."}
        
        # Check if session exists, if not create it
        session = sessions_collection.find_one({"session_id": session_id})
        if not session:
            sessions_collection.insert_one({
                "session_id": session_id,
                "time_created": datetime.utcnow()
            })

        # Get last 10 messages from chat history
        chat_history = list(messages_collection.find(
            {"session_id": session_id},
            {"_id": 0, "user_message": 1, "agent_message": 1}
        ).sort("timestamp", -1).limit(10))

        # Reverse to maintain chronological order
        chat_history.reverse()

        # Format the chat history for the prompt
        history_prompt = ""
        if chat_history:
            history_prompt = "Here's our recent conversation:\n"
            for message in chat_history:
                history_prompt += f"User: {message['user_message']}\n"
                history_prompt += f"Assistant: {message['agent_message']}\n"
            history_prompt += "\n"

        # Create the full prompt with history
        full_prompt = f"{history_prompt}User: {q.input}\nAssistant: "

        response = agent.invoke({"input": full_prompt})
        agent_message = response.get("output", "I'm not sure how to respond to that.")

        # Store the conversation
        messages_collection.insert_one({
            "session_id": session_id,
            "user_message": q.input,
            "agent_message": agent_message,
            "timestamp": datetime.now()
        })

        return {"response": agent_message, "session_id": session_id}

    except Exception as e:
        print("Agent error:", e)
        return {"response": "I apologize, but I encountered an error while processing your request. Please try again."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)