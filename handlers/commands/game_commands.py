import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import keyboards
import config
import db
from core.matchmaking import MatchmakingManager
from games.guess_number import GuessNumberGame
from utils.logging_utils import logger

# تعريف مدير المطابقة (Singleton)
matchmaking = MatchmakingManager()

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الأمر /game - عرض قائمة الألعاب المتاحة"""
    keyboard = [
        [InlineKeyboardButton("🎮 حجر ورقة مقص", callback_data="game_rps")],
        [InlineKeyboardButton("🔢 خمن الرقم", callback_data="game_guess")],
        [InlineKeyboardButton("❓ أسئلة وأجوبة", callback_data="game_quiz")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    await update.message.reply_text(
        "🎯 **اختر اللعبة التي تريد لعبها:**\n\n"
        "اختر من القائمة أدناه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الأمر /web - رابط الواجهة الإلكترونية (Mini App)"""
    chat_id = update.effective_chat.id
    base_url = config.WEBAPP_URL if hasattr(config, 'WEBAPP_URL') else "https://rps-bot-six.vercel.app"
    web_link = f"{base_url}/?chat={chat_id}"
    await update.message.reply_text(
        f"🌐 **افتح اللعبة في المتصفح:**\n\n"
        f"رابط اللعبة:\n{web_link}\n\n"
        "📱 يمكنك أيضاً فتحها من خلال الزر أدناه:",
        reply_markup=keyboards.mini_app_button()
    )

# ========== معالجات ألعاب جديدة (خمن الرقم) ==========
async def guess_number_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء لعبة خمن الرقم"""
    query = update.callback_query
    user = query.from_user
    
    # إنشاء لعبة جديدة للمستخدم
    game = GuessNumberGame(user.id)
    game.start()
    context.user_data['guess_game'] = game
    
    await query.edit_message_text(
        f"🔢 **لعبة خمن الرقم**\n\n"
        f"🎯 تم اختيار رقم بين 1 و 100.\n"
        f"💡 لديك {game.max_attempts} محاولات.\n\n"
        f"📝 أرسل تخمينك (رقم بين 1 و 100):"
    )

async def guess_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج رسائل لعبة خمن الرقم"""
    user = update.effective_user
    game = context.user_data.get('guess_game')
    
    if not game or game.user_id != user.id or game.is_finished():
        await update.message.reply_text("❌ لا توجد لعبة نشطة. استخدم /game لبدء لعبة جديدة.")
        return
    
    try:
        guess = int(update.message.text.strip())
        result, message = game.guess(guess)
        
        if result == "correct":
            # تحديث نقاط المستخدم
            user_data = db.get_user(user.id)
            points = user_data.get("points", 0) + 50
            db.update_user(user.id, points=points)
            await update.message.reply_text(
                f"🎉 **مبروك!** لقد خمنت الرقم الصحيح ({game.number})!\n"
                f"✨ ربحت 50 نقطة إضافية!\n"
                f"📊 نقاطك الحالية: {points}\n\n"
                f"🔄 استخدم /game للعب مجدداً."
            )
            context.user_data.pop('guess_game', None)
        else:
            await update.message.reply_text(
                f"{message}\n"
                f"🎯 المحاولات المتبقية: {game.remaining_attempts()}\n"
                f"📝 أرسل تخميناً آخر:"
            )
            if result == "lose":
                await update.message.reply_text(
                    f"😞 **انتهت المحاولات!** الرقم الصحيح كان: {game.number}\n"
                    f"🔄 استخدم /game للعب مجدداً."
                )
                context.user_data.pop('guess_game', None)
    except ValueError:
        await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح بين 1 و 100.")

# ========== ربط المطابقة (Matchmaking) ==========
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """طلب البحث عن خصم للعب"""
    query = update.callback_query
    user = query.from_user
    
    # إضافة المستخدم لقائمة الانتظار
    match_id = await matchmaking.add_player(user.id)
    if match_id:
        # تم العثور على خصم
        opponent_id = matchmaking.get_opponent(user.id)
        if opponent_id:
            await query.edit_message_text(
                f"✅ **تم العثور على خصم!**\n"
                f"👤 أنت: {user.first_name}\n"
                f"👤 الخصم: {db.get_user(opponent_id)['first_name']}\n\n"
                f"🎮 اضغط على 'ابدأ' لبدء المباراة.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 ابدأ المباراة", callback_data=f"match_start_{match_id}")]
                ])
            )
            # إشعار الخصم
            await context.bot.send_message(
                opponent_id,
                f"✅ **تم العثور على خصم!**\n"
                f"👤 أنت: {db.get_user(opponent_id)['first_name']}\n"
                f"👤 الخصم: {user.first_name}\n\n"
                f"🎮 اضغط على 'ابدأ' لبدء المباراة.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 ابدأ المباراة", callback_data=f"match_start_{match_id}")]
                ])
            )
    else:
        # في انتظار خصم
        await query.edit_message_text(
            f"⏳ **جاري البحث عن خصم...**\n"
            f"👤 أنت في قائمة الانتظار.\n"
            f"🔄 سيتم إعلامك عند العثور على خصم.\n\n"
            f"❌ اضغط 'إلغاء' لإلغاء البحث.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="match_cancel")]
            ])
        )

async def cancel_matchmaking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء البحث عن خصم"""
    query = update.callback_query
    user = query.from_user
    matchmaking.remove_player(user.id)
    await query.edit_message_text("❌ تم إلغاء البحث عن خصم.")

async def start_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء المباراة بعد العثور على خصم"""
    query = update.callback_query
    user = query.from_user
    match_id = query.data.split("_")[2]
    
    # الحصول على معلومات المباراة
    match = matchmaking.get_match(match_id)
    if not match:
        await query.answer("❌ انتهت صلاحية المباراة.")
        return
    
    opponent_id = match["opponent"]
    await query.edit_message_text(
        f"🎮 **المباراة بدأت!**\n\n"
        f"👤 أنت: {user.first_name}\n"
        f"👤 الخصم: {db.get_user(opponent_id)['first_name']}\n\n"
        f"⚔️ اختر حركتك:",
        reply_markup=keyboards.game_play_buttons()
    )
    
    # إعلام الخصم ببدء المباراة
    await context.bot.send_message(
        opponent_id,
        f"🎮 **المباراة بدأت!**\n\n"
        f"👤 أنت: {db.get_user(opponent_id)['first_name']}\n"
        f"👤 الخصم: {user.first_name}\n\n"
        f"⚔️ اختر حركتك:",
        reply_markup=keyboards.game_play_buttons()
    )
