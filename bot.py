import os
import random
import asyncio
from datetime import datetime
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

async def game_timeout(game_id, context):
    await asyncio.sleep(120)
    game = active_games.get(game_id)
    if game:
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
        parts = data.split("_")
        choice = parts[-1]
        game_id = "_".join(parts[1:-1])
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

    # ── Channel ──
    elif data == "play_channel":
        channels = db.get_active_channels()
        bot_username = context.bot.username
        text = "📺 *اللعب في القنوات والجروبات*\n\n"
        if channels:
            text += "الجروبات النشطة الآن:\n"
            for ch in channels:
                text += f"• {ch['title']}\n"
            text += "\n"
        text += (
            "عشان تفعّل البوت في جروبك:\n"
            "1️⃣ أضف البوت للجروب\n"
            f"2️⃣ اعمله Admin\n"
            "3️⃣ ابعت /activate في الجروب\n\n"
            f"🔗 لينك البوت: @{bot_username}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_play"))

    elif data.startswith("ch_"):
        parts = data.split("_")
        channel_id = int(parts[1])
        choice = parts[2]
        bot_choice = random.choice(list(CHOICES.keys()))
        result = get_result(choice, bot_choice)
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0) if u else 0
        pts_add = 10 if result == "win" else (5 if result == "draw" else 2)
        if u:
            wins = int(u.get("wins", 0) or 0)
            losses = int(u.get("losses", 0) or 0)
            draws = int(u.get("draws", 0) or 0)
            if result == "win": wins += 1
            elif result == "loss": losses += 1
            else: draws += 1
            db.update_user(user.id, points=pts+pts_add, wins=wins, losses=losses, draws=draws)
        channel_last_play[channel_id] = datetime.now()
        emoji = "🎉" if result == "win" else ("🤝" if result == "draw" else "😢")
        txt = "كسبت!" if result == "win" else ("تعادل!" if result == "draw" else "خسرت!")
        await query.answer(f"{emoji} {txt} (+{pts_add} نقطة)", show_alert=True)

    # ── Rank ──
    elif data == "menu_rank":
        await query.edit_message_text("🏆 اختار نوع التصنيف:",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("📅 يومي", callback_data="rank_daily"),
                                           InlineKeyboardButton("📆 أسبوعي", callback_data="rank_weekly")],
                                          [InlineKeyboardButton("🗓️ شهري", callback_data="rank_monthly"),
                                           InlineKeyboardButton("📊 إجمالي", callback_data="rank_all")],
                                          [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
                                      ]))

    elif data.startswith("rank_"):
        period = data.replace("rank_", "")
        period_names = {"daily": "اليومي", "weekly": "الأسبوعي", "monthly": "الشهري", "all": "الإجمالي"}
        lb = db.get_leaderboard(10, period)
        medals = ["🥇","🥈","🥉"]
        text = f"🏆 *التصنيف {period_names.get(period, '')}*\n\n"
        for i, u in enumerate(lb):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} *{u['name']}* — {u.get('points',0)} نقطة\n"
        if not lb:
            text += "مفيش لاعبين لسه!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_rank"))

    # ── Profile ──
    elif data == "menu_profile":
        u = db.get_user(user.id)
        total = int(u.get("wins",0)) + int(u.get("losses",0)) + int(u.get("draws",0))
        wr = round(int(u.get("wins",0)) / total * 100, 1) if total > 0 else 0
        clan = u.get("clan","") or "بدون عشيرة"
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        text = (
            f"👤 *ملفك الشخصي*\n\n"
            f"الاسم: {u['name']}\n"
            f"💰 النقاط: {u.get('points',0)}\n"
            f"🗡️ العشيرة: {clan}\n"
            f"✅ انتصارات: {u.get('wins',0)}\n"
            f"❌ خسارات: {u.get('losses',0)}\n"
            f"🤝 تعادل: {u.get('draws',0)}\n"
            f"📈 نسبة الفوز: {wr}%\n"
            f"🎯 إجمالي: {total}\n\n"
            f"🔗 رابط دعوتك:\n`{ref_link}`"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Referral ──
    elif data == "menu_referral":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        u = db.get_user(user.id)
        refs = int(u.get("referrals", 0) or 0)
        text = (
            f"🔗 *رابط الدعوة بتاعك*\n\n`{ref_link}`\n\n"
            f"👥 عدد من دعوتهم: {refs}\n"
            f"💰 مكافأة كل دعوة: 1000 نقطة\n\n"
            f"ابعت الرابط لأصحابك وكسب نقاط!"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Tasks ──
    elif data == "menu_tasks":
        tasks = db.get_tasks("daily")
        text = "🎁 *المهام اليومية*\n\nأكمل المهام واكسب نقاط إضافية!\n\n"
        for t in tasks:
            text += f"• {t['description']} — 💰 {t['points_reward']} نقطة\n"
        clan_tasks = db.get_tasks("clan")
        text += "\n🗡️ *مهام العشائر*\n\n"
        for t in clan_tasks:
            text += f"• {t['description']} — 💰 {t['points_reward']} نقطة\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Shop ──
    elif data == "menu_shop":
        items = db.get_shop_items()
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        text = f"🛒 *المتجر*\n💰 نقاطك: {pts}\n\n"
        btns = []
        for item in items:
            text += f"{item['emoji']} *{item['name']}* — {item['price']} نقطة\n_{item['description']}_\n\n"
            btns.append([InlineKeyboardButton(f"{item['emoji']} {item['name']} ({item['price']} نقطة)", callback_data=f"buy_{item['item_id']}")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("buy_"):
        item_id = data.replace("buy_", "")
        items = db.get_shop_items()
        item = next((i for i in items if i["item_id"] == item_id), None)
        if not item:
            await query.answer("❌ المنتج مش موجود!", show_alert=True)
            return
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        price = int(item["price"])
        if pts < price:
            await query.answer(f"❌ نقاطك مش كفاية! محتاج {price} نقطة.", show_alert=True)
            return
        owned = u.get("shop_items", "") or ""
        if item_id in owned.split(","):
            await query.answer("✅ عندك المنتج ده بالفعل!", show_alert=True)
            return
        new_items = f"{owned},{item_id}".strip(",")
        db.update_user(user.id, points=pts-price, shop_items=new_items)
        await query.answer(f"✅ اشتريت {item['name']}!", show_alert=True)

    # ── Clans ──
    elif data == "menu_clans":
        clans = db.get_all_clans()
        u = db.get_user(user.id)
        user_clan = u.get("clan", "") or ""
        text = "🗡️ *العشائر*\n\n"
        if clans:
            for i, c in enumerate(clans[:10]):
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
                members = len(str(c.get("members","")).split(",")) if c.get("members") else 0
                text += f"{medal} *{c['clan_name']}* — {c.get('points',0)} نقطة — {members} عضو\n"
        else:
            text += "مفيش عشائر لسه!\n"
        btns = []
        if user_clan:
            btns.append([InlineKeyboardButton(f"🗡️ عشيرتي: {user_clan}", callback_data=f"clan_view_{user_clan}")])
        else:
            btns.append([InlineKeyboardButton("➕ إنشاء عشيرة", callback_data="clan_create")])
            if clans:
                btns.append([InlineKeyboardButton("🚪 انضم لعشيرة", callback_data="clan_join_menu")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data == "clan_create":
        await query.edit_message_text("✏️ ابعت اسم العشيرة (من 2 لـ 20 حرف):", reply_markup=back_btn("menu_clans"))
        context.user_data["awaiting"] = "clan_name"
        context.user_data["awaiting_time"] = datetime.now()

    elif data == "clan_join_menu":
        clans = db.get_all_clans()
        btns = [[InlineKeyboardButton(c["clan_name"], callback_data=f"clan_join_{c['clan_name']}")] for c in clans]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_clans")])
        await query.edit_message_text("اختار العشيرة:", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("clan_join_"):
        clan_name = data.replace("clan_join_", "")
        clan = db.get_clan(clan_name)
        if not clan:
            await query.answer("❌ العشيرة مش موجودة!", show_alert=True)
            return
        u = db.get_user(user.id)
        if u.get("clan"):
            await query.answer("❌ انت في عشيرة بالفعل!", show_alert=True)
            return
        members = str(clan.get("members","")).split(",")
        members.append(str(user.id))
        db.update_clan(clan_name, members=",".join(members))
        db.update_user(user.id, clan=clan_name)
        await query.edit_message_text(f"✅ انضممت لعشيرة *{clan_name}*!", parse_mode="Markdown", reply_markup=back_btn("menu_clans"))

    elif data.startswith("clan_view_"):
        clan_name = data.replace("clan_view_", "")
        clan = db.get_clan(clan_name)
        if not clan:
            await query.edit_message_text("❌ العشيرة مش موجودة!")
            return
        members_count = len(str(clan.get("members","")).split(",")) if clan.get("members") else 0
        is_leader = str(user.id) == str(clan.get("leader_id",""))
        text = (
            f"🗡️ *{clan_name}*\n\n👥 الأعضاء: {members_count}\n"
            f"💰 النقاط: {clan.get('points',0)}\n"
            f"📝 الوصف: {clan.get('description','') or 'لا يوجد'}\n"
        )
        btns = []
        if is_leader:
            btns.append([InlineKeyboardButton("⚙️ إدارة العشيرة", callback_data=f"clan_manage_{clan_name}")])
        btns.append([InlineKeyboardButton("🚪 مغادرة العشيرة", callback_data=f"clan_leave_{clan_name}")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_clans")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("clan_leave_"):
        clan_name = data.replace("clan_leave_", "")
        db.update_user(user.id, clan="")
        clan = db.get_clan(clan_name)
        if clan:
            members = [m for m in str(clan.get("members","")).split(",") if m != str(user.id)]
            db.update_clan(clan_name, members=",".join(members))
        await query.edit_message_text("✅ غادرت العشيرة.", reply_markup=back_btn("menu_clans"))

    elif data.startswith("clan_manage_"):
        clan_name = data.replace("clan_manage_", "")
        await query.edit_message_text(
            f"⚙️ *إدارة عشيرة {clan_name}*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ تعديل الوصف", callback_data=f"clan_desc_{clan_name}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data=f"clan_view_{clan_name}")]
            ])
        )

    elif data.startswith("clan_desc_"):
        clan_name = data.replace("clan_desc_", "")
        context.user_data["awaiting"] = f"clan_desc:{clan_name}"
        context.user_data["awaiting_time"] = datetime.now()
        await query.edit_message_text("✏️ ابعت الوصف الجديد للعشيرة:", reply_markup=back_btn(f"clan_manage_{clan_name}"))

    # ── How to play ──
    elif data == "menu_howto":
        text = (
            "❓ *طريقة اللعب*\n\n"
            "🪨 حجر يكسر ✂️ مقص\n✂️ مقص يقطع 📄 ورقة\n📄 ورقة تغطي 🪨 حجر\n\n"
            "🎮 *أنواع اللعب:*\n"
            "• فردي — ضد البوت\n• مع صديق — ابعت تحدي\n• عشوائي — مع لاعب عشوائي\n• قنوات — لعب تلقائي كل 30 ثانية\n\n"
            "💰 *النقاط:*\n• فوز = 10 نقطة\n• تعادل = 5 نقاط\n• خسارة = 2 نقطة\n• دعوة صديق = 1000 نقطة\n\n"
            "🗡️ العشائر — انضم وتنافس\n🎁 المهام — نقاط إضافية\n🛒 المتجر — اشتري أيتمز"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Rate ──
    elif data == "menu_rate":
        avg, count = db.get_avg_rating()
        await query.edit_message_text(
            f"⭐ *تقييم البوت*\n\nالتقييم الحالي: {avg}/50 ⭐ ({count} تقييم)\n\nاختار تقييمك:",
            parse_mode="Markdown", reply_markup=stars_keyboard()
        )

    elif data.startswith("rate_"):
        stars = int(data.replace("rate_", ""))
        db.add_rating(user.id, stars)
        await query.edit_message_text(f"✅ شكراً! ديت {stars} نجمة ⭐", reply_markup=back_btn())

    # ── Support ──
    elif data == "menu_support":
        await query.edit_message_text("💎 *دعم البوت*\n\n⭐ قيّم البوت\n📢 شارك مع أصحابك\n💬 ابعت اقتراحاتك", parse_mode="Markdown", reply_markup=back_btn())

    # ── Channels info ──
    elif data == "menu_channels":
        channels = db.get_active_channels()
        text = "📺 *القنوات والجروبات النشطة*\n\n"
        if channels:
            for ch in channels:
                text += f"🟢 {ch['title']}\n"
        else:
            text += "مفيش جروبات نشطة دلوقتي.\n"
        text += "\nعشان تفعّل في جروبك:\n1. ضيف البوت واعمله Admin\n2. ابعت /activate"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # ── Founder Panel ──
    elif data == "founder_panel":
        if not is_founder(user.id):
            await query.answer("❌ مش مسموحلك!", show_alert=True)
            return
        users_count = len(db._cache["users"])
        await query.edit_message_text(f"👑 *لوحة المؤسس*\n\n👥 إجمالي اللاعبين: {users_count}", parse_mode="Markdown", reply_markup=founder_keyboard())

    elif data == "f_stats":
        if not is_founder(user.id): return
        users_count = len(db._cache["users"])
        clans_count = len(db._cache["clans"])
        avg, count = db.get_avg_rating()
        text = (
            f"📊 *إحصائيات البوت*\n\n👥 اللاعبين: {users_count}\n"
            f"🗡️ العشائر: {clans_count}\n⭐ متوسط التقييم: {avg}/50 ({count} تقييم)\n"
            f"📺 جروبات نشطة: {len(channel_auto_game)}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("founder_panel"))

    elif data == "f_ratings":
        if not is_founder(user.id): return
        avg, count = db.get_avg_rating()
        await query.edit_message_text(f"⭐ *التقييمات*\n\nمتوسط: {avg}/50\nعدد التقييمات: {count}", parse_mode="Markdown", reply_markup=back_btn("founder_panel"))

    elif data in ("f_addpts", "f_subpts", "f_ban", "f_unban", "f_broadcast"):
        if not is_founder(user.id): return
        prompts = {
            "f_addpts": "أرسل: add_pts USER_ID AMOUNT",
            "f_subpts": "أرسل: sub_pts USER_ID AMOUNT",
            "f_ban": "أرسل: ban USER_ID",
            "f_unban": "أرسل: unban USER_ID",
            "f_broadcast": "أرسل: broadcast رسالتك هنا",
        }
        context.user_data["awaiting"] = data
        context.user_data["awaiting_time"] = datetime.now()
        await query.edit_message_text(f"👑 {prompts[data]}", reply_markup=back_btn("founder_panel"))

    elif data in ("f_shop", "f_tasks"):
        if not is_founder(user.id): return
        await query.edit_message_text("🔧 إدارة المتجر والمهام قريباً!", reply_markup=back_btn("founder_panel"))

# ── Text Handler ──────────────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    awaiting = context.user_data.get("awaiting", "")
    text = update.message.text.strip()

    awaiting_time = context.user_data.get("awaiting_time")
    if awaiting and awaiting_time:
        if (datetime.now() - awaiting_time).total_seconds() > 120:
            context.user_data.pop("awaiting", None)
            context.user_data.pop("awaiting_time", None)
            await update.message.reply_text("⌛ انتهت صلاحية العملية السابقة.")
            return

    if awaiting == "clan_name":
        if len(text) < 2 or len(text) > 20:
            await update.message.reply_text("❌ الاسم لازم يكون بين 2 و 20 حرف!")
            return
        if db.get_clan(text):
            await update.message.reply_text("❌ الاسم موجود بالفعل!")
            return
        u = db.get_user(user.id)
        if u and u.get("clan"):
            await update.message.reply_text("❌ انت في عشيرة بالفعل!")
            return
        db.create_clan(text, user.id)
        db.update_user(user.id, clan=text)
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None
        await update.message.reply_text(f"✅ تم إنشاء عشيرة *{text}*! 🗡️", parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))

    elif awaiting and awaiting.startswith("clan_desc:"):
        clan_name = awaiting.split(":")[1]
        db.update_clan(clan_name, description=text)
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None
        await update.message.reply_text("✅ تم تحديث الوصف!", reply_markup=main_menu_keyboard(user.id))

    elif awaiting == "f_addpts" and is_founder(user.id):
        parts = text.split()
        if len(parts) == 3 and parts[0] == "add_pts":
            uid, amt = parts[1], int(parts[2])
            u = db.get_user(int(uid))
            if u:
                db.update_user(int(uid), points=int(u.get("points",0))+amt)
                await update.message.reply_text(f"✅ تم إضافة {amt} نقطة للاعب {u['name']}")
            else:
                await update.message.reply_text("❌ اللاعب مش موجود!")
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None

    elif awaiting == "f_subpts" and is_founder(user.id):
        parts = text.split()
        if len(parts) == 3 and parts[0] == "sub_pts":
            uid, amt = parts[1], int(parts[2])
            u = db.get_user(int(uid))
            if u:
                db.update_user(int(uid), points=max(0, int(u.get("points",0))-amt))
                await update.message.reply_text(f"✅ تم خصم {amt} نقطة من {u['name']}")
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None

    elif awaiting == "f_ban" and is_founder(user.id):
        parts = text.split()
        if len(parts) == 2 and parts[0] == "ban":
            db.update_user(int(parts[1]), banned=True)
            await update.message.reply_text("✅ تم الحظر!")
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None

    elif awaiting == "f_unban" and is_founder(user.id):
        parts = text.split()
        if len(parts) == 2 and parts[0] == "unban":
            db.update_user(int(parts[1]), banned=False)
            await update.message.reply_text("✅ تم فك الحظر!")
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None

    elif awaiting == "f_broadcast" and is_founder(user.id):
        parts = text.split(" ", 1)
        if len(parts) == 2 and parts[0] == "broadcast":
            msg = parts[1]
            sent = 0
            user_ids = get_all_user_ids()
            for uid in user_ids:
                try:
                    await context.bot.send_message(int(uid), msg, disable_notification=True)
                    sent += 1
                except tg_error.Forbidden:
                    pass
                except Exception:
                    pass
            await update.message.reply_text(f"✅ تم الإرسال لـ {sent} لاعب!")
        context.user_data["awaiting"] = None
        context.user_data["awaiting_time"] = None

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
