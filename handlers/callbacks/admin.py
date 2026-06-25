import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards, utils
import handlers.channel_handlers as channel_h
# ✅ استيراد دوال الإدارة من ملف الأوامر بدلاً من bot.py
from handlers.commands.admin_commands import (
    admin_stats, 
    admin_broadcast_prompt, 
    admin_set_points_prompt, 
    admin_channels_list, 
    admin_reset_games
)

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الإدارة"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    # التحقق من صلاحيات المؤسس
    if not utils.is_founder(user.id):
        await query.answer("غير مسموح")
        return True

    if data == "admin":
        await query.edit_message_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())
        return True

    elif data == "admin_stats":
        await admin_stats(update, context)
        return True

    elif data == "admin_broadcast":
        await admin_broadcast_prompt(update, context)
        return True

    elif data == "admin_set_points":
        await admin_set_points_prompt(update, context)
        return True

    elif data == "admin_channels":
        await admin_channels_list(update, context)
        return True

    elif data == "admin_reset":
        await admin_reset_games(update, context)
        return True

    elif data == "admin_start_channel":
        await channel_h.admin_start_channel_prompt(update, context)
        return True

    elif data == "admin_stop_channel":
        await channel_h.admin_stop_channel_prompt(update, context)
        return True

    return False
