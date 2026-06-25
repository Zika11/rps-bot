import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔥 الحل هنا (غيرنا الاستيراد)
try:
    from game_handlers import handle_move, handle_mode_selection
except:
    from handlers.game_handlers import handle_move, handle_mode_selection

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Welcome to RPS Bot!")

def main():
    print("🚀 بدء تشغيل API...")
    print("🤖 بدء تشغيل البوت...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_mode_selection, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(handle_move, pattern="^(rock|paper|scissors)$"))

    app.run_polling()

if __name__ == "__main__":
    main()
