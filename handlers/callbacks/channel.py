import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards
import db
import handlers.channel_handlers as channel_h
import state as channel_state
import engine.game_engine as game_engine

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار القناة والتصويت والتوقعات"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data.startswith("channel_play_"):
        await channel_h.channel_play(update, context)
    
    elif data.startswith("weekly_leaderboard_"):
        await channel_h.weekly_leaderboard(update, context)
    
    elif data.startswith("ch_leaderboard_"):
        chat_id = int(data.split("_")[-1])
        top = db.get_channel_leaderboard(chat_id, 10)
        text = "🏆 **أفضل 10 لاعبين في القناة:**\n"
        for i, r in enumerate(top, 1):
            text += f"{i}. {r['first_name']} - {r['points']} نقطة\n"
        await query.edit_message_text(text)

    # التوقعات
    elif data.startswith("predict_"):
        parts = data.split("_")
        chat_id = int(parts[1])
        predicted_move = parts[2]
        if predicted_move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        if await channel_state.is_spam_vote(chat_id, user.id):
            await query.answer("تم استلام توقعك بالفعل!")
            return
        success = await game_engine.predict(chat_id, user.id, predicted_move)
        if success:
            await query.answer("تم تسجيل توقعك! 🔮")
        else:
            await query.answer("التوقع غير متاح الآن.")
    
    else:
        logger.warning(f"زر قناة غير معروف: {data}")
