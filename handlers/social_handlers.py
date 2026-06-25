# handlers/social_handlers.py
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards
from core.social_manager import (
    send_friend_request, get_pending_requests, accept_friend_request,
    reject_friend_request, get_friends, get_user, get_user_by_username,
    get_clan, create_clan, join_clan, get_all_clans,
    get_clan_treasury, donate_points_to_clan, donate_gems_to_clan,
    upgrade_clan, get_active_war_season, get_clan_war_scores
)

logger = logging.getLogger(__name__)

# ========== الأصدقاء ==========
async def friends_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("قائمة الأصدقاء:", reply_markup=keyboards.friends_menu())

async def add_friend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل معرف المستخدم (@username) الذي تريد إضافته:")
    context.user_data["awaiting_friend_username"] = True

async def process_friend_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = update.message.text.strip().lstrip("@")
    target = get_user_by_username(username)
    if not target:
        await update.message.reply_text("لم يتم العثور على مستخدم بهذا المعرف.")
        return
    if target["user_id"] == user.id:
        await update.message.reply_text("لا يمكنك إضافة نفسك.")
        return
    send_friend_request(user.id, target["user_id"])
    await update.message.reply_text("تم إرسال طلب الصداقة.")
    context.user_data["awaiting_friend_username"] = False

async def friend_requests_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    requests = get_pending_requests(user.id)
    if not requests:
        await query.edit_message_text("لا توجد طلبات صداقة.")
        return
    buttons = []
    for sender_id in requests:
        sender = get_user(sender_id)
        name = sender["first_name"] if sender else str(sender_id)
        buttons.append([
            InlineKeyboardButton(f"قبول من {name}", callback_data=f"accept_friend_{sender_id}"),
            InlineKeyboardButton("رفض", callback_data=f"reject_friend_{sender_id}")
        ])
    buttons.append([InlineKeyboardButton("رجوع", callback_data="friends")])
    await query.edit_message_text("طلبات الصداقة:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_friend_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    if data.startswith("accept_friend_"):
        sender_id = int(data.split("_")[-1])
        accept_friend_request(sender_id, user.id)
        await query.answer("تم قبول الصداقة")
    elif data.startswith("reject_friend_"):
        sender_id = int(data.split("_")[-1])
        reject_friend_request(sender_id, user.id)
        await query.answer("تم رفض الطلب")
    await friend_requests_list(update, context)

async def friend_list_display(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    friends = get_friends(user.id)
    if not friends:
        await query.edit_message_text("لا يوجد أصدقاء بعد.")
        return
    lines = []
    for fid in friends:
        friend = get_user(fid)
        name = friend["first_name"] if friend else "Unknown"
        lines.append(f"- {name}")
    text = "👥 أصدقائي:\n" + "\n".join(lines)
    await query.edit_message_text(text, reply_markup=keyboards.back_button())

# ========== العشائر ==========
async def clans_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("العشائر:", reply_markup=keyboards.clans_menu())

async def clan_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل اسم العشيرة الجديدة:")
    context.user_data["awaiting_clan_name"] = True

async def process_clan_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = update.message.text.strip()
    if get_clan(name):
        await update.message.reply_text("الاسم موجود مسبقاً.")
        return
    if create_clan(name, user.id):
        join_clan(user.id, name)
        await update.message.reply_text(f"تم إنشاء العشيرة {name}!")
    else:
        await update.message.reply_text("حدث خطأ.")
    context.user_data["awaiting_clan_name"] = False

async def clan_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("أرسل اسم العشيرة التي تريد الانضمام إليها:")
    context.user_data["awaiting_join_clan"] = True

async def process_join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    clan_name = update.message.text.strip()
    clan = get_clan(clan_name)
    if not clan:
        await update.message.reply_text("العشيرة غير موجودة.")
        return
    join_clan(user.id, clan_name)
    await update.message.reply_text(f"انضممت إلى {clan_name}!")
    context.user_data["awaiting_join_clan"] = False

async def clan_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clans = get_all_clans()
    text = "🏆 ترتيب العشائر:\n"
    if clans:
        text += "\n".join([f"{i+1}. {c['name']} - {c['points']} نقطة" for i, c in enumerate(clans[:10])])
    else:
        text += "لا توجد عشائر بعد."
    await query.edit_message_text(text, reply_markup=keyboards.back_button())

# ========== خزينة العشيرة ==========
async def clan_treasury_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    u = get_user(user.id)
    clan_name = u.get("clan")
    if not clan_name:
        await query.answer("أنت لست في عشيرة!")
        return
    await query.edit_message_text(f"🏦 خزينة {clan_name}", reply_markup=keyboards.clan_treasury_menu(clan_name))

async def treasury_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clan_name = query.data.split("_")[-1]
    t = get_clan_treasury(clan_name)
    if not t:
        await query.edit_message_text("الخزينة فارغة.")
        return
    upgrades = json.loads(t["upgrades"] or "{}")
    text = f"🏦 خزينة {clan_name}\n💰 نقاط: {t['points']}\n💎 جواهر: {t['gems']}\n\nالتطويرات:\n"
    for up_id, up_data in config.CLAN_UPGRADES.items():
        lvl = upgrades.get(up_id, 0)
        text += f"{up_data['name']}: مستوى {lvl}/{up_data['levels']}\n"
    await query.edit_message_text(text, reply_markup=keyboards.clan_treasury_menu(clan_name))

async def treasury_donate_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    clan_name = query.data.split("_")[-1]
    success, msg = donate_points_to_clan(user.id, clan_name, 50)
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

async def treasury_donate_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    clan_name = query.data.split("_")[-1]
    success, msg = donate_gems_to_clan(user.id, clan_name, 5)
    if success:
        await query.answer(msg)
    else:
        await query.answer(msg)

async def treasury_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clan_name = query.data.split("_")[-1]
    buttons = []
    for up_id in config.CLAN_UPGRADES:
        buttons.append([InlineKeyboardButton(
            config.CLAN_UPGRADES[up_id]['name'],
            callback_data=f"do_upgrade_{clan_name}_{up_id}"
        )])
    buttons.append([InlineKeyboardButton("رجوع", callback_data=f"treasury_view_{clan_name}")])
    await query.edit_message_text("اختر تطويراً:", reply_markup=InlineKeyboardMarkup(buttons))

async def do_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    clan_name = parts[2]
    upgrade_id = parts[3]
    success = upgrade_clan(clan_name, upgrade_id)
    if success:
        await query.answer("تم التطوير بنجاح!")
    else:
        await query.answer("فشل التطوير. نقاط غير كافية أو وصلت لأقصى مستوى.")
    await treasury_view(update, context)

async def clan_war_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    season = get_active_war_season()
    if not season:
        await query.edit_message_text("لا يوجد موسم حرب عشائر نشط حالياً.")
        return
    scores = get_clan_war_scores(season["season_id"])
    text = f"⚔️ موسم حرب العشائر (من {season['start_date'][:10]} إلى {season['end_date'][:10]})\n\n"
    if scores:
        text += "النتائج:\n"
        for s in scores:
            text += f"{s['clan_name']} - {s['region']}: {s['score']} نقطة\n"
    else:
        text += "لا توجد نتائج بعد."
    await query.edit_message_text(text, reply_markup=keyboards.back_button("clans"))
