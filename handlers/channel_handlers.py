import logging
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db
import config
import keyboards
import state
import utils
from engine.game_engine import GameEngine

logger = logging.getLogger(__name__)
engine = GameEngine()

# ========== معالج الحركات ==========
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

# ========== بدء اللعب في القناة ==========
async def channel_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء اللعب في القناة"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    
    # حفظ chat_id في سياق المستخدم للاستخدام لاحقاً
    context.user_data["selected_channel_id"] = chat_id
    
    # بدء حلقة التصويت
    asyncio.create_task(channel_voting_loop(chat_id, context))
    await query.edit_message_text("تم بدء اللعبة! أول جولة خلال لحظات...")

# ========== لوحة المتصدرين الأسبوعية ==========
async def weekly_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أفضل اللاعبين في القناة هذا الأسبوع"""
    query = update.callback_query
    chat_id = int(query.data.split("_")[-1])
    top = db.get_weekly_channel_leaderboard(chat_id, 10)
    text = "🏆 **أفضل 10 لاعبين هذا الأسبوع:**\n"
    for i, r in enumerate(top, 1):
        text += f"{i}. {r['name']} - {r['points']} نقطة\n"
    await query.edit_message_text(text)

# ========== حلقة التصويت التلقائي ==========
async def channel_voting_loop(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """حلقة التصويت التلقائي للقناة"""
    last_message_id = None
    stats_task = None

    while state.channel_settings.get(chat_id):
        try:
            settings = state.channel_settings.get(chat_id, {})
            if not settings:
                break
            interval = settings.get("interval", 60)
            ttl = settings.get("ttl", 30)

            # حذف الرسالة السابقة
            if last_message_id:
                try:
                    await context.bot.delete_message(chat_id, last_message_id)
                except:
                    pass
                last_message_id = None

            # حدث عشوائي
            current_event = None
            if random.random() < config.EVENT_CHANCE:
                current_event = random.choice(config.POSSIBLE_EVENTS)

            event_text = _get_event_text(current_event)

            # بدء الجولة
            end_str = await engine.start_round(chat_id, interval, ttl)
            end_dt = datetime.fromisoformat(end_str)

            # إرسال رسائل الجولة
            try:
                msg = await context.bot.send_message(
                    chat_id,
                    f"🔥 **جولة جديدة!** (تنتهي خلال {interval} ثانية)\n{event_text}\nاختر حركتك:",
                    reply_markup=keyboards.rps_keyboard()
                )
                invite_message_id = msg.message_id
                
                pred_msg = await context.bot.send_message(
                    chat_id,
                    "🔮 توقع الحركة الفائزة:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("👊", callback_data=f"predict_{chat_id}_rock"),
                         InlineKeyboardButton("✋", callback_data=f"predict_{chat_id}_paper"),
                         InlineKeyboardButton("✌️", callback_data=f"predict_{chat_id}_scissors")]
                    ])
                )
                pred_message_id = pred_msg.message_id
            except Exception as e:
                logger.error(f"خطأ في جولة القناة {chat_id}: {e}")
                await asyncio.sleep(5)
                continue

            # تحديث الإحصائيات المباشرة
            if stats_task:
                stats_task.cancel()
            stats_task = asyncio.create_task(
                _update_live_stats(chat_id, end_dt, invite_message_id, event_text, context)
            )

            # انتظار انتهاء الجولة
            remaining = (end_dt - datetime.now()).total_seconds()
            if remaining > 0:
                try:
                    await asyncio.sleep(remaining)
                except asyncio.CancelledError:
                    if stats_task:
                        stats_task.cancel()
                    try:
                        await context.bot.delete_message(chat_id, invite_message_id)
                    except:
                        pass
                    try:
                        await context.bot.delete_message(chat_id, pred_message_id)
                    except:
                        pass
                    raise

            if stats_task:
                stats_task.cancel()

            # إنهاء الجولة
            result = await engine.finish_round(chat_id, event=current_event)

            # حذف رسالة التوقع
            try:
                await context.bot.delete_message(chat_id, pred_message_id)
            except:
                pass

            # معالجة النتائج
            last_message_id = await _process_round_results(
                chat_id, result, current_event, invite_message_id, context
            )

            await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info(f"تم إلغاء حلقة القناة {chat_id}")
            if stats_task:
                stats_task.cancel()
            break
        except Exception as e:
            logger.error(f"خطأ غير متوقع في حلقة القناة {chat_id}: {e}")
            await asyncio.sleep(5)

    async with state.channel_settings_lock:
        if chat_id in state.channel_settings:
            del state.channel_settings[chat_id]

# ========== دوال مساعدة ==========
def _get_event_text(event):
    """نص الحدث العشوائي"""
    if event == "double_points":
        return "🎁 حدث: نقاط مضاعفة!"
    elif event == "shuffle":
        return "🌀 حدث: خلط الأصوات!"
    elif event == "boss":
        return "🐉 حدث: الزعيم يشارك!"
    elif event == "reverse_win":
        return "🔄 حدث: عكس الفوز! الحركة الأقل تفوز"
    elif event == "random_winner":
        return "🎲 حدث: فائز عشوائي!"
    elif event in config.BANNED_MOVE_EVENTS:
        banned = config.BANNED_MOVE_EVENTS[event]
        return f"🚫 حدث: {banned} محظور هذه الجولة!"
    return ""

async def _update_live_stats(chat_id, end_dt, message_id, event_text, context):
    """تحديث إحصائيات الجولة بشكل مباشر"""
    while datetime.now() < end_dt:
        try:
            stats = engine.get_live_stats(chat_id)
            if stats:
                text = f"🔥 **جولة جديدة!** (تنتهي قريباً)\n{event_text}\nاختر حركتك:\n\n"
                for move, emoji in [("rock", "🪨"), ("paper", "📄"), ("scissors", "✂️")]:
                    text += f"{emoji} {move}: {stats['counts'][move]}\n"
                text += f"🗳 المجموع: {stats['total']}"
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text,
                        reply_markup=keyboards.dynamic_rps_keyboard(stats['counts'])
                    )
                except:
                    pass
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"خطأ في تحديث الإحصائيات: {e}")
            await asyncio.sleep(3)

async def _process_round_results(chat_id, result, event, message_id, context):
    """معالجة نتائج الجولة وإرسال النتائج"""
    predictions = engine.get_predictions(chat_id)
    prediction_winners = []
    
    if predictions and result and result["winning_moves"]:
        win_move = result["winning_moves"][0]
        for uid, pred in predictions.items():
            if pred == win_move:
                prediction_winners.append(int(uid))
                user_data = db.get_user(int(uid))
                if user_data:
                    db.update_user(int(uid), points=user_data["points"] + config.PREDICTION_BONUS)

    if result and result["players"]:
        counts = result["counts"]
        winners = result["winners"]
        winning = ", ".join(result["winning_moves"])
        is_draw = result["draw"]
        bot_move = utils.markov_bot_choice(0)

        players_rewards = []
        for uid, move in result["players"].items():
            uid_int = int(uid)
            is_winner = uid_int in winners
            base_reward = config.CHANNEL_LOOP_REWARDS["draw"] if is_draw else config.CHANNEL_LOOP_REWARDS["win"] if is_winner else config.CHANNEL_LOOP_REWARDS["loss"]
            if event == "double_points":
                base_reward *= 2
            bonus = 5 if move == bot_move else 0
            user_data = db.get_user(uid_int)
            players_rewards.append({
                "user_id": uid_int,
                "is_winner": is_winner,
                "reward": base_reward + bonus,
                "clan": user_data.get("clan") if user_data else None
            })

        engine.process_rewards(chat_id, players_rewards)

        # حساب MVP
        mvp_user_id = None
        mvp_score = -1
        for p in players_rewards:
            if p["is_winner"]:
                score = p["reward"]
                if score > mvp_score:
                    mvp_score = score
                    mvp_user_id = p["user_id"]
        mvp_name = ""
        if mvp_user_id:
            mvp_user = db.get_user(mvp_user_id)
            mvp_name = mvp_user["first_name"] if mvp_user else "غير معروف"

        # نقاط العشائر
        clan_scores = {}
        for p in players_rewards:
            if p["clan"]:
                clan_scores[p["clan"]] = clan_scores.get(p["clan"], 0) + p["reward"]

        # بناء رسالة النتائج
        text = "📊 **نتائج الجولة:**\n"
        for move, cnt in counts.items():
            text += f"{move}: {cnt} لاعب\n"
        text += f"\n🤖 حركة البوت: {bot_move}\n"
        if is_draw:
            text += f"🤝 تعادل! الحركات المتساوية: {winning}\n"
        else:
            text += f"🏆 الحركة الفائزة: {winning}\n"
            text += f"عدد الفائزين: {len(winners)}\n"
        if mvp_name:
            text += f"\n👑 **MVP الجولة:** {mvp_name} (+{mvp_score} نقطة)"
        if event == "double_points":
            text += "\n🎁 نقاط مضاعفة!"
        if event == "reverse_win":
            text += "\n🔄 حدث عكس الفوز: الحركة الأقل فازت!"
        if event == "random_winner":
            text += "\n🎲 تم اختيار فائز عشوائي!"
        if prediction_winners:
            names = ", ".join([
                db.get_user(uid)["first_name"] for uid in prediction_winners[:5] if db.get_user(uid)
            ])
            text += f"\n🔮 توقع صحيح: {names} (+{config.PREDICTION_BONUS})"
        if clan_scores:
            sorted_clans = sorted(clan_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            text += "\n\n🏰 **ترتيب العشائر:**"
            for i, (clan, score) in enumerate(sorted_clans, 1):
                text += f"\n{i}. {clan} - {score} نقطة"
        text += "\n\nاضغط لرؤية قائمة الأفضل:"
    else:
        text = "لم يشارك أحد في هذه الجولة."

    # إرسال النتائج
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=keyboards.channel_leaderboard_button(chat_id)
        )
        return message_id
    except:
        msg = await context.bot.send_message(
            chat_id,
            text,
            reply_markup=keyboards.channel_leaderboard_button(chat_id)
        )
        return msg.message_id

# ========== معالجات بدء/إيقاف القناة ==========
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
