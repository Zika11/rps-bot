import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ✅ الاستيراد الصح حسب مشروعك
from handlers.game_handlers import handle_move, handle_mode_selection

# keyboards (انت كنت مستخدمها قبل كده)
from keyboards import main_menu_keyboard

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")

# ✅ start فيها UI زي ما انت عامل
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"أهلاً يا {user.first_name} 👋\nاختار عايز تلعب إيه:",
        reply_markup=main_menu_keyboard()
    )

# ✅ handler موحد (زي القديم بتاعك)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data in ["mode_pvp", "mode_bot"]:
        await handle_mode_selection(query, context)

    elif data in ["rock", "paper", "scissors"]:
        await handle_move(query, context)

    elif data == "back_main":
        await query.edit_message_text(
            "رجعنا للقائمة الرئيسية 👇",
            reply_markup=main_menu_keyboard()
        )

def main():
    print("🚀 بدء تشغيل API...")
    print("🤖 بدء تشغيل البوت...")

    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN مش متضاف")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
