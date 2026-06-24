import json, random, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db, config, keyboards, game_logic, utils

logger = logging.getLogger(__name__)

# ... (سنكتفي هنا بدوال أساسية، وسأعطيك الملف كامل لو حابب)

async def tournament_menu(update, context):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    tour_id = context.user_data.get("tour_created")
    if not tour_id:
        tour_id = db.create_tournament("بطولة الأبطال")
        context.user_data["tour_created"] = tour_id
    tour = db.get_tournament(tour_id)
    players = json.loads(tour["players"] or "[]")
    text = f"🏆 {tour['name']}\nالمشاركون: {len(players)}/8"
    text += "\n✅ أنت مسجل" if user.id in players else "\nاضغط للانضمام"
    await query.edit_message_text(text, reply_markup=keyboards.tournament_keyboard(tour_id))

async def join_tournament_handler(update, context):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    tour_id = int(query.data.split("_")[-1])
    ok = db.join_tournament(tour_id, user.id)
    if ok:
        tour = db.get_tournament(tour_id)
        players = json.loads(tour["players"] or "[]")
        if len(players) == 8:
            db.update_tournament(tour_id, status="started", current_round=1,
                                 bracket=json.dumps(players))
            await context.bot.send_message(user.id, "بدأت البطولة! سيتم إعلامك بالخصم.")
        await query.edit_message_text("تم تسجيلك في البطولة ✅")
    else:
        await query.edit_message_text("البطولة ممتلئة أو حدث خطأ.")

# ... (باقي الدوال مشابهة، سأدمجها في bot.py بشكل مباشر للحفاظ على البساطة)
