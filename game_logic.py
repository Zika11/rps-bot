import json, logging
from datetime import datetime, date
from config import *
import db

def get_result(p1, p2):
    return "draw" if p1 == p2 else ("win" if WIN_MAP[p1] == p2 else "loss")

async def check_and_complete_task(user_id, task_id, bot_context, progress_increment=1):
    u = db.get_user(user_id)
    if not u: return False
    today = str(date.today())
    progress_data = u.get("tasks_progress")
    progress = {}
    if progress_data:
        try:
            progress = json.loads(progress_data)
        except:
            pass
    if progress.get("date") != today:
        progress = {"date": today, "tasks": {}}
    tasks = progress.setdefault("tasks", {})
    current = tasks.get(task_id, 0) + progress_increment
    tasks[task_id] = current

    all_tasks = db.get_tasks()
    task_def = next((t for t in all_tasks if t["task_id"] == task_id), None)
    rewarded = False
    if task_def:
        required = {"task_1":5,"task_2":3,"task_3":1,"task_4":1,"task_5":10}.get(task_id,1)
        if current >= required and not tasks.get(f"{task_id}_done"):
            pts = int(task_def["points_reward"])
            db.update_user(user_id, points=int(u.get("points",0)) + pts)
            tasks[f"{task_id}_done"] = True
            try:
                await bot_context.bot.send_message(user_id, f"🎉 أكملت مهمة {task_def['description']} وحصلت على {pts} نقطة!")
            except: pass
            rewarded = True
    db.update_user(user_id, tasks_progress=json.dumps(progress))
    return rewarded

def add_clan_points(user_id, amount):
    u = db.get_user(user_id)
    if not u or not u.get("clan"): return
    clan = db.get_clan(u["clan"])
    if not clan: return
    current = int(clan.get("points",0)) + amount
    db.update_clan(u["clan"], points=current)
    war = db.get_active_clan_war()
    if war:
        db.add_clan_war_points(u["clan"], amount)

async def check_achievements(user_id, context):
    u = db.get_user(user_id)
    if not u: return
    all_ach = db.get_achievements()
    earned = [a for a in (u.get("achievements") or "").split(",") if a]
    for ach in all_ach:
        if ach["ach_id"] in earned: continue
        field = ach["condition_field"]
        needed = ach["condition_value"]
        current = 0
        if field == "wins": current = int(u.get("wins",0))
        elif field == "losses": current = int(u.get("losses",0))
        elif field == "draws": current = int(u.get("draws",0))
        elif field == "points": current = int(u.get("points",0))
        elif field == "streak": current = int(u.get("streak_count",0))
        elif field == "win_streak": current = int(u.get("win_streak",0))
        elif field == "solo_games": current = int(u.get("solo_games",0))
        elif field == "random_games": current = int(u.get("random_games",0))
        elif field == "friend_games": current = int(u.get("friend_games",0))
        elif field == "channel_games": current = int(u.get("channel_games",0))
        elif field == "tournament_win": current = int(u.get("tournament_wins",0))
        elif field == "clan_joined": current = 1 if u.get("clan") else 0
        elif field == "rated":
            if db.get_user_rating(user_id): current = 1
        elif field == "rock_used": current = int(u.get("rock_used",0))
        elif field == "login_streak": current = int(u.get("login_streak",0))
        if current >= needed:
            if db.add_achievement(user_id, ach["ach_id"]):
                try:
                    await context.bot.send_message(user_id, f"🎖 إنجاز جديد: {ach['icon']} {ach['name']} - {ach['description']}")
                except: pass
