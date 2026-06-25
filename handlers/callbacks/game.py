import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import keyboards
import state
import db
import handlers.game_handlers as game_h

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار أوضاع اللعب والحركات"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    # أوضاع اللعب الرئيسية
    if data == "game":
        await query.edit_message_text("اختر نمط اللعب:", reply_markup=keyboards.game_mode_menu())
    
    elif data == "solo":
        await game_h.solo_start(update, context)
    
    elif data == "random":
        await game_h.random_matchmaking(update, context)
    
    elif data == "friend":
        await game_h.friend_challenge_prompt(update, context)
    
    elif data == "channel":
        await query.edit_message_text("تحدي القنوات: أرسل هذه الرسالة في قناة/مجموعة واطلب من شخص الرد بـ /accept")
        context.user_data["channel_challenge_active"] = True
    
    elif data == "spock":
        from config import SPOCK_CHOICES
        buttons = [InlineKeyboardButton(icon, callback_data=f"spockpick_{key}") for key, icon in SPOCK_CHOICES.items()]
        await query.edit_message_text("اختر حركتك (Spock):", reply_markup=InlineKeyboardMarkup([buttons]))
    
    elif data == "story":
        await query.edit_message_text("وضع القصة قيد التطوير...", reply_markup=keyboards.back_button())

    # اختيار الحركات
    elif data.startswith("pick_"):
        parts = data.split("_", 2)
        if len(parts) < 3: return
        game_type = parts[1]
        tail = parts[2]
        try:
            game_id, move = tail.rsplit("_", 1)
        except ValueError:
            return
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        if game_type == "solo":
            await game_h.process_solo_pick(update, context, move, game_id)
        elif game_type == "random":
            await game_h.process_random_pick(update, context, move, game_id)
        elif game_type == "tournament":
            try:
                tour_id = game_id
                match_index, move = tail.rsplit("_", 1)
                match_index = int(match_index)
            except:
                return
            await game_h.process_tournament_pick(update, context, move, tour_id, match_index)
        elif game_type == "spectate":
            await game_h.process_spectate_pick(update, context, move, game_id)
        elif game_type == "mass":
            chat_id = int(game_id)
            db.add_mass_pick(chat_id, user.id, move)
            await query.edit_message_text("تم تسجيل حركتك في المعركة الجماعية!")

    elif data.startswith("group_pick_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        player_id = int(parts[4])
        game_id = parts[5]
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        await game_h.process_group_solo_pick(update, context, move, chat_id, player_id, game_id)

    elif data.startswith("spockpick_"):
        move = data.split("_", 1)[1]
        await game_h.process_spock_move(update, context, move)

    elif data.startswith("open_pick_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        await game_h.process_open_pick(update, context, move, chat_id)

    elif data.startswith("open_accept_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        await game_h.process_open_acceptor_pick(update, context, move, chat_id)

    # ألعاب المجموعة
    elif data.startswith("group_solo_"):
        chat_id = int(data.split("_")[-1])
        game_id = state.start_solo_game(user.id)
        state.group_solo_games[user.id] = {"chat_id": chat_id, "game_id": game_id}
        keyboard = keyboards.group_choice_buttons(chat_id, user.id, game_id)
        sent = await context.bot.send_message(chat_id, f"🎮 {user.first_name} يلعب ضد البوت. اختر حركتك:", reply_markup=keyboard)
        state.group_solo_games[user.id]["message_id"] = sent.message_id
        await query.answer("ظهرت أزرار الاختيار في المجموعة.")
    
    elif data.startswith("group_random_join_"):
        chat_id = int(data.split("_")[-1])
        async with state.group_session_lock:
            session = state.group_game_sessions.get(chat_id)
            if not session:
                await query.answer("انتهت الجلسة الحالية. انتظر الجولة القادمة.")
                return
            if user.id in session["players"]:
                await query.answer("أنت مشترك بالفعل!")
                return
            session["players"].add(user.id)
            await query.answer("تم تسجيلك في اللعبة العشوائية! 🎲")
    
    elif data.startswith("group_friend_"):
        await query.answer("استخدم /challenge في المجموعة.")
    
    elif data.startswith("group_open_"):
        chat_id = int(data.split("_")[-1])
        await game_h.start_open_challenge(update, context, chat_id)
    
    elif data.startswith("accept_open_"):
        chat_id = int(data.split("_")[-1])
        await game_h.accept_open_challenge(update, context, chat_id)
    
    elif data.startswith("spectate_"):
        chat_id = int(data.split("_")[-1])
        import handlers.misc_handlers as misc_h
        await misc_h.spectate_room_create(update, context)

    else:
        logger.warning(f"زر لعبة غير معروف: {data}")
