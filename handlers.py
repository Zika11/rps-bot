import random, json, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db
from config import *
from keyboards import *
from game_logic import *
from state import active_games_lock, active_games
from utils import is_founder   # <-- تمت إضافتها

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ─ـ البطولات ─ـ
async def create_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_founder(update.effective_user.id):
        await update.message.reply_text("❌ مش مسموحلك.")
        return
    tourney_id = f"t_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    prize = int(context.args[0]) if context.args and context.args[0].isdigit() else 500
    db.create_tournament(tourney_id, prize)
    await update.message.reply_text(f"🏆 تم إنشاء بطولة جديدة!\nID: {tourney_id}\nالجائزة: {prize} نقطة\nالعدد المطلوب: 8 لاعبين\nاستخدم /join عشان تنضم!")

async def join_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t = db.get_active_tournament()
    if not t:
        await update.message.reply_text("❌ مفيش بطولة مفتوحة حالياً.")
        return
    if db.join_tournament(t["tournament_id"], user.id):
        t = db.get_active_tournament()
        players = [p for p in t["players"].split(",") if p]
        await update.message.reply_text(f"✅ انضميت للبطولة! ({len(players)}/8)")
        if len(players) >= 8:
            t["status"] = "running"
            await start_tournament(t, context)
    else:
        await update.message.reply_text("❌ إما البطولة مقفولة أو انت مشترك بالفعل.")

async def start_tournament(t, context):
    players = [p for p in t["players"].split(",") if p]
    random.shuffle(players)
    rounds = []
    round1 = []
    for i in range(0, 8, 2):
        match = {"p1": players[i], "p2": players[i+1], "winner": None, "status": "pending"}
        round1.append(match)
        try:
            u1 = db.get_user(int(players[i]))
            u2 = db.get_user(int(players[i+1]))
            name1 = u1["name"] if u1 else "لاعب"
            name2 = u2["name"] if u2 else "لاعب"
            await context.bot.send_message(int(players[i]), f"🏆 مباراتك في البطولة ضد {name2}!")
            await context.bot.send_message(int(players[i+1]), f"🏆 مباراتك في البطولة ضد {name1}!")
            async with active_games_lock:
                game_id = f"t_{players[i]}_{players[i+1]}"
                active_games[game_id] = {
                    "p1": int(players[i]), "p1_name": name1,
                    "p2": int(players[i+1]), "p2_name": name2,
                    "c1": None, "c2": None, "created_at": datetime.now(),
                    "best_of": 1, "p1_wins": 0, "p2_wins": 0,
                    "tournament_match": True, "tournament_id": t["tournament_id"],
                    "match_index": i // 2
                }
            kb = mp_keyboard(game_id)
            await context.bot.send_message(int(players[i]), "اختار حركتك:", reply_markup=kb)
            await context.bot.send_message(int(players[i+1]), "اختار حركتك:", reply_markup=kb)
        except Exception as e:
            logging.error(f"خطأ بدء مباراة البطولة: {e}")
    rounds.append(round1)
    t["rounds"] = json.dumps(rounds)
    db.update_tournament(t["tournament_id"], rounds=t["rounds"], status="running")

async def handle_tournament_match_result(game, winner_id, context):
    t = db.get_tournament(game["tournament_id"])
    if not t or t["status"] != "running":
        return
    rounds = json.loads(t["rounds"])
    current_round = rounds[-1]
    match = current_round[game["match_index"]]
    match["winner"] = str(winner_id)
    match["status"] = "finished"
    if all(m["status"] == "finished" for m in current_round):
        winners = [m["winner"] for m in current_round if m["winner"]]
        if len(winners) == 1:
            t["winner_id"] = winners[0]
            t["status"] = "finished"
            prize = t["prize"]
            winner_u = db.get_user(int(winners[0]))
            if winner_u:
                db.update_user(int(winners[0]), points=int(winner_u.get("points", 0)) + prize,
                               tournament_wins=int(winner_u.get("tournament_wins", 0)) + 1)
                try:
                    await context.bot.send_message(int(winners[0]), f"🎉 مبروك! أنت بطل البطولة وكسبت {prize} نقطة!")
                except:
                    pass
        else:
            next_round = []
            for i in range(0, len(winners), 2):
                next_round.append({"p1": winners[i], "p2": winners[i+1], "winner": None, "status": "pending"})
                async with active_games_lock:
                    game_id = f"t_{winners[i]}_{winners[i+1]}"
                    u1 = db.get_user(int(winners[i]))
                    u2 = db.get_user(int(winners[i+1]))
                    name1 = u1["name"] if u1 else "لاعب"
                    name2 = u2["name"] if u2 else "لاعب"
                    active_games[game_id] = {
                        "p1": int(winners[i]), "p1_name": name1,
                        "p2": int(winners[i+1]), "p2_name": name2,
                        "c1": None, "c2": None, "created_at": datetime.now(),
                        "best_of": 1, "p1_wins": 0, "p2_wins": 0,
                        "tournament_match": True, "tournament_id": t["tournament_id"],
                        "match_index": i // 2
                    }
                kb = mp_keyboard(game_id)
                await context.bot.send_message(int(winners[i]), "اختار حركتك للجولة القادمة:", reply_markup=kb)
                await context.bot.send_message(int(winners[i+1]), "اختار حركتك للجولة القادمة:", reply_markup=kb)
            rounds.append(next_round)
            t["rounds"] = json.dumps(rounds)
    db.update_tournament(t["tournament_id"], rounds=t["rounds"], status=t["status"], winner_id=t["winner_id"])

# ─ـ الأصدقاء ─ـ
async def handle_friend_request(update, context, action, from_id):
    user = update.effective_user
    if action == "accept":
        db.add_friend(user.id, int(from_id))
        db.remove_friend_request(user.id, int(from_id))
        await update.callback_query.answer("✅ تم قبول الصداقة!", show_alert=True)
    elif action == "reject":
        db.remove_friend_request(user.id, int(from_id))
        await update.callback_query.answer("❌ تم رفض الطلب.", show_alert=True)
    await show_friend_list(update, context)

async def show_friend_list(update, context):
    query = update.callback_query
    user = query.from_user
    friends = db.get_friends(user.id)
    requests = db.get_friend_requests(user.id)
    text = "👥 قائمة الأصدقاء\n\n"
    if friends:
        for fid in friends:
            fuser = db.get_user(int(fid))
            if fuser:
                text += f"• {fuser['name']}\n"
    else:
        text += "لا يوجد أصدقاء بعد.\n"
    if requests:
        text += f"\n📥 طلبات الصداقة ({len(requests)}):\n"
    btns = []
    if friends:
        for fid in friends:
            fuser = db.get_user(int(fid))
            if fuser:
                btns.append([InlineKeyboardButton(f"⚔️ تحدي {fuser['name']}", callback_data=f"friend_challenge_{fid}")])
    btns.append([InlineKeyboardButton("➕ إضافة صديق", callback_data="add_friend")])
    if requests:
        btns.append([InlineKeyboardButton("📥 عرض الطلبات", callback_data="view_requests")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns))

# ─ـ التحديات الجماعية ─ـ
async def group_challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ("supergroup", "group"):
        await update.message.reply_text("⚠️ الأمر ده للجروبات بس!")
        return
    if not is_founder(user.id):
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ لازم تكون مشرف.")
            return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("استخدام: /groupchallenge <عدد_الانتصارات> <المدة_بالساعات> [الجائزة]")
        return
    try:
        target_wins = int(args[0])
        hours = int(args[1])
        prize = int(args[2]) if len(args) > 2 else 500
    except:
        await update.message.reply_text("أرقام غير صحيحة.")
        return
    challenge_id = f"gc_{chat.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db.create_group_challenge(challenge_id, chat.id, target_wins, prize, hours)
    await update.message.reply_text(f"🏆 تم بدء تحدي جماعي!\nالهدف: {target_wins} انتصارات\nالمدة: {hours} ساعة\nالجائزة: {prize} نقطة")

async def update_group_challenge(group_id, user_id, wins, context):
    challenge = db.get_active_group_challenge(group_id)
    if challenge:
        db.update_group_challenge_participant(challenge["challenge_id"], user_id, wins)
        if challenge["winner_id"]:
            winner_id = int(challenge["winner_id"])
            db.update_user(winner_id, points=int(db.get_user(winner_id).get("points", 0)) + challenge["prize"])
            try:
                await context.bot.send_message(
                    group_id,
                    f"🎉 {db.get_user(winner_id)['name']} فاز بالتحدي الجماعي وحصل على {challenge['prize']} نقطة!"
                )
            except Exception as e:
                logging.error(f"فشل إرسال إشعار فوز تحدي جماعي: {e}")

# ─ـ الألقاب والثيمات ─ـ
async def titles_shop_handler(update, context):
    query = update.callback_query
    titles = db.get_titles_shop()
    u = db.get_user(query.from_user.id)
    gems = u.get("gems", 0)
    text = f"🏅 متجر الألقاب\n💎 جواهرك: {gems}\n\n"
    btns = []
    for t in titles:
        owned = (u.get("title") == t["title_id"])
        if owned:
            text += f"✅ {t['name']} - {t['description']}\n"
        else:
            text += f"🔒 {t['name']} - {t['description']} ({t['cost_gems']} جوهرة)\n"
            btns.append([InlineKeyboardButton(f"شراء {t['name']} ({t['cost_gems']}💎)", callback_data=f"buytitle_{t['title_id']}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns))

async def buy_title_handler(update, context, title_id):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    titles = db.get_titles_shop()
    title = next((t for t in titles if t["title_id"] == title_id), None)
    if not title:
        await query.answer("لقب غير موجود", show_alert=True)
        return
    if u.get("gems", 0) < title["cost_gems"]:
        await query.answer("جواهر غير كافية", show_alert=True)
        return
    db.update_user(user.id, gems=u["gems"] - title["cost_gems"], title=title_id)
    await query.answer(f"اشتريت لقب {title['name']}!", show_alert=True)

async def themes_shop_handler(update, context):
    query = update.callback_query
    themes = db.get_themes_shop()
    u = db.get_user(query.from_user.id)
    gems = u.get("gems", 0)
    text = f"🎨 متجر الثيمات\n💎 جواهرك: {gems}\n\n"
    btns = []
    for th in themes:
        owned = (u.get("theme") == th["theme_id"])
        if owned:
            text += f"✅ {th['name']} - {th['description']}\n"
        else:
            text += f"🔒 {th['name']} - {th['description']} ({th['cost_gems']} جوهرة)\n"
            btns.append([InlineKeyboardButton(f"شراء {th['name']} ({th['cost_gems']}💎)", callback_data=f"buytheme_{th['theme_id']}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns))

async def buy_theme_handler(update, context, theme_id):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    themes = db.get_themes_shop()
    theme = next((t for t in themes if t["theme_id"] == theme_id), None)
    if not theme:
        await query.answer("ثيم غير موجود", show_alert=True)
        return
    if u.get("gems", 0) < theme["cost_gems"]:
        await query.answer("جواهر غير كافية", show_alert=True)
        return
    db.update_user(user.id, gems=u["gems"] - theme["cost_gems"], theme=theme_id)
    await query.answer(f"اشتريت ثيم {theme['name']}!", show_alert=True)

# ─ـ صندوق الغنائم ─ـ
async def open_loot_box(update, context):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    owned = [o for o in (u.get("shop_items", "") or "").split(",") if o]
    if "item_6" not in owned:
        await query.answer("❌ ما عندكش صندوق كنز.", show_alert=True)
        return
    owned.remove("item_6")
    db.update_user(user.id, shop_items=",".join(owned))
    roll = random.random()
    if roll < 0.5:
        points_won = random.randint(500, 1500)
        db.update_user(user.id, points=int(u.get("points", 0)) + points_won)
        msg = f"🎁 فتحت صندوق الكنز وكسبت {points_won} نقطة!"
    elif roll < 0.8:
        all_items = db.get_shop_items()
        cards = [i for i in all_items if i["item_id"] != "item_6"]
        if cards:
            chosen = random.choice(cards)
            new_owned = [o for o in (u.get("shop_items", "") or "").split(",") if o] + [chosen["item_id"]]
            db.update_user(user.id, shop_items=",".join(new_owned))
            msg = f"🎁 فتحت صندوق الكنز وحصلت على {chosen['emoji']} {chosen['name']}!"
        else:
            points_won = random.randint(500, 1500)
            db.update_user(user.id, points=int(u.get("points", 0)) + points_won)
            msg = f"🎁 فتحت صندوق الكنز وكسبت {points_won} نقطة!"
    else:
        gems_won = random.randint(1, 5)
        db.update_user(user.id, gems=int(u.get("gems", 0)) + gems_won)
        msg = f"🎁 فتحت صندوق الكنز وكسبت {gems_won} جوهرة 💎!"
    await query.answer(msg, show_alert=True)
    await show_my_items(update, context)

async def show_my_items(update, context):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    owned = [o for o in (u.get("shop_items", "") or "").split(",") if o]
    items = db.get_shop_items()
    counts = {}
    for o in owned:
        counts[o] = counts.get(o, 0) + 1
    text = "🎒 بطاقاتي\n\n"
    if not owned:
        text += "ما عندكش بطاقات."
    else:
        for item_id, count in counts.items():
            item = next((i for i in items if i["item_id"] == item_id), None)
            if item:
                text += f"{item['emoji']} {item['name']} (x{count})\n"
    btns = []
    if owned:
        for item_id in set(owned):
            item = next((i for i in items if i["item_id"] == item_id), None)
            if item:
                if item_id == "item_6":
                    btns.append([InlineKeyboardButton("🎁 فتح صندوق الكنز", callback_data="open_box")])
                else:
                    btns.append([InlineKeyboardButton(f"استخدام {item['name']}", callback_data=f"use_{item_id}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns))

# ─ـ الأحداث الموسمية ─ـ
async def event_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ev = db.get_active_event()
    if not ev:
        await update.message.reply_text("لا يوجد حدث حالي.")
        return
    tasks_str = ""
    if ev["special_tasks"]:
        for t in ev["special_tasks"]:
            tasks_str += f"• {t['description']} — {t['reward']} نقطة\n"
    text = f"🎉 الحدث الحالي: {ev['name']}\nينتهي: {ev['end_date']}\n\n🎯 مهام خاصة:\n{tasks_str}"
    await update.message.reply_text(text)

# ─ـ حرب العشائر ─ـ
async def clan_war_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    war = db.get_active_clan_war()
    if not war:
        await update.message.reply_text("لا توجد حرب عشائر حالية.")
        return
    cp = json.loads(war["clan_points"])
    sorted_clans = sorted(cp.items(), key=lambda x: x[1], reverse=True)
    text = "⚔️ حرب العشائر\n\n"
    for i, (clan, pts) in enumerate(sorted_clans[:10], 1):
        text += f"{i}. {clan}: {pts} نقطة\n"
    await update.message.reply_text(text)

async def start_clan_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_founder(update.effective_user.id):
        await update.message.reply_text("❌ غير مسموح.")
        return
    days = int(context.args[0]) if context.args else 7
    war = db.create_clan_war(duration_days=days)
    await update.message.reply_text(f"⚔️ بدأت حرب العشائر! تنتهي بعد {days} يوم.")

async def end_war_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_founder(update.effective_user.id):
        await update.message.reply_text("❌ غير مسموح.")
        return
    war = db.get_active_clan_war()
    if not war:
        await update.message.reply_text("لا توجد حرب نشطة.")
        return
    db.end_clan_war(war["war_id"])
    await update.message.reply_text(f"🏆 انتهت حرب العشائر! العشيرة الفائزة: {war.get('winner_clan', '?')}")

# ─ـ وضع القصة ─ـ
async def story_mode_handler(update, context):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    level = u.get("story_level", 1)
    boss = STORY_LEVELS.get(level)
    if not boss:
        await query.edit_message_text("🎉 لقد أكملت كل المستويات!")
        return
    text = f"📖 المستوى {level}\n\n{boss['story']}\nالزعيم: {boss['emoji']} {boss['boss']}\nاختار حركتك:"
    await query.edit_message_text(text, reply_markup=solo_keyboard(user.id))
    context.user_data["in_story_mode"] = True

# ─ـ Spock ─ـ
async def play_spock_handler(update, context):
    query = update.callback_query
    choices = CHOICES_SPOCK
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=f"spock_{k}") for k, v in choices.items()]])
    await query.edit_message_text("🖖 اختار حركتك (Spock):", reply_markup=kb)

async def handle_spock_choice(update, context, choice):
    query = update.callback_query
    user = query.from_user
    bot_choice = random.choice(list(CHOICES_SPOCK.keys()))
    if choice == bot_choice:
        result = "draw"
    elif bot_choice in WIN_MAP_SPOCK[choice]:
        result = "win"
    else:
        result = "loss"
    u = db.get_user(user.id)
    pts = int(u.get("points", 0) or 0)
    if result == "win":
        pts_add = 10
        wins = int(u.get("wins", 0)) + 1
        losses = int(u.get("losses", 0))
        draws = int(u.get("draws", 0))
    elif result == "loss":
        pts_add = -3
        wins = int(u.get("wins", 0))
        losses = int(u.get("losses", 0)) + 1
        draws = int(u.get("draws", 0))
    else:
        pts_add = 5
        wins = int(u.get("wins", 0))
        losses = int(u.get("losses", 0))
        draws = int(u.get("draws", 0)) + 1
    pts = max(0, pts + pts_add)
    db.update_user(user.id, points=pts, wins=wins, losses=losses, draws=draws)
    await query.edit_message_text(
        f"انت: {CHOICES_SPOCK[choice]}\nالبوت: {CHOICES_SPOCK[bot_choice]}\n\n"
        f"{'🎉 كسبت!' if result == 'win' else '😢 خسرت!' if result == 'loss' else '🤝 تعادل!'} ({'+' if pts_add >= 0 else ''}{pts_add} نقطة)\n💰 نقاطك: {pts}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 العب تاني", callback_data="play_spock")],
            [InlineKeyboardButton("🏠 القائمة", callback_data="menu_main")]
        ])
    )
