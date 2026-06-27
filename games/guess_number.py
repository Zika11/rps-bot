import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db
import config
import keyboards

logger = logging.getLogger(__name__)

# حالة اللعبة لكل لاعب
game_states = {}

# ========== دوال لعبة خمن الرقم ==========
def start_guess_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء لعبة خمن الرقم"""
    query = update.callback_query
    user = query.from_user
    
    # إنشاء لعبة جديدة
    number = random.randint(1, 100)
    game_states[user.id] = {
        "number": number,
        "attempts": 0,
        "max_attempts": 10,
        "guesses": [],
        "hint": None
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔢 أدخل رقم", callback_data="guess_input")],
        [InlineKeyboardButton("💡 تلميحة", callback_data="guess_hint")],
        [InlineKeyboardButton("🚫 إنهاء اللعبة", callback_data="guess_end")]
    ])
    
    text = (
        f"🎯 **لعبة خمن الرقم**\n\n"
        f"قمت باختيار رقم بين 1 و 100.\n"
        f"لديك {game_states[user.id]['max_attempts']} محاولات.\n\n"
        f"🔢 أدخل رقمك باستخدام الزر أدناه:"
    )
    
    query.edit_message_text(text, reply_markup=keyboard)
    context.user_data["game"] = "guess_number"

def process_guess(update: Update, context: ContextTypes.DEFAULT_TYPE, guess_text: str):
    """معالجة تخمين الرقم"""
    query = update.callback_query if update.callback_query else None
    user = update.effective_user
    chat = update.effective_chat
    
    if user.id not in game_states:
        return False, "❌ لا توجد لعبة نشطة. استخدم /guess لبدء لعبة جديدة."
    
    game = game_states[user.id]
    
    try:
        guess = int(guess_text)
    except ValueError:
        return False, "❌ الرجاء إدخال رقم صحيح."
    
    if guess < 1 or guess > 100:
        return False, "❌ الرقم يجب أن يكون بين 1 و 100."
    
    game["attempts"] += 1
    game["guesses"].append(guess)
    remaining = game["max_attempts"] - game["attempts"]
    
    if guess == game["number"]:
        # فوز
        points_reward = 50 - (game["attempts"] * 2)  # مكافأة حسب عدد المحاولات
        if points_reward < 10:
            points_reward = 10
        
        db.update_user(user.id, points=db.get_user(user.id)["points"] + points_reward)
        db.add_battle_pass_xp(user.id, 20)
        
        text = (
            f"🎉 **مبروك!**\n\n"
            f"لقد خمنت الرقم **{game['number']}** في {game['attempts']} محاولات!\n"
            f"ربحت {points_reward} نقطة و 20 خبرة!\n\n"
            f"📊 تاريخ التخمينات: {', '.join(map(str, game['guesses']))}"
        )
        
        del game_states[user.id]
        return True, text
    
    # لم يخمن
    if guess < game["number"]:
        hint = "📈 الرقم أكبر من ذلك."
    else:
        hint = "📉 الرقم أصغر من ذلك."
    
    if remaining <= 0:
        # خسارة
        text = (
            f"😔 **انتهت المحاولات!**\n\n"
            f"الرقم الصحيح كان **{game['number']}**.\n"
            f"📊 تاريخ التخمينات: {', '.join(map(str, game['guesses']))}"
        )
        del game_states[user.id]
        return False, text
    
    text = (
        f"🔢 **تخمين #{game['attempts']}**\n\n"
        f"{hint}\n"
        f"📊 تاريخ التخمينات: {', '.join(map(str, game['guesses']))}\n"
        f"⏳ المحاولات المتبقية: {remaining}\n\n"
        f"أدخل رقمك التالي:"
    )
    
    # تحديث الرسالة إذا كان query
    if query:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔢 أدخل رقم", callback_data="guess_input")],
            [InlineKeyboardButton("💡 تلميحة", callback_data="guess_hint")],
            [InlineKeyboardButton("🚫 إنهاء اللعبة", callback_data="guess_end")]
        ])
        query.edit_message_text(text, reply_markup=keyboard)
    
    return False, text

def get_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على تلميحة"""
    query = update.callback_query
    user = query.from_user
    
    if user.id not in game_states:
        query.answer("❌ لا توجد لعبة نشطة!")
        return
    
    game = game_states[user.id]
    number = game["number"]
    
    # تلميحات محتملة
    hints = [
        f"الرقم {number}",
        f"مجموع أرقام الرقم هو {sum(int(d) for d in str(number))}",
        f"الرقم {'زوجي' if number % 2 == 0 else 'فردي'}",
        f"الرقم يقع بين {max(1, number - 10)} و {min(100, number + 10)}",
        f"آخر رقم في العدد هو {str(number)[-1]}"
    ]
    
    # استخدام تلميحة جديدة
    if game.get("hint") is None:
        game["hint"] = 0
    else:
        game["hint"] = (game["hint"] + 1) % len(hints)
    
    hint_text = hints[game["hint"]]
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔢 أدخل رقم", callback_data="guess_input")],
        [InlineKeyboardButton("💡 تلميحة أخرى", callback_data="guess_hint")],
        [InlineKeyboardButton("🚫 إنهاء اللعبة", callback_data="guess_end")]
    ])
    
    query.edit_message_text(
        f"💡 **تلميحة:** {hint_text}\n\n"
        f"📊 تاريخ التخمينات: {', '.join(map(str, game['guesses']))}\n"
        f"⏳ المحاولات المتبقية: {game['max_attempts'] - game['attempts']}\n\n"
        f"أدخل رقمك التالي:",
        reply_markup=keyboard
    )

def end_guess_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء لعبة خمن الرقم"""
    query = update.callback_query
    user = query.from_user
    
    if user.id in game_states:
        number = game_states[user.id]["number"]
        del game_states[user.id]
        query.edit_message_text(
            f"🚫 **تم إنهاء اللعبة**\n\n"
            f"الرقم الصحيح كان **{number}**.\n"
            f"يمكنك بدء لعبة جديدة باستخدام /guess."
        )
    else:
        query.answer("لا توجد لعبة نشطة!")
