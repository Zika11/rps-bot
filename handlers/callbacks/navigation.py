import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import keyboards
import db
import state

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الملاحة الأساسية + الأزرار الجديدة"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    # ========== الملاحة الأساسية ==========
    if data == "back_main":
        u = db.get_user(user.id)
        points = u.get("points", 0) if u else 0
        rating = db.get_user_rating(user.id) or 1000
        rank = "غير مصنف"
        for low, high, name, icon in db.RATING_TIERS:
            if low <= rating <= high:
                rank = f"{icon} {name}"
                break
        text = f"مرحباً {user.first_name}\n\nاختر من القائمة لبدء التحدي\nنقاطك: {points:,} | تصنيفك: {rank}\n\n"
        await query.edit_message_text(text, reply_markup=keyboards.main_menu())
        return True

    elif data == "delete_message":
        await query.delete_message()
        return True

    elif data == "language":
        u = db.get_user(user.id)
        new_lang = "en" if u["language"] == "ar" else "ar"
        db.update_user(user.id, language=new_lang)
        await query.edit_message_text("تم تغيير اللغة", reply_markup=keyboards.main_menu(new_lang))
        return True

    elif data == "profile":
        from bot import me_command
        await me_command(update, context)
        return True

    # ========== القائمة الرئيسية الجديدة ==========
    elif data == "play_now":
        await query.edit_message_text(
            "اختر وضع اللعب\nابدأ بتحديد نوع الأسئلة ثم اختر الوضع المناسب",
            reply_markup=keyboards.game_mode_menu()
        )
        return True

    elif data == "more":
        await query.edit_message_text(
            "المزيد\nخيارات إضافية:",
            reply_markup=keyboards.more_menu()
        )
        return True

    elif data == "how_to_play":
        await query.edit_message_text(
            "📖 **طريقة اللعب**\n\n"
            "1. اختر وضع اللعب من القائمة.\n"
            "2. اختر نوع الأسئلة (قائمة أو سريع).\n"
            "3. اختر القناة أو أنشئ غرفة.\n"
            "4. ابدأ اللعب واختر حركتك!\n\n"
            "🔄 يمكنك إعادة اللعب في أي وقت.",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "support":
        await query.edit_message_text(
            "💬 **دعم البوت**\n\n"
            "للتواصل مع المطور:\n"
            "📱 [@Zika11](https://t.me/Zika11)\n\n"
            "للإبلاغ عن مشكلة أو اقتراح، تواصل معنا.",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "rate_bot":
        await query.edit_message_text(
            "⭐ **قيم البوت**\n\n"
            "ساعدنا في تحسين البوت بتقييمك:\n"
            "https://t.me/Zi_83bot\n\n"
            "شكراً لدعمك! 🎉",
            reply_markup=keyboards.back_button()
        )
        return True

    # ========== اختيار القناة ==========
    elif data == "select_type":
        # جلب القنوات النشطة من الحالة
        async with state.channel_settings_lock:
            channel_ids = list(state.channel_settings.keys())
        
        channels = []
        for cid in channel_ids:
            try:
                chat = await context.bot.get_chat(cid)
                channels.append({"id": str(cid), "name": chat.title or f"قناة {cid}"})
            except:
                channels.append({"id": str(cid), "name": f"قناة {cid}"})
        
        # إذا لم توجد قنوات، أضف قنوات افتراضية
        if not channels:
            channels = [
                {"id": "z", "name": "Z"},
                {"id": "be_inspired", "name": "BE INSPIRED"}
            ]
        
        await query.edit_message_text(
            "تم اختيار نوع الأسئلة:\n"
            "اختر القناة التي تريد إنشاء اللعبة فيها:\n"
            "يمكنك أيضاً إدارة القنوات من خلال الرجوع للقائمة الرئيسية.",
            reply_markup=keyboards.channel_selection_menu(channels)
        )
        return True

    elif data == "browse_sections":
        await query.edit_message_text(
            "📱 **تصفح الأقسام (سريع)**\n\n"
            "هذه الميزة قيد التطوير...",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "create_room":
        await query.edit_message_text(
            "🆕 **أنشئ غرفة**\n\n"
            "هذه الميزة قيد التطوير...",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "search_games":
        await query.edit_message_text(
            "🔍 **بحث عن ألعاب**\n\n"
            "هذه الميزة قيد التطوير...",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "search_room":
        await query.edit_message_text(
            "🔍 **بحث عن غرفة**\n\n"
            "هذه الميزة قيد التطوير...",
            reply_markup=keyboards.back_button()
        )
        return True

    # ========== خيارات القناة ==========
    elif data.startswith("channel_"):
        channel_id = data.split("_")[1]
        try:
            chat = await context.bot.get_chat(int(channel_id))
            channel_name = chat.title or f"قناة {channel_id}"
        except:
            channel_name = channel_id.upper()
        
        # جلب إعدادات القناة من الحالة
        async with state.channel_settings_lock:
            settings = state.channel_settings.get(int(channel_id), {})
        
        question_type = settings.get("question_type", "اختيارات")
        auto_play = settings.get("auto_play", False)
        
        await query.edit_message_text(
            f"**خيارات القناة: {channel_name}**\n\n"
            f"نوع الأسئلة: {'🔴 اختيارات' if question_type == 'اختيارات' else '🔵 أسئلة'}\n"
            f"اللعب التلقائي: {'🟢 مفعل' if auto_play else '🔴 معطل'}",
            reply_markup=keyboards.channel_options_menu(channel_name, question_type, auto_play)
        )
        return True

    elif data == "manage_channels":
        async with state.channel_settings_lock:
            channel_ids = list(state.channel_settings.keys())
        text = "📋 **إدارة القنوات**\n\n"
        if channel_ids:
            for cid in channel_ids:
                try:
                    chat = await context.bot.get_chat(cid)
                    text += f"- {chat.title} (ID: {cid})\n"
                except:
                    text += f"- قناة {cid}\n"
        else:
            text += "لا توجد قنوات مفعلة."
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
        return True

    elif data == "change_question_type":
        await query.edit_message_text(
            "🔄 **تغيير نوع الأسئلة**\n\n"
            "اختر النوع الجديد:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 اختيارات", callback_data="set_question_type_choices")],
                [InlineKeyboardButton("🔵 أسئلة مفتوحة", callback_data="set_question_type_open")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
            ])
        )
        return True

    elif data.startswith("set_question_type_"):
        q_type = data.split("_")[-1]
        # تخزين النوع في سياق المستخدم
        context.user_data["selected_question_type"] = q_type
        await query.edit_message_text(
            f"✅ تم اختيار نوع الأسئلة: {'🔴 اختيارات' if q_type == 'choices' else '🔵 أسئلة مفتوحة'}\n"
            "اختر القناة لتفعيل الإعداد:",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "create_game_now":
        chat_id = context.user_data.get("selected_channel_id")
        if not chat_id:
            await query.edit_message_text(
                "❌ لم يتم اختيار قناة!\n"
                "اختر قناة أولاً من قائمة القنوات.",
                reply_markup=keyboards.back_button()
            )
            return True
        
        # بدء لعبة في القناة
        await query.edit_message_text(
            "🎮 **تم إنشاء اللعبة!**\n\n"
            "اختر حركتك:",
            reply_markup=keyboards.game_play_buttons(broadcast=True)
        )
        return True

    elif data == "enable_auto_play":
        chat_id = context.user_data.get("selected_channel_id")
        if chat_id:
            async with state.channel_settings_lock:
                if chat_id not in state.channel_settings:
                    state.channel_settings[chat_id] = {}
                state.channel_settings[chat_id]["auto_play"] = True
        
        await query.edit_message_text(
            "⚡ **تم تفعيل اللعب التلقائي!**\n\n"
            "سيتم إنشاء ألعاب تلقائياً في هذه القناة.",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "toggle_auto_play":
        chat_id = context.user_data.get("selected_channel_id")
        if chat_id:
            async with state.channel_settings_lock:
                if chat_id in state.channel_settings:
                    current = state.channel_settings[chat_id].get("auto_play", False)
                    state.channel_settings[chat_id]["auto_play"] = not current
        
        await query.edit_message_text(
            "🔄 **تم تغيير حالة اللعب التلقائي!**",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "broadcast_game":
        await query.edit_message_text(
            "📢 **تم إرسال البث!**\n\n"
            "تم إرسال رسالة اللعبة إلى جميع المشتركين.",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "show_question_type":
        await query.edit_message_text(
            "📋 **نوع الأسئلة الحالي**\n\n"
            "نوع الأسئلة: 🔴 اختيارات\n"
            "يمكنك تغييره من خيارات القناة.",
            reply_markup=keyboards.back_button()
        )
        return True

    return False
