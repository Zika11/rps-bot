from telegram import Update
from telegram.ext import CallbackContext
from keyboards import main_menu_keyboard, game_keyboard, play_again_keyboard
from game_logic import get_bot_choice, get_winner, check_achievements


# 🎮 بدء اللعب
def handle_play(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    query.edit_message_text(
        "اختار حركتك 👇",
        reply_markup=game_keyboard()
    )


# 🎯 اختيار اللاعب
def handle_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    user_choice = query.data.split("_")[1]
    bot_choice = get_bot_choice()

    result = get_winner(user_choice, bot_choice)

    text = f"🤖 اختيار البوت: {bot_choice}\n"

    if result == "win":
        text += "🎉 انت كسبت!"
    elif result == "lose":
        text += "😢 خسرت!"
    else:
        text += "🤝 تعادل!"

    query.edit_message_text(
        text,
        reply_markup=play_again_keyboard()
    )


# 🔙 رجوع للقائمة
def handle_back(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    query.edit_message_text(
        "🏠 القائمة الرئيسية",
        reply_markup=main_menu_keyboard()
    )
