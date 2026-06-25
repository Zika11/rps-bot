from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# استدعاء الملفات بتاعتك
from game_handlers import handle_move, handle_mode_selection
from keyboards import main_menu_keyboard


# ✅ رسالة البداية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"أهلاً يا {user.first_name} 👋\n"
        "اختار عايز تلعب إيه:",
        reply_markup=main_menu_keyboard()
    )


# ✅ التحكم في كل الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # اختيار مود اللعب
    if data in ["mode_pvp", "mode_bot"]:
        await handle_mode_selection(query, context)

    # اختيار حركة (حجر/ورقة/مقص)
    elif data in ["rock", "paper", "scissors"]:
        await handle_move(query, context)

    # رجوع للقائمة
    elif data == "back_main":
        await query.edit_message_text(
            "رجعنا للقائمة الرئيسية 👇",
            reply_markup=main_menu_keyboard()
        )


# ✅ تشغيل البوت
def main():
    TOKEN = "YOUR_BOT_TOKEN_HERE"  # 🔥 حط التوكن هنا

    app = ApplicationBuilder().token(TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))

    # الأزرار (Callback)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🔥 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
