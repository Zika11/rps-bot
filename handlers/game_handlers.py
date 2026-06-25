from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random

# تخزين حالة اللاعبين
user_states = {}

# 🎮 اختيار نوع اللعب
async def handle_mode_selection(query, context):
    data = query.data

    if data == "mode_bot":
        user_states[query.from_user.id] = {"mode": "bot"}

        keyboard = [
            [
                InlineKeyboardButton("🪨 حجر", callback_data="rock"),
                InlineKeyboardButton("📄 ورقة", callback_data="paper"),
                InlineKeyboardButton("✂️ مقص", callback_data="scissors"),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]

        await query.edit_message_text(
            "اختر حركتك 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "mode_pvp":
        await query.edit_message_text("⚔️ PvP لسه تحت التطوير")

# 🧠 منطق اللعبة
def get_winner(player, bot):
    if player == bot:
        return "تعادل 🤝"
    elif (
        (player == "rock" and bot == "scissors") or
        (player == "paper" and bot == "rock") or
        (player == "scissors" and bot == "paper")
    ):
        return "انت كسبت 🎉"
    else:
        return "البوت كسب 🤖"

# 🎯 تنفيذ الحركة
async def handle_move(query, context):
    user_id = query.from_user.id
    player_move = query.data

    if user_id not in user_states:
        await query.answer("ابدأ لعبة الأول", show_alert=True)
        return

    bot_move = random.choice(["rock", "paper", "scissors"])

    result = get_winner(player_move, bot_move)

    text = (
        f"حركتك: {player_move}\n"
        f"حركة البوت: {bot_move}\n\n"
        f"{result}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔁 العب تاني", callback_data="mode_bot"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
