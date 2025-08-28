from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List
from pathlib import Path

from src.agent import run_agent

app = FastAPI(title="SmartAgent", version="1.0")

# In-memory session store (simple demo)
SESSIONS: Dict[str, List[Dict]] = {}

class ChatIn(BaseModel):
    message: str
    session_id: str = "default"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(body: ChatIn):
    history = SESSIONS.get(body.session_id, [])
    result = run_agent(body.message, history)
    SESSIONS[body.session_id] = result["history"]
    return JSONResponse({"reply": result["reply"], "history": result["history"]})

@app.get("/", response_class=HTMLResponse)
def home():
    html_path = Path(__file__).resolve().parent.parent / "public" / "index.html"
    return HTMLResponse(html_path.read_text())
