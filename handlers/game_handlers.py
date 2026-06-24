from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from game_logic import state
import keyboards


# =========================
# 🎮 SOLO PICK
# =========================
async def process_solo_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # example: solo_123_rock
    try:
        _, game_id, player_choice = data.split("_")
        game_id = int(game_id)
    except Exception:
        await query.edit_message_text("❌ حصل خطأ في البيانات")
        return

    result = state.play_solo_round(game_id, player_choice)

    if not result:
        await query.edit_message_text("❌ اللعبة غير موجودة أو انتهت")
        return

    text = (
        f"🎮 النتيجة:\n\n"
        f"👤 اختيارك: {result['player']}\n"
        f"🤖 اختيار البوت: {result['bot']}\n\n"
        f"🏆 النتيجة: {result['result']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=keyboards.after_game_buttons()
    )

    state.finish_solo_game(game_id)


# =========================
# 🔄 REPLAY SOLO
# =========================
async def replay_solo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    game_id = state.start_solo_game(user.id)

    await query.edit_message_text(
        "🎮 اختار حركتك:",
        reply_markup=keyboards.solo_choice_buttons(game_id)
    )


# =========================
# 🧠 CALLBACK ROUTER
# =========================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("solo_"):
        await process_solo_pick(update, context)

    elif data == "replay_solo":
        await replay_solo(update, context)

    elif data == "main_menu":
        await query.edit_message_text(
            "🏠 القائمة الرئيسية:",
            reply_markup=keyboards.main_menu()
        )
