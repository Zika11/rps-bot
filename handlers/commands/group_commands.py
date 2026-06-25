import logging, random, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards, state, utils

logger = logging.getLogger(__name__)

async def massbattle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    battle_id = db.start_mass_battle(chat_id)
    await context.bot.send_message(chat_id, "⚡ معركة جماعية! اختر حركتك خلال 30 ثانية:",
                                   reply_markup=keyboards.mass_battle_start_button(chat_id))
    await asyncio.sleep(config.MASS_BATTLE_DURATION)
    winners = db.get_mass_battle_results(battle_id)
    if winners:
        for uid in winners:
            user_data = db.get_user(uid)
            db.update_user(uid, points=user_data["points"] + config.MASS_BATTLE_REWARD[0],
                           gems=user_data.get("gems",0) + config.MASS_BATTLE_REWARD[1])
        winner_names = ", ".join([db.get_user(uid)["first_name"] for uid in winners[:5]])
        await context.bot.send_message(chat_id, f"🎉 انتهت المعركة! الفائزون: {winner_names} (+{config.MASS_BATTLE_REWARD[0]} نقطة، +{config.MASS_BATTLE_REWARD[1]} جوهرة)")
    else:
        await context.bot.send_message(chat_id, "لم ينضم أحد للمعركة!")

async def teambattle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("استخدم: /teambattle اسم_الفريق_الأحمر اسم_الفريق_الأزرق")
        return
    team1, team2 = context.args[0], context.args[1]
    battle_id = db.create_team_battle(chat_id, team1, team2)
    await update.message.reply_text(f"🔴 {team1} vs {team2} 🔵\nاضغط للانضمام لفريق:",
                                   reply_markup=keyboards.team_battle_team_buttons(battle_id))
    await asyncio.sleep(60)
    conn = sqlite3.connect(config.DB_NAME)
    battle = conn.execute("SELECT * FROM team_battles WHERE battle_id=?", (battle_id,)).fetchone()
    if not battle: return
    chat_id = battle["chat_id"]
    team1_players = db.get_team_players(battle_id, "red")
    team2_players = db.get_team_players(battle_id, "blue")
    for uid in team1_players:
        await context.bot.send_message(uid, "اختر حركتك لمعركة الفريق:", reply_markup=keyboards.choice_buttons(f"teambattle_{battle_id}"))
    for uid in team2_players:
        await context.bot.send_message(uid, "اختر حركتك لمعركة الفريق:", reply_markup=keyboards.choice_buttons(f"teambattle_{battle_id}"))
    state.team_battle_moves[battle_id] = {}
    await asyncio.sleep(60)
    team1_score, team2_score = 0, 0
    if battle_id in state.team_battle_moves:
        for uid, move in state.team_battle_moves[battle_id].items():
            if uid in team1_players:
                team1_score += 1 if move == "rock" else 0
            elif uid in team2_players:
                team2_score += 1 if move == "rock" else 0
    winner_team = "red" if team1_score > team2_score else "blue" if team2_score > team1_score else "draw"
    await context.bot.send_message(chat_id, f"نتيجة المعركة: {'🔴 فاز الفريق الأحمر' if winner_team=='red' else '🔵 فاز الفريق الأزرق' if winner_team=='blue' else 'تعادل'}")

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id): return
    chat_id = update.effective_chat.id
    reward = random.choice(config.DROP_REWARDS)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎁 افتح الصندوق!", callback_data=f"claim_drop_{reward[0]}_{reward[1]}")]])
    await context.bot.send_message(chat_id, "💥 صندوق مفاجئ! أول واحد يضغط يربح:", reply_markup=keyboard)
