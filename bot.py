import os
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram import error as tg_error
import db

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في متغيرات البيئة!")

FOUNDER_ID = 1232067711

CHOICES = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
WIN_MAP = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

pending_matches = []
active_games = {}
channel_auto_game = {}
channel_last_play = {}

def get_result(p1, p2):
    if p1 == p2: return "draw"
    return "win" if WIN_MAP[p1] == p2 else "loss"

def is_founder(user_id):
    return user_id == FOUNDER_ID

def main_menu_keyboard(user_id=None):
    rows = [
        [InlineKeyboardButton("🎮 العب الآن", callback_data="menu_play")],
        [InlineKeyboardButton("🏆 التصنيف", callback_data="menu_rank"),
         InlineKeyboardButton("🗡️ العشائر", callback_data="menu_clans")],
        [InlineKeyboardButton("🎁 المهام", callback_data="menu_tasks"),
         InlineKeyboardButton("🛒 المتجر", callback_data="menu_shop")],
        [InlineKeyboardButton("📺 القنوات", callback_data="menu_channels"),
         InlineKeyboardButton("👤 حسابي", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ طريقة اللعب", callback_data="menu_howto"),
         InlineKeyboardButton("⭐ تقييم البوت", callback_data="menu_rate")],
        [InlineKeyboardButton("💎 دعم البوت", callback_data="menu_support"),
         InlineKeyboardButton("🔗 دعوة صديق", callback_data="menu_referral")],
    ]
    if user_id and is_founder(user_id):
        rows.append([InlineKeyboardButton("👑 لوحة المؤسس", callback_data="founder_panel")])
    return InlineKeyboardMarkup(rows)

def back_btn(target="menu_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=target)]])

def play_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 لعب فردي", callback_data="play_solo")],
        [InlineKeyboardButton("👥 لعب مع صديق", callback_data="play_friend")],
        [InlineKeyboardButton("🎲 لعب عشوائي", callback_data="play_random")],
        [InlineKeyboardButton("📺 لعب في قناة/جروب", callback_data="play_channel")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
    ])

def solo_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"solo_{k}")
        for k, v in CHOICES.items()
    ]])

def mp_keyboard(game_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"mp_{game_id}_{k}")
        for k, v in CHOICES.items()
    ]])

def channel_keyboard(channel_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"ch_{channel_id}_{k}")
        for k, v in CHOICES.items()
    ]])

def stars_keyboard():
    options = [1, 5, 10, 20, 30, 40, 50]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'⭐'*(min(s//10+1,3))} {s}", callback_data=f"rate_{s}") for s in options[:4]],
        [InlineKeyboardButton(f"{'⭐'*(min(s//10+1,3))} {s}", callback_data=f"rate_{s}") for s in options[4:]],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
    ])

def founder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة نقاط", callback_data="f_addpts"),
         InlineKeyboardButton("➖ خصم نقاط", callback_data="f_subpts")],
        [InlineKeyboardButton("🚫 حظر لاعب", callback_data="f_ban"),
         InlineKeyboardButton("✅ فك حظر", callback_data="f_unban")],
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="f_broadcast")],
        [InlineKeyboardButton("🛒 إدارة المتجر", callback_data="f_shop"),
         InlineKeyboardButton("🎁 إدارة المهام", callback_data="f_tasks")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="f_stats"),
         InlineKeyboardButton("⭐ التقييمات", callback_data="f_ratings")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
    ])

def get_all_user_ids():
    try:
        return list(db._cache["users"].keys())
    except Exception:
        return []

# ── مؤقت تلقائي لتنظيف الألعاب المعلقة ─────────────────────────────
async def game_timeout(game_id, context):
    await asyncio.sleep(120)
    game = active_games.get(game_id)
    if game:
        # إبلاغ الطرفين
        try:
            await context.bot.send_message(game["p1"], "⌛ انتهت صلاحية التحدي.")
            if game.get("p2"):
                await context.bot.send_message(game["p2"], "⌛ انتهت صلاحية التحدي.")
        except:
            pass
        del active_games[game_id]

# ── Commands ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_bonus = False

    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_id = arg.replace("ref_", "")
            existing = db.get_user(user.id)
            if not existing and str(user.id) != ref_id:
                referrer = db.get_user(int(ref_id))
                if referrer:
                    pts = int(referrer.get("points", 0) or 0)
                    db.update_user(int(ref_id), points=pts + 1000)
                    ref_bonus = True
        elif arg.startswith("challenge_"):
            game_id = arg.replace("challenge_", "")
            game = active_games.get(game_id)
            if not game:
                await update.message.reply_text("❌ التحدي انتهى أو لم يعد موجوداً.")
                return
            if game["p1"] == user.id:
                await update.message.reply_text("❌ لا يمكنك قبول تحدي نفسك!")
                return
            if game["p2"] is not None:
                await update.message.reply_text("❌ هذا التحدي ممتلئ بالفعل!")
                return
            game["p2"] = user.id
            game["p2_name"] = user.first_name
            db.get_or_create_user(user.id, user.first_name, user.username)

            await update.message.reply_text(
                f"✅ تم قبول التحدي! ⚔️ *{game['p1_name']}* vs *{user.first_name}*",
                parse_mode="Markdown"
            )
            kb = mp_keyboard(game_id)
            await context.bot.send_message(game["p1"], "اللعبة بدأت! اختار حركتك 👇", reply_markup=kb)
            await context.bot.send_message(user.id, "اختار حركتك 👇", reply_markup=kb)
            return

    db.get_or_create_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    if u and u.get("banned"):
        await update.message.reply_text("🚫 أنت محظور من استخدام البوت.")
        return

    text = f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\nاختار من القائمة 👇"
    if ref_bonus:
        text += "\n\n🎁 تم منح صاحبك 1000 نقطة على دعوتك!"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))

async def activate_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("supergroup", "group"):
        await update.message.reply_text("⚠️ الأمر ده للجروبات بس!\nللقنوات استخدم القائمة في الشات الخاص.")
        return
    channel_auto_game[chat.id] = None
    channel_last_play[chat.id] = datetime.now()
    db.add_active_channel(chat.id, chat.title or "جروب")
    await update.message.reply_text("✅ تم تفعيل اللعب التلقائي في الجروب!\nكل 30 ثانية هتظهر لعبة جديدة 🎮")
    asyncio.create_task(auto_channel_loop(context, chat.id))

async def auto_channel_loop(context, channel_id):
    while channel_id in channel_auto_game:
        await asyncio.sleep(30)
        if channel_id not in channel_auto_game:
            break
        last = channel_last_play.get(channel_id)
        if last and (datetime.now() - last).seconds > 1800:
            del channel_auto_game[channel_id]
            db.remove_active_channel(channel_id)
            try:
                await context.bot.send_message(channel_id, "😴 مفيش لاعبين من 30 دقيقة — تم إيقاف اللعب التلقائي.\nابعت /activate عشان تشغله تاني.")
            except:
                pass
            break
        try:
            await context.bot.send_message(channel_id, "🎮 *جولة جديدة!* اضغط حركتك 👇", parse_mode="Markdown", reply_markup=channel_keyboard(channel_id))
        except (tg_error.Forbidden, tg_error.BadRequest, tg_error.ChatNotFound):
            del channel_auto_game[channel_id]
            db.remove_active_channel(channel_id)
            break
        except:
            pass

# ── Main Button Handler ───────────────────────────────────────────────
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    db.get_or_create_user(user.id, user.first_name, user.username)

    u = db.get_user(user.id)
    if u and u.get("banned") and not data.startswith("founder"):
        await query.edit_message_text("🚫 أنت محظور من استخدام البوت.")
        return

    # ── Main Menu ──
    if data == "menu_main":
        await query.edit_message_text(
            f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\nاختار من القائمة 👇",
            parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id)
        )

    elif data == "menu_play":
        await query.edit_message_text("🎮 اختار نوع اللعب:", reply_markup=play_menu_keyboard())

    # ── Solo ──
    elif data == "play_solo":
        await query.edit_message_text("🤖 اختار حركتك:", reply_markup=solo_keyboard())

    elif data.startswith("solo_"):
        choice = data.replace("solo_", "")
        bot_choice = random.choice(list(CHOICES.keys()))
        result = get_result(choice, bot_choice)
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        wins = int(u.get("wins", 0) or 0)
        losses = int(u.get("losses", 0) or 0)
        draws = int(u.get("draws", 0) or 0)

        if result == "win":
            emoji, txt, pts_add = "🎉", "كسبت!", 10
            wins += 1
        elif result == "loss":
            emoji, txt, pts_add = "😢", "خسرت!", 2
            losses += 1
        else:
            emoji, txt, pts_add = "🤝", "تعادل!", 5
            draws += 1

        pts += pts_add
        db.update_user(user.id, points=pts, wins=wins, losses=losses, draws=draws)

        await query.edit_message_text(
            f"انت: {CHOICES[choice]}\nالبوت: {CHOICES[bot_choice]}\n\n{emoji} *{txt}*  (+{pts_add} نقطة)\n💰 نقاطك: {pts}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 العب تاني", callback_data="play_solo")],
                [InlineKeyboardButton("🏠 القائمة", callback_data="menu_main")]
            ])
        )

    # ── Friend ──
    elif data == "play_friend":
        game_id = f"f_{user.id}_{random.randint(1000,9999)}"
        active_games[game_id] = {
            "p1": user.id, "p1_name": user.first_name,
            "p2": None, "p2_name": None, "c1": None, "c2": None,
            "created_at": datetime.now()
        }
        # بدء مؤقت الإلغاء التلقائي
        asyncio.create_task(game_timeout(game_id, context))

        bot_username = context.bot.username
        deep_link = f"https://t.me/{bot_username}?start=challenge_{game_id}"
        text = (
            f"⚔️ *تحدي جاهز!*\n\nشارك هذا الرابط مع صديقك:\n[اضغط هنا للدخول]({deep_link})\n\nأو أرسل له النص: `{deep_link}`\n\nفي انتظار الخصم..."
        )
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True,
                                      reply_markup=InlineKeyboardMarkup([[
                                          InlineKeyboardButton("❌ إلغاء التحدي", callback_data=f"cancel_challenge_{game_id}")
                                      ]]))

    elif data.startswith("cancel_challenge_"):
        game_id = data.replace("cancel_challenge_", "")
        game = active_games.get(game_id)
        if game and game["p1"] == user.id:
            del active_games[game_id]
            await query.edit_message_text("✅ تم إلغاء التحدي.", reply_markup=main_menu_keyboard(user.id))
        else:
            await query.answer("❌ لا يمكنك إلغاء هذا التحدي!", show_alert=True)

    # ── Multiplayer (Friend & Random) ──
    elif data.startswith("mp_"):
        # ✅ تصحيح تحليل callback_data
        parts = data.split("_")
        choice = parts[-1]                      # آخر جزء = حركة اللاعب
        game_id = "_".join(parts[1:-1])         # تجميع الأجزاء بين الأول والأخير
        game = active_games.get(game_id)
        if not game:
            await query.edit_message_text("❌ اللعبة انتهت.")
            return

        if user.id == game["p1"] and not game["c1"]:
            game["c1"] = choice
            await query.edit_message_text("✅ اخترت! استنى...")
        elif user.id == game["p2"] and not game["c2"]:
            game["c2"] = choice
            await query.edit_message_text("✅ اخترت! استنى...")
        else:
            return

        if game["c1"] and game["c2"]:
            c1, c2 = game["c1"], game["c2"]
            result = get_result(c1, c2)
            summary = (
                f"⚔️ *النتيجة*\n\n"
                f"{game['p1_name']}: {CHOICES[c1]}\n"
                f"{game['p2_name']}: {CHOICES[c2]}\n\n"
            )
            u1 = db.get_user(game["p1"])
            u2 = db.get_user(game["p2"])
            if result == "win":
                r1, r2 = "🎉 كسبت! (+15 نقطة)", "😢 خسرت! (+3 نقطة)"
                db.update_user(game["p1"], points=int(u1.get("points",0))+15, wins=int(u1.get("wins",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+3, losses=int(u2.get("losses",0))+1)
            elif result == "loss":
                r1, r2 = "😢 خسرت! (+3 نقطة)", "🎉 كسبت! (+15 نقطة)"
                db.update_user(game["p1"], points=int(u1.get("points",0))+3, losses=int(u1.get("losses",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+15, wins=int(u2.get("wins",0))+1)
            else:
                r1 = r2 = "🤝 تعادل! (+5 نقطة)"
                db.update_user(game["p1"], points=int(u1.get("points",0))+5, draws=int(u1.get("draws",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+5, draws=int(u2.get("draws",0))+1)

            await context.bot.send_message(game["p1"], summary + f"*{r1}*", parse_mode="Markdown")
            await context.bot.send_message(game["p2"], summary + f"*{r2}*", parse_mode="Markdown")
            del active_games[game_id]

    # ── Random ──
    elif data == "play_random":
        if any(m["id"] == user.id for m in pending_matches):
            await query.answer("أنت بالفعل في قائمة الانتظار!", show_alert=True)
            return

        if pending_matches:
            opponent = pending_matches.pop(0)
            game_id = f"r_{user.id}_{random.randint(1000,9999)}"
            active_games[game_id] = {
                "p1": opponent["id"], "p1_name": opponent["name"],
                "p2": user.id, "p2_name": user.first_name,
                "c1": None, "c2": None,
                "created_at": datetime.now()
            }
            asyncio.create_task(game_timeout(game_id, context))
            kb = mp_keyboard(game_id)
            await query.edit_message_text(f"✅ لاقيت خصم: *{opponent['name']}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
            await context.bot.send_message(opponent["id"], f"✅ لاقيت خصم: *{user.first_name}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
        else:
            pending_matches.append({"id": user.id, "name": user.first_name})
            await query.edit_message_text("🔍 بندور على خصم... استنى!",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton("❌ إلغاء", callback_data="cancel_random")
                                          ]]))

    elif data == "cancel_random":
        pending_matches[:] = [m for m in pending_matches if m["id"] != user.id]
        await query.edit_message_text("✅ تم الإلغاء.", reply_markup=main_menu_keyboard(user.id))

    # ── باقي الأزرار (قنوات، تصنيف، ملف شخصي...) دون تغيير ─────────
    # (نفس الكود السابق للمتجر والعشائر والتقييم... تم حذفها اختصاراً لكنها موجودة في الملف الكامل)
    # ...
    # يمكنك نسخ باقي الأجزاء من الردود السابقة

# ── Text Handler ──────────────────────────────────────────────────────
# ... (نفس الكود السابق مع التحقق من صلاحية awaiting)

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN غير موجود!")
    db.init_cache()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("activate", activate_channel))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("✅ البوت شغال...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
