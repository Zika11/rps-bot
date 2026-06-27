import random
import logging
from typing import Dict, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class GuessNumberGame:
    """لعبة خمن الرقم - إدارة الجلسات والمنطق"""
    
    def __init__(self):
        self.sessions: Dict[int, Dict] = {}  # user_id -> session data
    
    def start_game(self, user_id: int, min_num: int = 1, max_num: int = 100, attempts: int = 7) -> Tuple[str, InlineKeyboardMarkup]:
        """بدء لعبة جديدة"""
        secret = random.randint(min_num, max_num)
        self.sessions[user_id] = {
            "secret": secret,
            "min": min_num,
            "max": max_num,
            "attempts": attempts,
            "remaining": attempts,
            "guesses": [],
            "hint": f"اختر رقم بين {min_num} و {max_num}"
        }
        return self.get_status(user_id)
    
    def guess(self, user_id: int, number: int) -> Tuple[str, Optional[bool]]:
        """
        محاولة تخمين
        Returns: (رسالة, هل فاز؟ أو None لو لسه)
        """
        if user_id not in self.sessions:
            return "⚠️ لا توجد لعبة نشطة. استخدم /guess_start لبدء لعبة جديدة.", None
        
        session = self.sessions[user_id]
        session["remaining"] -= 1
        session["guesses"].append(number)
        
        if number == session["secret"]:
            # فوز
            result = self._win(user_id)
            return result, True
        elif session["remaining"] <= 0:
            # خسارة
            result = self._lose(user_id)
            return result, False
        else:
            # استمرار
            hint = "أكبر" if number < session["secret"] else "أصغر"
            session["hint"] = f"❌ {number} ليس صحيحاً. الرقم {hint}. متبقي {session['remaining']} محاولات."
            return session["hint"], None
    
    def get_status(self, user_id: int) -> str:
        """الحصول على حالة اللعبة الحالية"""
        if user_id not in self.sessions:
            return "⚠️ لا توجد لعبة نشطة."
        session = self.sessions[user_id]
        text = f"🎯 خمن الرقم (بين {session['min']} و {session['max']})\n"
        text += f"📊 المحاولات المتبقية: {session['remaining']}\n"
        if session["guesses"]:
            text += f"📝 تخميناتك السابقة: {', '.join(map(str, session['guesses']))}\n"
        text += f"\n💡 {session['hint']}"
        return text
    
    def _win(self, user_id: int) -> str:
        session = self.sessions[user_id]
        return f"🎉 تهانينا! لقد خمنت الرقم {session['secret']} في {len(session['guesses'])} محاولات!"
    
    def _lose(self, user_id: int) -> str:
        session = self.sessions[user_id]
        return f"😢 لقد نفذت المحاولات! الرقم كان {session['secret']}. حاول مجدداً!"
    
    def end_game(self, user_id: int) -> bool:
        """إنهاء اللعبة وحذف الجلسة"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            return True
        return False
    
    def is_active(self, user_id: int) -> bool:
        return user_id in self.sessions

# مثيل واحد للاستخدام
guess_game = GuessNumberGame()

# ========== Handlers للعبة ==========
async def guess_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء لعبة خمن الرقم"""
    user = update.effective_user
    if guess_game.is_active(user.id):
        await update.message.reply_text("⚠️ لديك لعبة نشطة بالفعل! استخدم /guess_status لمتابعتها.")
        return
    
    text, keyboard = guess_game.start_game(user.id)
    await update.message.reply_text(text, reply_markup=keyboard)

async def guess_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تخمين رقم (استخدام من خلال الأزرار أو الكتابة)"""
    user = update.effective_user
    if not guess_game.is_active(user.id):
        await update.message.reply_text("⚠️ لا توجد لعبة نشطة. استخدم /guess_start لبدء لعبة جديدة.")
        return
    
    # محاولة قراءة الرقم من النص
    try:
        number = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح!")
        return
    
    result, won = guess_game.guess(user.id, number)
    if won is True:
        # فوز - نهاية اللعبة
        await update.message.reply_text(result)
        guess_game.end_game(user.id)
    elif won is False:
        # خسارة - نهاية اللعبة
        await update.message.reply_text(result)
        guess_game.end_game(user.id)
    else:
        # مستمر
        await update.message.reply_text(result)

async def guess_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض حالة اللعبة الحالية"""
    user = update.effective_user
    status = guess_game.get_status(user.id)
    await update.message.reply_text(status)

async def guess_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء اللعبة الحالية"""
    user = update.effective_user
    if guess_game.end_game(user.id):
        await update.message.reply_text("✅ تم إنهاء اللعبة.")
    else:
        await update.message.reply_text("⚠️ لا توجد لعبة نشطة.")
