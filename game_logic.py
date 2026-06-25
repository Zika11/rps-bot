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
            progress = {}
    # Initialize nested dicts if absent
    if "tasks" not in progress: progress["tasks"] = {}
    if "repeatable" not in progress: progress["repeatable"] = {}
    curr_progress = progress["tasks"].get(str(task_id), 0)
    needed = None

    task = db.get_task(task_id)
    if task["is_repeatable"]:
        progress["tasks"][str(task_id)] = curr_progress + progress_increment
        if task["points_reward"]:
            if not progress["tasks"].get(f"{task_id}_done", False):
                # Check first completion
                if progress["tasks"][str(task_id)] >= task["target"]:
                    progress["tasks"][f"{task_id}_done"] = True
                    db.add_points(user_id, task["points_reward"])
                    await bot_context.bot.send_message(user_id, f"🎉 أكملت المهمة: {task['description']} (+{task['points_reward']} نقاط)")
        else:
            # Task with no point reward
            if not progress["tasks"].get(f"{task_id}_done", False):
                if progress["tasks"][str(task_id)] >= task["target"]:
                    progress["tasks"][f"{task_id}_done"] = True
                    await bot_context.bot.send_message(user_id, f"🎉 أكملت المهمة: {task['description']}")
    else:
        if not progress["tasks"].get(f"{task_id}_done", False):
            progress["tasks"][str(task_id)] = curr_progress + progress_increment
            if progress["tasks"][str(task_id)] >= task["target"]:
                progress["tasks"][f"{task_id}_done"] = True
                db.add_points(user_id, task["points_reward"])
                await bot_context.bot.send_message(user_id, f"🎉 أكملت المهمة: {task['description']} (+{task['points_reward']} نقاط)")

    db.update_user(user_id, {"tasks_progress": json.dumps(progress)})
    return True

async def check_achievements(user_id, context):
    u = db.get_user(user_id)
    if not u: return
    all_ach = db.get_achievements()
    earned = [a for a in (u.get("achievements", '') or '').split(',') if a]
    progress_json = u.get("tasks_progress")
    progress = {}
    if progress_json:
        try:
            progress = json.loads(progress_json)
        except:
            progress = {}
    points = int(u.get("points", 0))

    for ach in all_ach:
        if ach["ach_id"] in earned: continue
        cond = ach.get("condition")
        if not cond: continue
        field = cond.get("field")
        needed = cond.get("target", 0)
        current = 0
        if field == "total_points":
            current = points
        elif field == "win_games":
            current = int(u.get("wins", 0))
        elif field == "games":
            current = int(u.get("games", 0))
        elif field == "tasks_completed":
            tasks_done = progress.get("tasks", {})
            current = sum(1 for k,v in tasks_done.items() if k.endswith("_done") and v)
        elif field == "first_game":
            current = 1 if int(u.get("games",0)) >= 1 else 0
        if current >= needed:
            if db.add_achievement(user_id, ach["ach_id"]):
                earned.append(ach["ach_id"])
                try:
                    await context.bot.send_message(user_id, f"🎖 *إنجاز جديد:* {ach['icon']} {ach['name']} - {ach['description']}")
                except:
                    pass

async def give_daily_points(user_id, streak, context):
    u = db.get_user(user_id)
    if not u: return
    points_today = config.DAILY_POINTS
    if streak >= 7:
        points_today *= 2
    db.add_points(user_id, points_today)
    try:
        await context.bot.send_message(user_id, f"🔔 لقد سجلت الدخول لليوم {streak} من {config.LOGIN_STREAK_RESET} أيام! +{points_today} نقاط.")
    except:
        pass

async def leaderboard(update, context, period="total"):
    pass  # Implementation omitted for brevity
