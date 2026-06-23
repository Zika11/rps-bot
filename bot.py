import os
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
import db

TOKEN = os.environ.get("BOT_TOKEN", "")

CHOICES = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
WIN_MAP = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

# In-memory game state
pending_matches = []       # للعب العشوائي
active_games = {}          # game_id -> game data
channel_auto_game = {}     # channel_id -> game data
channel_last_play = {}     # channel_id -> timestamp

# ── Helpers ──────────────────────────────────────────────────────────

def get_result(p1, p2):
    if p1 == p2: return "draw"
    return "win" if WIN_MAP[p1] == p2 else "loss"

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 العب الآن", callback_data="menu_play")],
        [InlineKeyboardButton("🏆 التصنيف", callback_data="menu_rank"),
         InlineKeyboardButton("🗡️ العشائر", callback_data="menu_clans")],
        [InlineKeyboardButton("🎁 المهام", callback_data="menu_tasks"),
         InlineKeyboardButton("🛒 المتجر", callback_data="menu_shop")],
        [InlineKeyboardButton("📺 القنوات", callback_data="menu_channels"),
         InlineKeyboardButton("👤 حسابي", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ طريقة اللعب", callback_data="menu_howto"),
         InlineKeyboardButton("⭐ تقييم البوت", callback_data="menu_rate")],
        [InlineKeyboardButton("💎 دعم البوت", callback_data="menu_support")],
    ])

def play_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 لعب فردي (ضد البوت)", callback_data="play_solo")],
        [InlineKeyboardButton("👥 لعب مع صديق", callback_data="play_friend")],
        [InlineKeyboardButton("🎲 لعب عشوائي", callback_data="play_random")],
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
    rows = []
    row = []
    for i in range(1, 51):
        row.append(InlineKeyboardButton(str(i), callback_data=f"rate_{i}"))
        if len(row) == 10:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")])
    return InlineKeyboardMarkup(rows)

# ── Commands ──────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.first_name, user.username)
    await update.message.reply_text(
        f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\nاختار من القائمة 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

async def activate_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("channel", "supergroup", "group"):
        await update.message.reply_text("⚠️ الأمر ده للقنوات والجروبات بس!")
        return
    channel_auto_game[chat.id] = None
    channel_last_play[chat.id] = datetime.now()
    await update.message.reply_text(
        "✅ تم تفعيل اللعب التلقائي!\nكل 30 ثانية هتظهر لعبة جديدة تلقائياً 🎮"
    )
    asyncio.create_task(auto_channel_loop(context, chat.id))

# ── Auto Channel Loop ─────────────────────────────────────────────────

async def auto_channel_loop(context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    while channel_id in channel_auto_game:
        await asyncio.sleep(30)
        if channel_id not in channel_auto_game:
            break

        # Check if 30 min passed with no plays
        last = channel_last_play.get(channel_id)
        if last and (datetime.now() - last).seconds > 1800:
            del channel_auto_game[channel_id]
            try:
                await context.bot.send_message(
                    channel_id,
                    "😴 مفيش لاعبين من 30 دقيقة — تم إيقاف اللعب التلقائي.\nابعت /activate عشان تشغله تاني."
                )
            except:
                pass
            break

        game_id = f"ch_{channel_id}_{random.randint(1000,9999)}"
        channel_auto_game[channel_id] = game_id
        try:
            await context.bot.send_message(
                channel_id,
                "🎮 *جولة جديدة!*\nاضغط حركتك 👇",
                parse_mode="Markdown",
                reply_markup=channel_keyboard(channel_id)
            )
        except:
            break

# ── Callbacks ──────────────────────────────────────────────────────────

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    db.get_or_create_user(user.id, user.first_name, user.username)

    # ── Main Menu ──
    if data == "menu_main":
        await query.edit_message_text(
            f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\nاختار من القائمة 👇",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
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
            f"انت: {CHOICES[choice]}\nالبوت: {CHOICES[bot_choice]}\n\n"
            f"{emoji} *{txt}*  (+{pts_add} نقطة)\n💰 نقاطك: {pts}",
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
            "p2": None, "p2_name": None,
            "c1": None, "c2": None
        }
        join_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ قبول التحدي", callback_data=f"join_{game_id}")
        ]])
        await query.edit_message_text(
            f"⚔️ *{user.first_name}* بيتحدى!\nابعت الرسالة دي لصاحبك 👇",
            parse_mode="Markdown"
        )
        await context.bot.send_message(
            user.id,
            f"⚔️ انت بعتت تحدي!\nاستنى صاحبك يقبل...",
        )
        await context.bot.send_message(
            user.id,
            f"📨 ابعت الرسالة دي لصاحبك:",
        )
        await context.bot.send_message(
            user.id,
            f"⚔️ *{user.first_name}* بيتحداك في حجر ورقة مقص!\nاضغط قبول 👇",
            parse_mode="Markdown",
            reply_markup=join_btn
        )

    elif data.startswith("join_"):
        game_id = data.replace("join_", "")
        if game_id not in active_games:
            await query.edit_message_text("❌ التحدي انتهى.")
            return
        game = active_games[game_id]
        if user.id == game["p1"]:
            await query.answer("مش ممكن تقبل تحديك أنت! 😄", show_alert=True)
            return
        game["p2"] = user.id
        game["p2_name"] = user.first_name
        await query.edit_message_text(
            f"⚔️ *{game['p1_name']}* vs *{user.first_name}*\nاللعبة بدأت!",
            parse_mode="Markdown"
        )
        kb = mp_keyboard(game_id)
        await context.bot.send_message(game["p1"], "اختار حركتك 👇", reply_markup=kb)
        await context.bot.send_message(user.id, "اختار حركتك 👇", reply_markup=kb)

    elif data.startswith("mp_"):
        parts = data.split("_")
        game_id = f"{parts[0]}_{parts[1]}_{parts[2]}"
        choice = parts[3]
        if game_id not in active_games:
            await query.edit_message_text("❌ اللعبة انتهت.")
            return
        game = active_games[game_id]
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
            if result == "win":
                r1, r2 = "🎉 كسبت! (+15 نقطة)", "😢 خسرت! (+3 نقطة)"
                u1 = db.get_user(game["p1"])
                u2 = db.get_user(game["p2"])
                db.update_user(game["p1"], points=int(u1.get("points",0))+15, wins=int(u1.get("wins",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+3, losses=int(u2.get("losses",0))+1)
            elif result == "loss":
                r1, r2 = "😢 خسرت! (+3 نقطة)", "🎉 كسبت! (+15 نقطة)"
                u1 = db.get_user(game["p1"])
                u2 = db.get_user(game["p2"])
                db.update_user(game["p1"], points=int(u1.get("points",0))+3, losses=int(u1.get("losses",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+15, wins=int(u2.get("wins",0))+1)
            else:
                r1 = r2 = "🤝 تعادل! (+5 نقطة)"
                u1 = db.get_user(game["p1"])
                u2 = db.get_user(game["p2"])
                db.update_user(game["p1"], points=int(u1.get("points",0))+5, draws=int(u1.get("draws",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+5, draws=int(u2.get("draws",0))+1)

            await context.bot.send_message(game["p1"], summary + f"*{r1}*", parse_mode="Markdown")
            await context.bot.send_message(game["p2"], summary + f"*{r2}*", parse_mode="Markdown")
            del active_games[game_id]

    # ── Random ──
    elif data == "play_random":
        if pending_matches and pending_matches[0]["id"] != user.id:
            opponent = pending_matches.pop(0)
            game_id = f"r_{user.id}_{random.randint(1000,9999)}"
            active_games[game_id] = {
                "p1": opponent["id"], "p1_name": opponent["name"],
                "p2": user.id, "p2_name": user.first_name,
                "c1": None, "c2": None
            }
            kb = mp_keyboard(game_id)
            await query.edit_message_text(f"✅ لاقيت خصم: *{opponent['name']}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
            await context.bot.send_message(opponent["id"], f"✅ لاقيت خصم: *{user.first_name}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
        else:
            pending_matches.append({"id": user.id, "name": user.first_name})
            await query.edit_message_text(
                "🔍 بندور على خصم... استنى!\n\n_(لو مفيش حد متاح هتتلاعب مع البوت تلقائياً)_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ إلغاء", callback_data="cancel_random")
                ]])
            )

    elif data == "cancel_random":
        pending_matches[:] = [m for m in pending_matches if m["id"] != user.id]
        await query.edit_message_text("✅ تم الإلغاء.", reply_markup=main_menu_keyboard())

    # ── Channel game ──
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
            db.update_user(user.id, points=pts + pts_add)

        channel_last_play[channel_id] = datetime.now()

        emoji = "🎉" if result == "win" else ("🤝" if result == "draw" else "😢")
        txt = "كسبت!" if result == "win" else ("تعادل!" if result == "draw" else "خسرت!")
        await query.answer(f"{emoji} {txt} (+{pts_add} نقطة)", show_alert=True)

    # ── Rank ──
    elif data == "menu_rank":
        lb = db.get_leaderboard(10)
        medals = ["🥇","🥈","🥉"]
        text = "🏆 *أفضل 10 لاعبين*\n\n"
        for i, u in enumerate(lb):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} *{u['name']}* — {u.get('points',0)} نقطة\n"
        if not lb:
            text += "مفيش لاعبين لسه!"
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

    # ── Profile ──
    elif data == "menu_profile":
        u = db.get_user(user.id)
        total = int(u.get("wins",0)) + int(u.get("losses",0)) + int(u.get("draws",0))
        wr = round(int(u.get("wins",0)) / total * 100, 1) if total > 0 else 0
        clan = u.get("clan","") or "بدون عشيرة"
        text = (
            f"👤 *ملفك الشخصي*\n\n"
            f"الاسم: {u['name']}\n"
            f"💰 النقاط: {u.get('points',0)}\n"
            f"🗡️ العشيرة: {clan}\n"
            f"✅ انتصارات: {u.get('wins',0)}\n"
            f"❌ خسارات: {u.get('losses',0)}\n"
            f"🤝 تعادل: {u.get('draws',0)}\n"
            f"📈 نسبة الفوز: {wr}%\n"
            f"🎯 إجمالي: {total}"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

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
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

    # ── Shop ──
    elif data == "menu_shop":
        items = db.get_shop_items()
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        text = f"🛒 *المتجر*\n💰 نقاطك: {pts}\n\n"
        btns = []
        for item in items:
            text += f"{item['emoji']} *{item['name']}* — {item['price']} نقطة\n_{item['description']}_\n\n"
            btns.append([InlineKeyboardButton(
                f"{item['emoji']} {item['name']} ({item['price']} نقطة)",
                callback_data=f"buy_{item['item_id']}"
            )])
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
        await query.edit_message_text(
            "✏️ ابعت اسم العشيرة اللي عايز تنشئها:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 إلغاء", callback_data="menu_clans")]])
        )
        context.user_data["awaiting"] = "clan_name"

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
        await query.edit_message_text(f"✅ انضممت لعشيرة *{clan_name}*!", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_clans")]]))

    elif data.startswith("clan_view_"):
        clan_name = data.replace("clan_view_", "")
        clan = db.get_clan(clan_name)
        if not clan:
            await query.edit_message_text("❌ العشيرة مش موجودة!")
            return
        members_count = len(str(clan.get("members","")).split(",")) if clan.get("members") else 0
        text = (
            f"🗡️ *{clan_name}*\n\n"
            f"👑 القائد: {clan.get('leader_id','')}\n"
            f"👥 الأعضاء: {members_count}\n"
            f"💰 النقاط: {clan.get('points',0)}\n"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_clans")]]))

    # ── Channels ──
    elif data == "menu_channels":
        active = [cid for cid in channel_auto_game.keys()]
        text = "📺 *القنوات النشطة*\n\n"
        if active:
            text += f"يوجد {len(active)} قناة/جروب نشطة الآن 🟢\n\n"
        else:
            text += "مفيش قنوات نشطة دلوقتي.\n\n"
        text += "عشان تفعّل البوت في قناتك:\n1. ضيف البوت كـ Admin\n2. ابعت /activate في القناة"
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

    # ── How to play ──
    elif data == "menu_howto":
        text = (
            "❓ *طريقة اللعب*\n\n"
            "🪨 *حجر* يكسر ✂️ مقص\n"
            "✂️ *مقص* يقطع 📄 ورقة\n"
            "📄 *ورقة* تغطي 🪨 حجر\n\n"
            "🎮 *أنواع اللعب:*\n"
            "• *فردي* — العب ضد البوت واكسب نقاط\n"
            "• *مع صديق* — ابعت تحدي لصاحبك\n"
            "• *عشوائي* — اتلاعب مع لاعب عشوائي\n"
            "• *القنوات* — لعب تلقائي كل 30 ثانية\n\n"
            "💰 *النقاط:*\n"
            "• فوز = 10 نقاط\n"
            "• تعادل = 5 نقاط\n"
            "• خسارة = 2 نقطة\n\n"
            "🗡️ *العشائر:* انضم أو أنشئ عشيرة وتنافس\n"
            "🎁 *المهام:* أكمل مهام يومية واكسب نقاط أكتر\n"
            "🛒 *المتجر:* اشتري كروت وأيتمز بنقاطك"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

    # ── Rate ──
    elif data == "menu_rate":
        avg, count = db.get_avg_rating()
        await query.edit_message_text(
            f"⭐ *تقييم البوت*\n\n"
            f"التقييم الحالي: {avg}/50 ⭐ ({count} تقييم)\n\n"
            "اختار تقييمك من 1 لـ 50:",
            parse_mode="Markdown",
            reply_markup=stars_keyboard()
        )

    elif data.startswith("rate_"):
        stars = int(data.replace("rate_", ""))
        db.add_rating(user.id, stars)
        await query.edit_message_text(
            f"✅ شكراً! ديت {stars} نجمة ⭐",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

    # ── Support ──
    elif data == "menu_support":
        await query.edit_message_text(
            "💎 *دعم البوت*\n\n"
            "دعمك بيساعدنا نحسن البوت ونضيف features جديدة!\n\n"
            "⭐ قيّم البوت بـ 50 نجمة\n"
            "📢 شارك البوت مع أصحابك\n"
            "💬 ابعت اقتراحاتك",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]]))

# ── Text handler for clan creation ──
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    awaiting = context.user_data.get("awaiting")

    if awaiting == "clan_name":
        clan_name = update.message.text.strip()
        if len(clan_name) < 2 or len(clan_name) > 20:
            await update.message.reply_text("❌ الاسم لازم يكون بين 2 و 20 حرف!")
            return
        if db.get_clan(clan_name):
            await update.message.reply_text("❌ الاسم ده موجود بالفعل! اختار اسم تاني.")
            return
        u = db.get_user(user.id)
        if u and u.get("clan"):
            await update.message.reply_text("❌ انت في عشيرة بالفعل!")
            return
        db.create_clan(clan_name, user.id)
        db.update_user(user.id, clan=clan_name)
        context.user_data["awaiting"] = None
        await update.message.reply_text(
            f"✅ تم إنشاء عشيرة *{clan_name}*! 🗡️",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("activate", activate_channel))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("✅ البوت شغال...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
