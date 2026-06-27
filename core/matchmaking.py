import asyncio
import logging
import json
from datetime import datetime, timedelta
import db
import state

logger = logging.getLogger(__name__)

class MatchmakingManager:
    """نظام المطابقة المتقدم – قائمة انتظار، إلغاء تلقائي، إعادة محاولة"""
    
    def __init__(self):
        self.queues = {}  # chat_id -> قائمة انتظار اللاعبين
        self.matches = {}  # match_id -> بيانات المباراة
        self.timeout = 30  # ثانية قبل إلغاء المباراة
        self.max_players = 2  # عدد اللاعبين في المباراة
        
    async def join_queue(self, user_id: int, chat_id: int, game_type: str = "random"):
        """انضمام لاعب إلى قائمة الانتظار"""
        async with state.group_session_lock:
            if chat_id not in self.queues:
                self.queues[chat_id] = []
            
            queue = self.queues[chat_id]
            # التحقق من أن اللاعب ليس في القائمة بالفعل
            if user_id in queue:
                return None
            
            # إضافة اللاعب
            queue.append({
                "user_id": user_id,
                "joined_at": datetime.now().isoformat(),
                "game_type": game_type
            })
            
            # محاولة المطابقة
            match = await self._try_match(chat_id)
            if match:
                return match
            return {"status": "waiting", "position": len(queue)}
    
    async def _try_match(self, chat_id: int):
        """محاولة مطابقة لاعبين"""
        queue = self.queues.get(chat_id, [])
        if len(queue) < 2:
            return None
        
        # إزالة اللاعبين الذين انتهت مدة انتظارهم
        now = datetime.now()
        expired = []
        for i, player in enumerate(queue):
            joined = datetime.fromisoformat(player["joined_at"])
            if (now - joined).total_seconds() > self.timeout * 2:
                expired.append(i)
        
        for i in reversed(expired):
            del queue[i]
        
        if len(queue) < 2:
            return None
        
        # أخذ أول لاعبين
        player1 = queue.pop(0)
        player2 = queue.pop(0)
        
        # إنشاء مباراة
        match_id = f"match_{chat_id}_{player1['user_id']}_{player2['user_id']}_{int(datetime.now().timestamp())}"
        
        # حفظ في قاعدة البيانات
        state.start_solo_game(player1['user_id'])  # إنشاء game في state
        
        match_data = {
            "match_id": match_id,
            "chat_id": chat_id,
            "player1": player1['user_id'],
            "player2": player2['user_id'],
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "game_type": player1['game_type'],
            "moves": {}
        }
        
        self.matches[match_id] = match_data
        return match_data
    
    async def submit_move(self, match_id: str, user_id: int, move: str):
        """تسجيل حركة لاعب في المباراة"""
        match = self.matches.get(match_id)
        if not match:
            return {"error": "المباراة غير موجودة"}
        
        if match["status"] != "active":
            return {"error": "المباراة انتهت"}
        
        if user_id not in [match["player1"], match["player2"]]:
            return {"error": "أنت لست في هذه المباراة"}
        
        # تسجيل الحركة
        match["moves"][str(user_id)] = move
        
        # التحقق من اكتمال الحركات
        if str(match["player1"]) in match["moves"] and str(match["player2"]) in match["moves"]:
            # حساب النتيجة
            from core.game_engine import get_result
            m1 = match["moves"][str(match["player1"])]
            m2 = match["moves"][str(match["player2"])]
            result = get_result(m1, m2)
            
            # تحديث النتيجة
            if result == "win":
                winner = match["player1"]
            elif result == "loss":
                winner = match["player2"]
            else:
                winner = None
            
            match["status"] = "finished"
            match["result"] = result
            match["winner"] = winner
            
            return {
                "status": "finished",
                "result": result,
                "winner": winner,
                "player1_move": m1,
                "player2_move": m2
            }
        
        return {"status": "waiting", "message": "بانتظار حركة الخصم"}
    
    async def cancel_match(self, match_id: str, user_id: int):
        """إلغاء مباراة من قبل لاعب"""
        match = self.matches.get(match_id)
        if not match:
            return {"error": "المباراة غير موجودة"}
        
        if user_id not in [match["player1"], match["player2"]]:
            return {"error": "أنت لست في هذه المباراة"}
        
        match["status"] = "cancelled"
        # إرجاع اللاعبين إلى قائمة الانتظار
        chat_id = match["chat_id"]
        async with state.group_session_lock:
            if chat_id not in self.queues:
                self.queues[chat_id] = []
            # إضافة اللاعبين مرة أخرى
            self.queues[chat_id].append({
                "user_id": match["player1"],
                "joined_at": datetime.now().isoformat(),
                "game_type": match["game_type"]
            })
            self.queues[chat_id].append({
                "user_id": match["player2"],
                "joined_at": datetime.now().isoformat(),
                "game_type": match["game_type"]
            })
        
        return {"status": "cancelled"}
    
    async def get_queue_status(self, chat_id: int):
        """الحصول على حالة قائمة الانتظار"""
        queue = self.queues.get(chat_id, [])
        return {
            "chat_id": chat_id,
            "players": [p["user_id"] for p in queue],
            "count": len(queue),
            "max_players": self.max_players
        }
    
    async def get_active_matches(self, chat_id: int = None):
        """الحصول على المباريات النشطة"""
        if chat_id:
            return [m for m in self.matches.values() if m["chat_id"] == chat_id and m["status"] == "active"]
        return [m for m in self.matches.values() if m["status"] == "active"]
    
    async def cleanup_expired(self):
        """تنظيف المباريات المنتهية وقوائم الانتظار القديمة"""
        now = datetime.now()
        
        # تنظيف المباريات المعلقة
        expired_matches = []
        for mid, match in self.matches.items():
            if match["status"] == "active":
                created = datetime.fromisoformat(match["created_at"])
                if (now - created).total_seconds() > self.timeout * 2:
                    expired_matches.append(mid)
        
        for mid in expired_matches:
            del self.matches[mid]
        
        # تنظيف قوائم الانتظار القديمة
        for chat_id, queue in self.queues.items():
            expired = []
            for i, player in enumerate(queue):
                joined = datetime.fromisoformat(player["joined_at"])
                if (now - joined).total_seconds() > self.timeout * 3:
                    expired.append(i)
            for i in reversed(expired):
                del queue[i]
            if not queue:
                del self.queues[chat_id]

# مثيل واحد للاستخدام
matchmaking = MatchmakingManager()

# مهمة خلفية للتنظيف
async def run_matchmaking_cleanup():
    while True:
        await asyncio.sleep(60)  # كل دقيقة
        await matchmaking.cleanup_expired()
