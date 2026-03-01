import os
import uuid
import logging
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from chatbot import get_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")

sessions = defaultdict(list)
ready_flag = False

@asynccontextmanager
async def lifespan(app):
    global ready_flag
    logger.info("Starting Retail Chatbot server")
    ready_flag = True
    yield
    logger.info("Shutting down")

app = FastAPI(title="GKE Retail Chatbot", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(BASE_DIR, "templates", "chat.html")
    with open(html_path, "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())
    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)
    history = sessions[session_id]
    reply = await get_response(message, history)
    history.append({"role": "user", "content": message})
    history.append({"role": "model", "content": reply})
    if len(history) > 20:
        sessions[session_id] = history[-20:]
    return JSONResponse({"reply": reply, "session_id": session_id})

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gke-retail-chatbot"}

@app.get("/ready")
async def ready():
    if not ready_flag:
        return JSONResponse({"status": "not ready"}, status_code=503)
    return {"status": "ready"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, access_log=False)
