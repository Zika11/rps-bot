import logging, asyncio, sqlite3
from telegram import Update
from telegram.ext import ContextTypes
import db, config, keyboards, utils, state
import handlers.channel_handlers as channel_h

logger = logging.getLogger(__name__)

# ========== أوامر الإدارة ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    await update.message.reply_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())

async def start_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("استخدم: /start_channel @channelname interval=60 ttl=30")
        return
    channel_name = args[0]
    interval = 60
    ttl = 30
    for a in args[1:]:
        if a.startswith("interval="): interval = int(a.split("=")[1])
        elif a.startswith("ttl="): ttl = int(a.split("=")[1])
    try:
        chat = await context.bot.get_chat(channel_name)
        chat_id = chat.id
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                old_task = state.channel_settings[chat_id].get("task")
                if old_task: old_task.cancel()
                del state.channel_settings[chat_id]
        task = asyncio.create_task(channel_h.channel_voting_loop(chat_id, context))
        async with state.channel_settings_lock:
            state.channel_settings[chat_id] = {"interval": interval, "ttl": ttl, "task": task}
        await update.message.reply_text(f"تم بدء جولات التصويت التلقائي في {chat.title}\nالفاصل: {interval}s | حذف الرسالة: {ttl}s")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

async def stop_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("استخدم: /stop_channel @channelname")
        return
    try:
        chat = await context.bot.get_chat(context.args[0])
        chat_id = chat.id
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                task = state.channel_settings[chat_id].get("task")
                if task: task.cancel()
                del state.channel_settings[chat_id]
                await update.message.reply_text(f"تم إيقاف جولات التصويت في {chat.title}")
            else:
                await update.message.reply_text("لا توجد جولات نشطة لهذه القناة.")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

# ========== دوال الإدارة المستخدمة في الأزرار ==========
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    total_users = len(db.get_all_user_ids())
    conn = sqlite3.connect(config.DB_NAME)
    total_games = conn.execute("SELECT COUNT(*) FROM active_games").fetchone()[0]
    total_clans = conn.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
    conn.close()
    text = (f"👥 المستخدمين: {total_users}\n"
            f"🎮 المباريات النشطة: {total_games}\n"
            f"🏰 العشائر: {total_clans}")
    await query.edit_message_text(text, reply_markup=keyboards.admin_menu())

async def admin_broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل الرسالة التي تريد إرسالها للجميع:", reply_markup=keyboards.back_button("admin"))
    context.user_data["awaiting_broadcast"] = True

async def admin_set_points_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل:\n`user_id points gems`", reply_markup=keyboards.back_button("admin"))
    context.user_data["awaiting_set_points"] = True

async def admin_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with state.channel_settings_lock:
        chans = list(state.channel_settings.keys())
    text = "القنوات المفعلة:\n" + "\n".join([str(c) for c in chans]) if chans else "لا توجد"
    await query.edit_message_text(text, reply_markup=keyboards.admin_menu())

async def admin_reset_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect(config.DB_NAME)
    conn.execute("DELETE FROM active_games")
    conn.execute("DELETE FROM pending_matches")
    conn.commit()
    conn.close()
    await query.answer("تم مسح المباريات العالقة.")
