from studying_assistant.building.build_agent import build_agent
from hydra import initialize, compose
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.mount("/static", StaticFiles(directory="studying_assistant/deployment/frontend/static"), name="static")
templates = Jinja2Templates(directory="studying_assistant/deployment/frontend/templates")

class Question(BaseModel):
    input: str

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
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
def chat(q: Question):
    response = agent.invoke({"input": q.input})
    print(response)
    return {"response": response['output']}
