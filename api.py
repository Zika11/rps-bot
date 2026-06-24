import sqlite3, json, logging, hashlib, hmac
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from engine import voting, rewards, state
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
    loop = voting.get_channel_loop(chat_id)
    if not loop:
        return {"status": "no active round", "chat_id": chat_id}
    return {
        "chat_id": chat_id,
        "round_id": loop["round_id"],
        "players_count": len(json.loads(loop["players_choice"] or "{}")),
        "interval_sec": loop["interval_sec"],
        "ttl_sec": loop["ttl_sec"]
    }

@app.post("/vote")
def submit_vote(data: VoteRequest):
    success = voting.record_channel_vote(data.chat_id, data.user_id, data.move)
    if not success:
        raise HTTPException(status_code=400, detail="الجولة غير نشطة أو انتهت")
    return {"status": "vote registered"}

@app.post("/predict")
def submit_prediction(data: PredictionRequest):
    success = voting.record_prediction(data.chat_id, data.user_id, data.predicted_move)
    if not success:
        raise HTTPException(status_code=400, detail="غير متاح")
    return {"status": "prediction registered"}

@app.post("/finish_round/{chat_id}")
def finish_round(chat_id: int):
    result = voting.finish_channel_round(chat_id)
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

# 🆕 نقطة نهاية للتحقق من بيانات تسجيل الدخول عبر Telegram
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
