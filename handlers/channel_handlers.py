# handlers/channel_handlers.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import db, config, keyboards, state
from core.channel_manager import channel_voting_loop
from engine.game_engine import GameEngine
import utils

logger = logging.getLogger(__name__)
engine = GameEngine()

# ========== معالج الأزرار ==========
async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الحركات (move_rock, move_paper, move_scissors)"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    move = data.split("_")[1]
    chat_id = query.message.chat_id

    if await state.is_spam_vote(chat_id, user.id):
        await query.answer("أنت تصوت بسرعة كبيرة! انتظر ثانيتين.", show_alert=True)
        return

    success = await engine.vote(chat_id, user.id, move)
    if success:
        await query.answer(f"لقد اخترت {move}! ✅")
        voter_count = engine.get_voter_count(chat_id)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=query.message.message_id,
                text=f"🔥 **جولة جديدة!** (تنتهي قريباً)\nاختر حركتك:\n\n🗳 عدد المصوتين: {voter_count}",
                reply_markup=keyboards.rps_keyboard()
            )
        except Exception as e:
            logger.error(f"فشل تحديث عدد المصوتين: {e}")
    else:
        await query.answer("التصويت متوقف (تجميد ما قبل النهاية).", show_alert=True)

# ========== قائمة القناة ==========
async def channel_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء اللعب في القناة"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    asyncio.create_task(channel_voting_loop(chat_id, context))
    await query.edit_message_text("تم بدء اللعبة! أول جولة خلال لحظات...")

async def weekly_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أفضل اللاعبين في القناة هذا الأسبوع"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    top = db.get_weekly_channel_leaderboard(chat_id, 10)
    text = "🏆 **أفضل 10 لاعبين هذا الأسبوع:**\n"
    for i, r in enumerate(top, 1):
        text += f"{i}. {r['name']} - {r['points']} نقطة\n"
    await query.edit_message_text(text)

# ========== أزرار الإدارة ==========
async def admin_start_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب بدء قناة من المؤسس"""
    query = update.callback_query
    await query.edit_message_text(
        "أرسل معرف القناة (مثل @channelname) مع الإعدادات:\n"
        "`@channelname interval=60 ttl=30`"
    )
    context.user_data["awaiting_start_channel"] = True

async def process_start_channel_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص بدء القناة"""
    user = update.effective_user
    if not utils.is_founder(user.id):
        await update.message.reply_text("غير مسموح")
        return

    text = update.message.text.strip()
    args = text.split()
    if not args:
        await update.message.reply_text("استخدم: @channelname interval=60 ttl=30")
        return

    channel_name = args[0]
    interval = 60
    ttl = 30
    for a in args[1:]:
        if a.startswith("interval="):
            interval = int(a.split("=")[1])
        elif a.startswith("ttl="):
            ttl = int(a.split("=")[1])

    try:
        chat = await context.bot.get_chat(channel_name)
        chat_id = chat.id

        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                old_task = state.channel_settings[chat_id].get("task")
                if old_task:
                    old_task.cancel()
                del state.channel_settings[chat_id]

        task = asyncio.create_task(channel_voting_loop(chat_id, context))
        async with state.channel_settings_lock:
            state.channel_settings[chat_id] = {"interval": interval, "ttl": ttl, "task": task}

        await update.message.reply_text(
            f"تم بدء جولات التصويت التلقائي في {chat.title}\n"
            f"الفاصل: {interval}s | حذف الرسالة: {ttl}s"
        )
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

    context.user_data["awaiting_start_channel"] = False

async def admin_stop_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب إيقاف قناة من المؤسس"""
    query = update.callback_query
    await query.edit_message_text("أرسل معرف القناة (مثل @channelname) لإيقاف اللعبة:")
    context.user_data["awaiting_stop_channel"] = True

async def process_stop_channel_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص إيقاف القناة"""
    user = update.effective_user
    if not utils.is_founder(user.id):
        await update.message.reply_text("غير مسموح")
        return

    text = update.message.text.strip()
    channel_name = text.split()[0]

    try:
        chat = await context.bot.get_chat(channel_name)
        chat_id = chat.id

        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                task = state.channel_settings[chat_id].get("task")
                if task:
                    task.cancel()
                del state.channel_settings[chat_id]
                await update.message.reply_text(f"تم إيقاف جولات التصويت في {chat.title}")
            else:
                await update.message.reply_text("لا توجد جولات نشطة لهذه القناة.")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

    context.user_data["awaiting_stop_channel"] = False
