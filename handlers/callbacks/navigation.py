import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards
import db

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الملاحة الأساسية"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=keyboards.main_menu())
        return True

    elif data == "delete_message":
        await query.delete_message()
        return True

    elif data == "language":
        u = db.get_user(user.id)
        new_lang = "en" if u["language"] == "ar" else "ar"
        db.update_user(user.id, language=new_lang)
        await query.edit_message_text("تم تغيير اللغة", reply_markup=keyboards.main_menu(new_lang))
        return True

    elif data == "profile":
        # استدعاء /me من bot.py (سنقوم بتحريكه لاحقاً)
        from bot import me_command
        await me_command(update, context)
        return True

    return False
