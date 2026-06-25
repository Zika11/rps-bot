import json, asyncio, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, state, keyboards, game_logic, utils
import engine.users as users_engine

# ---------- أوضاع اللعب الخاص ----------
async def solo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    game_id = state.start_solo_game(user.id)
    await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons(f"solo_{game_id}"))

async def random_matchmaking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    result = await state.add_pending(user.id)
    if result is None:
        await query.answer("أنت بالفعل في قائمة الانتظار أو مشغول بلعبة!")
    elif result is True:
        await query.edit_message_text("بانتظار لاعب آخر...")
    else:
        opp_id = result
        game = state.get_game_by_player(user.id)
        if game:
            await query.edit_message_text("تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"random_{game['game_id']}"))
            await context.bot.send_message(opp_id, "تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"random_{game['game_id']}"))

async def friend_challenge_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل معرف الصديق (@username) لتحديه:")
    context.user_data["awaiting_friend_challenge"] = True

# ---------- معالجة اختيارات اللعب ----------
async def process_solo_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or game["player1"] != user.id:
        await query.edit_message_text("انتهت اللعبة.")
        return

    bot_move = utils.markov_bot_choice(user.id)
    result = game_logic.get_result(move, bot_move)

    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)

    theme = utils.get_choices_for_user(user.id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)

    text = (
        f"أنت: {user_icon} vs البوت: {bot_icon}\n"
        f"النتيجة: {result}"
    )
    await query.edit_message_text(text)
    state.finish_solo_game(game_id)

async def process_random_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or (game["player1"] != user.id and game["player2"] != user.id):
        await query.edit_message_text("انتهت اللعبة.")
        return

    state.set_game_move(game_id, user.id, move)
    moves = state.get_game_moves(game_id)
    p1, p2 = game["player1"], game["player2"]

    if str(p1) in moves and str(p2) in moves:
        m1 = moves[str(p1)]
        m2 = moves[str(p2)]

        res1 = game_logic.get_result(m1, m2)
        res2 = "loss" if res1 == "win" else ("win" if res1 == "loss" else "draw")

        db.apply_game_result(p1, res1, m1, p2)
        db.apply_game_result(p2, res2, m2, p1)

        utils.update_user_moves(p1, m1)
        utils.update_user_moves(p2, m2)

        theme1 = utils.get_choices_for_user(p1)
        theme2 = utils.get_choices_for_user(p2)

        icon1 = theme1.get(m1, m1)
        icon2 = theme2.get(m2, m2)

        text = (
            f"⚔️ {users_engine.get_user(p1)['first_name']} اختار {icon1} vs "
            f"{users_engine.get_user(p2)['first_name']} اختار {icon2}\n"
            f"النتيجة: {res1} لصالح {users_engine.get_user(p1)['first_name']}"
        )

        await query.edit_message_text(text)
        try:
            await context.bot.send_message(p2, text)
        except:
            pass

        await state.remove_game(game_id)
    else:
        await query.edit_message_text("تم تسجيل حركتك، بانتظار الخصم...")

async def process_spock_move(update, context, move):
    query = update.callback_query
    user = query.from_user
    from config import SPOCK_CHOICES, SPOCK_WIN_MAP
    bot_move = random.choice(list(SPOCK_CHOICES.keys()))
    result = "draw" if move == bot_move else ("win" if SPOCK_WIN_MAP[move] == bot_move else "loss")

    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)

    user_icon = SPOCK_CHOICES[move]
    bot_icon = SPOCK_CHOICES[bot_move]

    text = (
        f"🎮 نتيجة Spock:\n"
        f"👤 اختيارك: {user_icon}\n"
        f"🤖 اختيار البوت: {bot_icon}\n"
        f"🏆 النتيجة: {result}"
    )
    await query.edit_message_text(text)

async def challenge_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    friend_name = query.data.split("_", 1)[1]
    user = query.from_user
    friend = users_engine.get_user_by_username(friend_name)
    if not friend:
        await query.answer("لم يتم العثور على المستخدم.")
        return
    await query.edit_message_text(f"🎮 {user.first_name} يتحداك للعب! هل تقبل؟", 
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton("✔️ قبول", callback_data=f"friend_accept_{user.id}"),
                                       InlineKeyboardButton("❌ رفض", callback_data="friend_decline")]
                                  ]))
    context.user_data["pending_challenge"] = {"from": user.id, "to": friend["user_id"]}

async def accept_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementation for accepting friend challenge (omitted for brevity)
    pass
