import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards
import utils
from bot import admin_stats, admin_broadcast_prompt, admin_set_points_prompt, admin_channels_list, admin_reset_games
import handlers.channel_handlers as channel_h
import handlers.misc_handlers as misc_h

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الإدارة"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    # تحقق من صلاحيات المؤسس
    if not utils.is_founder(user.id):
        await query.answer("غير مسموح")
        return

    if data == "admin":
        await update.message.reply_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())
    
    elif data == "admin_stats":
        await admin_stats(update, context)
    
    elif data == "admin_broadcast":
        await admin_broadcast_prompt(update, context)
    
    elif data == "admin_set_points":
        await admin_set_points_prompt(update, context)
    
    elif data == "admin_channels":
        await admin_channels_list(update, context)
    
    elif data == "admin_reset":
        await admin_reset_games(update, context)
    
    elif data == "admin_start_channel":
        await channel_h.admin_start_channel_prompt(update, context)
    
    elif data == "admin_stop_channel":
        await channel_h.admin_stop_channel_prompt(update, context)
    
    # أزرار الزعيم العالمي والبطولة والمشاهدة
    elif data == "boss_attack":
        await misc_h.boss_attack(update, context)
    
    elif data == "boss_status":
        await misc_h.boss_command(update, context)
    
    elif data == "tournament":
        await misc_h.tournament_menu(update, context)
    
    elif data.startswith("join_tournament_"):
        await misc_h.join_tournament_handler(update, context)
    
    elif data.startswith("accept_challenge_"):
        await misc_h.accept_challenge(update, context)
    
    elif data.startswith("reject_challenge_"):
        await misc_h.reject_challenge(update, context)
    
    elif data.startswith("spectate_join_"):
        await misc_h.spectate_join(update, context)
    
    else:
        logger.warning(f"زر إدارة غير معروف: {data}")
