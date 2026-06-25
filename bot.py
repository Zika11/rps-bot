import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔥 الاستيراد الصح (لأن الملف جوه handlers)
from handlers.game_handlers import handle_move, handle_mode_selection

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# التوكن من Railway Variables
TOKEN = os.getenv("BOT_TOKEN")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Welcome to RPS Bot!\nChoose a mode 👇")

# Main function
def main():
    print("🚀 بدء تشغيل API...")
    print("🤖 بدء تشغيل البوت...")

    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN مش متضاف في Railway")

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # Buttons (Modes)
    app.add_handler(CallbackQueryHandler(handle_mode_selection, pattern="^mode_"))

    # Buttons (Moves)
    app.add_handler(CallbackQueryHandler(handle_move, pattern="^(rock|paper|scissors)$"))

    # تشغيل البوت
    app.run_polling()

if __name__ == "__main__":
    main()
