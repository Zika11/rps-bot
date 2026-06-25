import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards

logger = logging.getLogger(__name__)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اضغط للعب:", reply_markup=keyboards.mini_app_button())

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    base_url = "https://rps-bot-six.vercel.app"
    web_link = f"{base_url}/?chat={chat_id}"
    await update.message.reply_text(f"🔗 رابط اللعبة على الويب:\n{web_link}")
