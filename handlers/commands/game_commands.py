import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards
from core.matchmaking import matchmaking  # ✅ استيراد المثيل

logger = logging.getLogger(__name__)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /game - فتح قائمة اللعب"""
    await update.message.reply_text("اختر نمط اللعب:", reply_markup=keyboards.game_mode_menu())

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /web - رابط اللعبة على الويب"""
    chat_id = update.effective_chat.id
    base_url = "https://rps-bot-six.vercel.app"
    web_link = f"{base_url}/?chat={chat_id}"
    await update.message.reply_text(f"🔗 رابط اللعبة على الويب:\n{web_link}")

async def matchmaking_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /matchmaking - عرض حالة قائمة الانتظار"""
    count = matchmaking.get_pending_count()
    users = matchmaking.get_pending_users()
    text = f"👥 قائمة الانتظار: {count} لاعب\n"
    if users:
        text += "\n".join([f"- {uid}" for uid in users[:10]])
        if len(users) > 10:
            text += f"\n... و {len(users) - 10} آخرين"
    await update.message.reply_text(text)
