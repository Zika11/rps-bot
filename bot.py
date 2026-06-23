import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

CHOICES = {
    "rock": "🪨 حجر",
    "paper": "📄 ورقة",
    "scissors": "✂️ مقص",
}

WIN_MAP = {
    "rock": "scissors",
    "scissors": "paper",
    "paper": "rock",
}

# Stats stored in memory (per user)
user_stats: dict[int, dict] = {}


def get_stats(user_id: int) -> dict:
    if user_id not in user_stats:
        user_stats[user_id] = {"wins": 0, "losses": 0, "draws": 0}
    return user_stats[user_id]


def get_result(player: str, bot: str) -> str:
    if player == bot:
        return "draw"
    elif WIN_MAP[player] == bot:
        return "win"
    else:
        return "loss"


def build_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(label, callback_data=key)
        for key, label in CHOICES.items()
    ]
    return InlineKeyboardMarkup([buttons])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    text = (
        f"أهلاً {name}! 👋\n\n"
        "🎮 *لعبة حجر ورقة مقص*\n\n"
        "اختار حركتك وانا هلعب معاك!\n"
        "استخدم /stats عشان تشوف إحصائياتك\n"
        "استخدم /reset عشان تبدأ من الأول"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=build_keyboard()
    )


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 اختار حركتك:", reply_markup=build_keyboard()
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.first_name
    s = get_stats(update.effective_user.id)
    total = s["wins"] + s["losses"] + s["draws"]
    win_rate = (s["wins"] / total * 100) if total > 0 else 0

    text = (
        f"📊 *إحصائياتك يا {uid}*\n\n"
        f"✅ انتصارات: {s['wins']}\n"
        f"❌ خسارات: {s['losses']}\n"
        f"🤝 تعادل: {s['draws']}\n"
        f"🎯 إجمالي الجولات: {total}\n"
        f"📈 نسبة الفوز: {win_rate:.1f}%"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_stats[uid] = {"wins": 0, "losses": 0, "draws": 0}
    await update.message.reply_text("✅ تم مسح إحصائياتك! ابدأ من الأول 💪")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    player_choice = query.data
    if player_choice not in CHOICES:
        return

    bot_choice = random.choice(list(CHOICES.keys()))
    result = get_result(player_choice, bot_choice)

    uid = query.from_user.id
    s = get_stats(uid)

    if result == "win":
        s["wins"] += 1
        emoji = "🎉"
        result_text = "انت كسبت!"
    elif result == "loss":
        s["losses"] += 1
        emoji = "😢"
        result_text = "انت خسرت!"
    else:
        s["draws"] += 1
        emoji = "🤝"
        result_text = "تعادل!"

    player_label = CHOICES[player_choice]
    bot_label = CHOICES[bot_choice]

    response = (
        f"انت اخترت: {player_label}\n"
        f"انا اخترت: {bot_label}\n\n"
        f"{emoji} *{result_text}*\n\n"
        f"✅ {s['wins']}  ❌ {s['losses']}  🤝 {s['draws']}"
    )

    await query.edit_message_text(
        text=response,
        parse_mode="Markdown",
        reply_markup=build_keyboard(),
    )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(button))

    print("✅ البوت شغال...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
