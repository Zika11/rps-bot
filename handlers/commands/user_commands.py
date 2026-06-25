import logging
from datetime import datetime, date
from telegram import Update
from telegram.ext import ContextTypes
import db, config, keyboards, game_logic

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        u = db.get_user(user.id)
        if not u:
            db.create_user(user.id, user.username, user.first_name)
            args = context.args
            if args and args[0].startswith("ref"):
                try:
                    ref_id = int(args[0][3:])
                    if ref_id != user.id:
                        ref_user = db.get_user(ref_id)
                        if ref_user:
                            db.update_user(ref_id,
                                           referrals=int(ref_user.get("referrals",0)) + 1,
                                           points=int(ref_user.get("points",0)) + config.REFERRAL_REWARD)
                            await context.bot.send_message(ref_id, f"🎉 {user.first_name} انضم عبر رابط الإحالة الخاص بك! ربحت {config.REFERRAL_REWARD} نقطة.")
                except:
                    pass
        else:
            today = date.today().isoformat()
            last = u.get("last_login")
            streak = int(u.get("login_streak",0))
            if last:
                last_date = date.fromisoformat(last[:10])
                diff = (date.today() - last_date).days
                if diff == 1: streak += 1
                elif diff > 1: streak = 1
            else:
                streak = 1
            days = (date.today() - date.fromisoformat(u["registered_date"][:10])).days if u.get("registered_date") else 0
            db.update_user(user.id, last_login=datetime.now().isoformat(), login_streak=streak, days_since_register=days)
            await game_logic.check_achievements(user.id, context)
        text = f"أهلاً {user.first_name}! اختر من القائمة:"
        await update.message.reply_text(text, reply_markup=keyboards.main_menu())
    except Exception as e:
        logger.error(f"خطأ في أمر /start: {e}")
        await update.message.reply_text("حدث خطأ، الرجاء المحاولة لاحقاً.")

async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        await update.message.reply_text("سجّل دخولك أولاً باستخدام /start")
        return
    rating = db.get_user_rating(user.id) or config.DEFAULT_RATING
    tier_name, tier_icon = config.get_tier_info(rating)
    frame = db.get_user_frame(user.id)
    frame_icon = config.AVATAR_FRAMES.get(frame, "⬛")
    wins = u.get("wins", 0)
    losses = u.get("losses", 0)
    draws = u.get("draws", 0)
    total = wins + losses + draws
    winrate = f"{(wins / total * 100):.1f}%" if total > 0 else "0%"
    xp = u.get("xp", 0)
    level = u.get("level", 1)
    level_title, level_icon = "مبتدئ", "🥉"
    for lvl in sorted(config.LEVEL_TITLES.keys(), reverse=True):
        if level >= lvl:
            level_title, level_icon = config.LEVEL_TITLES[lvl]
            break
    profile_text = (
        f"{frame_icon} {u['first_name']}\n"
        f"🏅 التصنيف: {rating} نقطة\n"
        f"{tier_icon} الرانك: {tier_name}\n"
        f"⬆️ المستوى: {level} {level_icon} ({level_title})\n"
        f"⚔️ الإنتصارات: {wins}\n"
        f"💀 الهزائم: {losses}\n"
        f"🤝 التعادلات: {draws}\n"
        f"📈 نسبة الفوز: {winrate}\n"
        f"💎 الجواهر: {u.get('gems', 0)}\n"
        f"🎖 الإنجازات: {len((u.get('achievements') or '').split(',')) if u.get('achievements') else 0}\n"
        f"🏘️ العشيرة: {u.get('clan', 'لا يوجد')}"
    )
    await update.message.reply_text(profile_text)

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    result = db.claim_daily(user.id)
    if result is None:
        await update.message.reply_text("لقد حصلت على مكافأتك اليومية بالفعل! ⏳")
        return
    day = result["day"]
    points = result["points"]
    gems = result["gems"]
    text = f"🎁 **مكافأة اليوم {day}**\n+{points} نقطة"
    if gems > 0:
        text += f" +{gems} جوهرة"
    await update.message.reply_text(text)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start=ref{user.id}"
    u = db.get_user(user.id)
    refs = u.get("referrals", 0) if u else 0
    text = f"🔗 **رابط الإحالة الخاص بك:**\n{ref_link}\n\nعدد المدعوين: {refs}\nكل من ينضم عبر هذا الرابط يكسبك {config.REFERRAL_REWARD} نقطة."
    await update.message.reply_text(text)
