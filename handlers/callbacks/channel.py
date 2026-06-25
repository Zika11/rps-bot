import logging
from telegram import Update
from telegram.ext import ContextTypes
import db, config, keyboards, state
import handlers.channel_handlers as channel_h
import engine.game_engine as game_engine

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار القناة والتصويت"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    # ===== قائمة القناة =====
    if data.startswith("channel_play_"):
        await channel_h.channel_play(update, context)
        return True

    elif data.startswith("weekly_leaderboard_"):
        await channel_h.weekly_leaderboard(update, context)
        return True

    elif data.startswith("ch_leaderboard_"):
        chat_id = int(data.split("_")[-1])
        top = db.get_channel_leaderboard(chat_id, 10)
        text = "🏆 **أفضل 10 لاعبين في القناة:**\n"
        for i, r in enumerate(top, 1):
            text += f"{i}. {r['first_name']} - {r['points']} نقطة\n"
        await query.edit_message_text(text)
        return True

    # ===== التوقعات =====
    elif data.startswith("predict_"):
        parts = data.split("_")
        chat_id = int(parts[1])
        predicted_move = parts[2]
        if predicted_move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return True
        if await state.is_spam_vote(chat_id, user.id):
            await query.answer("تم استلام توقعك بالفعل!")
            return True
        success = await game_engine.predict(chat_id, user.id, predicted_move)
        if success:
            await query.answer("تم تسجيل توقعك! 🔮")
        else:
            await query.answer("التوقع غير متاح الآن.")
        return True

    # ===== المهام والإنجازات والتصنيف =====
    elif data == "tasks":
        tasks = db.get_tasks()
        u = db.get_user(user.id)
        progress_data = u.get("tasks_progress")
        progress = {}
        if progress_data:
            try: import json; progress = json.loads(progress_data)
            except: pass
        tasks_progress = progress.get("tasks", {})
        text = "📋 المهام:\n"
        for t in tasks:
            done = tasks_progress.get(f"{t['task_id']}_done", False)
            text += f"{'✅' if done else '⭕'} {t['description']} (+{t['points_reward']} نقطة)\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
        return True

    elif data == "achievements":
        all_ach = db.get_achievements()
        u = db.get_user(user.id)
        earned = [a for a in (u.get("achievements") or "").split(",") if a]
        text = "🏅 الإنجازات:\n"
        for a in all_ach:
            icon = a["icon"] if a["ach_id"] in earned else "🔒"
            text += f"{icon} {a['name']} - {a['description']}\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
        return True

    elif data == "rating":
        top = db.get_top_ratings(10)
        text = "📊 أفضل 10 لاعبين:\n"
        for i, r in enumerate(top, 1):
            name = r["first_name"] or str(r["user_id"])
            rating_val = r["rating"]
            tier_name, tier_icon = config.get_tier_info(rating_val)
            text += f"{i}. {name} - {rating_val} ({tier_icon} {tier_name})\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
        return True

    # ===== Battle Pass =====
    elif data in ["battlepass", "battlepass_progress"]:
        from bot import battlepass_command
        await battlepass_command(update, context)
        return True

    # ===== عجلة الحظ =====
    elif data == "wheel":
        await query.edit_message_text("🎡 عجلة الحظ! تدوير بـ 5 جواهر.", reply_markup=keyboards.wheel_button())
        return True

    elif data == "wheel_spin":
        from bot import wheel_spin_handler
        await wheel_spin_handler(update, context)
        return True

    return False
