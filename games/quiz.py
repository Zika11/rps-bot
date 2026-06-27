import random
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import db
import keyboards

logger = logging.getLogger(__name__)

# أسئلة افتراضية
DEFAULT_QUESTIONS = [
    {
        "question": "ما هي عاصمة مصر؟",
        "options": ["القاهرة", "الإسكندرية", "الجيزة", "بورسعيد"],
        "answer": 0
    },
    {
        "question": "كم عدد أركان الإسلام؟",
        "options": ["3", "4", "5", "6"],
        "answer": 2
    },
    {
        "question": "ما هي أكبر قارة في العالم؟",
        "options": ["أفريقيا", "آسيا", "أمريكا الشمالية", "أوروبا"],
        "answer": 1
    },
    {
        "question": "من هو مؤسس شركة مايكروسوفت؟",
        "options": ["ستيف جوبز", "بيل غيتس", "مارك زوكربيرغ", "إيلون ماسك"],
        "answer": 1
    },
    {
        "question": "ما هو الكوكب الأقرب إلى الشمس؟",
        "options": ["الزهرة", "الأرض", "عطارد", "المريخ"],
        "answer": 2
    }
]

# تخزين جلسات اللعبة
quiz_sessions = {}

class QuizGame:
    """لعبة أسئلة وأجوبة - اختيار من متعدد"""
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء لعبة الأسئلة"""
        query = update.callback_query
        user = query.from_user
        
        # استخدام الأسئلة الافتراضية
        questions = DEFAULT_QUESTIONS.copy()
        random.shuffle(questions)
        questions = questions[:10]  # حد أقصى 10 أسئلة
        
        quiz_sessions[user.id] = {
            "questions": questions,
            "current": 0,
            "score": 0,
            "total": len(questions)
        }
        
        await QuizGame._send_question(query, user)
        return True
    
    @staticmethod
    async def _send_question(query, user):
        """إرسال السؤال الحالي"""
        session = quiz_sessions.get(user.id)
        if not session:
            await query.edit_message_text("❌ انتهت الجلسة.")
            return
        
        current = session["current"]
        total = session["total"]
        
        if current >= total:
            # انتهت الأسئلة
            score = session["score"]
            points_reward = score * 5
            
            user_data = db.get_user(user.id)
            db.update_user(user.id, points=user_data["points"] + points_reward)
            
            await query.edit_message_text(
                f"🏁 **انتهت الأسئلة!**\n\n"
                f"أجبت على {score} من {total} سؤالاً بشكل صحيح.\n"
                f"ربحت {points_reward} نقطة! 🎊\n\n"
                f"هل تريد لعب جولة جديدة؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 جولة جديدة", callback_data="quiz_again")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
                ])
            )
            del quiz_sessions[user.id]
            return
        
        q = session["questions"][current]
        buttons = []
        for i, option in enumerate(q["options"]):
            buttons.append([InlineKeyboardButton(option, callback_data=f"quiz_answer_{i}")])
        
        await query.edit_message_text(
            f"📝 **سؤال {current + 1} من {total}**\n\n"
            f"{q['question']}\n\n"
            f"اختر الإجابة الصحيحة:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    @staticmethod
    async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إجابة المستخدم"""
        query = update.callback_query
        user = query.from_user
        data = query.data
        
        try:
            answer_index = int(data.split("_")[-1])
        except:
            await query.answer("إجابة غير صالحة!")
            return
        
        session = quiz_sessions.get(user.id)
        if not session:
            await query.answer("انتهت الجلسة!")
            return
        
        current = session["current"]
        q = session["questions"][current]
        correct = q["answer"]
        
        if answer_index == correct:
            session["score"] += 1
            await query.answer("✅ إجابة صحيحة! +1")
        else:
            await query.answer(f"❌ الإجابة الصحيحة هي: {q['options'][correct]}")
        
        session["current"] += 1
        await QuizGame._send_question(query, user)
    
    @staticmethod
    async def again(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إعادة تشغيل اللعبة"""
        query = update.callback_query
        user = query.from_user
        
        questions = DEFAULT_QUESTIONS.copy()
        random.shuffle(questions)
        questions = questions[:10]
        
        quiz_sessions[user.id] = {
            "questions": questions,
            "current": 0,
            "score": 0,
            "total": len(questions)
        }
        
        await QuizGame._send_question(query, user)

# تسجيل الهاندلرز
def register_handlers(app):
    """تسجيل معالجات لعبة الأسئلة"""
    app.add_handler(CallbackQueryHandler(QuizGame.start, pattern="^quiz$"))
    app.add_handler(CallbackQueryHandler(QuizGame.again, pattern="^quiz_again$"))
    app.add_handler(CallbackQueryHandler(QuizGame.handle_answer, pattern="^quiz_answer_"))
    return app
