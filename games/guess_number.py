import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
import db
import config
import keyboards

logger = logging.getLogger(__name__)

# تخزين جلسات اللعبة
guess_games = {}

class GuessNumberGame:
    """لعبة خمن الرقم - يختار البوت رقم بين 1 و 100، واللاعب يحاول تخمينه"""
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء لعبة خمن الرقم"""
        query = update.callback_query
        user = query.from_user
        
        # إنشاء لعبة جديدة
        number = random.randint(1, 100)
        attempts = 0
        guess_games[user.id] = {"number": number, "attempts": attempts, "max_attempts": 10}
        
        await query.edit_message_text(
            f"🎯 **لعبة خمن الرقم**\n\n"
            f"مرحباً {user.first_name}!\n"
            f"لقد اخترت رقماً بين 1 و 100.\n"
            f"لديك 10 محاولات لتخمينه.\n\n"
            f"أرسل رقمك (1-100):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 إلغاء", callback_data="back_main")]
            ])
        )
        
        context.user_data["guess_game_active"] = True
        return True
    
    @staticmethod
    async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة تخمين الرقم"""
        user = update.effective_user
        msg = update.message.text.strip()
        
        # التحقق من صحة المدخل
        if not msg.isdigit():
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح (1-100).")
            return
        
        guess = int(msg)
        if guess < 1 or guess > 100:
            await update.message.reply_text("❌ الرقم يجب أن يكون بين 1 و 100.")
            return
        
        # جلب اللعبة
        game = guess_games.get(user.id)
        if not game:
            await update.message.reply_text("❌ لا توجد لعبة نشطة. استخدم /game لبدء لعبة جديدة.")
            return
        
        number = game["number"]
        attempts = game["attempts"] + 1
        game["attempts"] = attempts
        max_attempts = game.get("max_attempts", 10)
        
        # التحقق من التخمين
        if guess == number:
            # فوز
            points_reward = 50 - attempts * 2  # كلما قل المحاولات، زادت النقاط
            if points_reward < 10:
                points_reward = 10
            
            user_data = db.get_user(user.id)
            db.update_user(user.id, points=user_data["points"] + points_reward)
            
            await update.message.reply_text(
                f"🎉 **تهانينا!**\n\n"
                f"لقد خمنت الرقم {number} في {attempts} محاولات.\n"
                f"ربحت {points_reward} نقطة! 🎊\n\n"
                f"هل تريد اللعب مرة أخرى؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 العب مرة أخرى", callback_data="guess_number_again")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
                ])
            )
            del guess_games[user.id]
            context.user_data["guess_game_active"] = False
            return
        
        elif attempts >= max_attempts:
            # خسارة
            await update.message.reply_text(
                f"😔 **انتهت المحاولات!**\n\n"
                f"الرقم الصحيح كان: {number}\n\n"
                f"حظاً أوفر في المرة القادمة!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 العب مرة أخرى", callback_data="guess_number_again")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
                ])
            )
            del guess_games[user.id]
            context.user_data["guess_game_active"] = False
            return
        
        # رسالة المساعدة (أعلى أو أقل)
        hint = "أعلى" if guess < number else "أقل"
        remaining = max_attempts - attempts
        
        await update.message.reply_text(
            f"🔍 الرقم {hint} من {guess}.\n"
            f"المحاولات المتبقية: {remaining}\n"
            f"أرسل تخمينك التالي (1-100):"
        )
    
    @staticmethod
    async def again(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إعادة تشغيل اللعبة"""
        query = update.callback_query
        user = query.from_user
        
        # إنشاء لعبة جديدة
        number = random.randint(1, 100)
        guess_games[user.id] = {"number": number, "attempts": 0, "max_attempts": 10}
        
        await query.edit_message_text(
            f"🔄 **لعبة جديدة!**\n\n"
            f"لقد اخترت رقماً جديداً بين 1 و 100.\n"
            f"لديك 10 محاولات لتخمينه.\n\n"
            f"أرسل رقمك (1-100):"
        )

# تسجيل الهاندلرز
def register_handlers(app):
    """تسجيل معالجات لعبة خمن الرقم"""
    app.add_handler(CallbackQueryHandler(GuessNumberGame.start, pattern="^guess_number$"))
    app.add_handler(CallbackQueryHandler(GuessNumberGame.again, pattern="^guess_number_again$"))
    # معالج النصوص يتم تسجيله بشكل منفصل في bot.py
    return app
