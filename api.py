import sqlite3, json, logging, hashlib, hmac
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import engine.game_engine as game_engine
import config

app = FastAPI(title="RPS Channel Game API")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

class VoteRequest(BaseModel):
    chat_id: int
    user_id: int
    move: str

class PredictionRequest(BaseModel):
    chat_id: int
    user_id: int
    predicted_move: str

@app.get("/")
def root():
    return {"status": "RPS Game API is running"}

@app.get("/round/{chat_id}")
def get_round_status(chat_id: int):
    status = game_engine.get_round_status(chat_id)
    if not status:
        return {"status": "no active round", "chat_id": chat_id}
    return status

@app.post("/vote")
async def submit_vote(data: VoteRequest):
    success = await game_engine.vote(data.chat_id, data.user_id, data.move)
    if not success:
        raise HTTPException(status_code=400, detail="الجولة غير نشطة أو انتهت")
    return {"status": "vote registered"}

@app.post("/predict")
async def submit_prediction(data: PredictionRequest):
    success = await game_engine.predict(data.chat_id, data.user_id, data.predicted_move)
    if not success:
        raise HTTPException(status_code=400, detail="غير متاح")
    return {"status": "prediction registered"}

@app.post("/finish_round/{chat_id}")
async def finish_round(chat_id: int):
    result = await game_engine.finish_round(chat_id)
    if result is None:
        raise HTTPException(status_code=404, detail="الجولة غير موجودة")
    return result

@app.get("/leaderboard/{chat_id}")
def leaderboard(chat_id: int, limit: int = 10):
    conn = sqlite3.connect("rps_bot.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.first_name, c.points 
        FROM channel_user_points c JOIN users u ON c.user_id = u.user_id
        WHERE c.chat_id = ? ORDER BY c.points DESC LIMIT ?
    """, (chat_id, limit)).fetchall()
    conn.close()
    return [{"name": r["first_name"], "points": r["points"]} for r in rows]

@app.post("/auth/telegram")
async def verify_telegram(data: dict):
    check_hash = data.pop("hash", None)
    if not check_hash:
        return {"valid": False}

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(config.BOT_TOKEN.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if hmac_hash == check_hash:
        return {"valid": True}
    return {"valid": False}
