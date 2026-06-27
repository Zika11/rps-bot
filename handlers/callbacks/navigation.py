import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards
import db

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الملاحة الأساسية"""
    query = update.callback_query
    user = query.from_user
    data = query.data

    # ========== الملاحة الأساسية ==========
    if data == "back_main":
        u = db.get_user(user.id)
        points = u.get("points", 0)
        rating = db.get_user_rating(user.id) or 1000
        rank = "غير مصنف"
        for low, high, name, icon in [
            (0, 999, "برونز", "🥉"),
            (1000, 1199, "فضة", "🥈"),
            (1200, 1399, "ذهبي", "🥇"),
            (1400, 1599, "بلاتينيوم", "🔮"),
            (1600, 1799, "ماسي", "💎"),
            (1800, 9999, "أسطورة", "👑")
        ]:
            if low <= rating <= high:
                rank = f"{icon} {name}"
                break

        text = f"مرحباً {user.first_name}\n\n"
        text += f"اختر من القائمة لبدء التحدي\n"
        text += f"نقاطك: {points:,} | تصنيفك: {rank}\n\n"

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

    # ========== القوائم الجديدة ==========
    elif data == "play_now":
        await query.edit_message_text(
            "اختر وضع اللعب\nابدأ بتحديد نوع الأسئلة ثم اختر الوضع المناسب",
            reply_markup=keyboards.game_mode_menu()
        )
        return True

    elif data == "more":
        await query.edit_message_text(
            "المزيد\nخيارات إضافية:\n\nالوقت الحالي: " + datetime.now().strftime("%H:%M:%S"),
            reply_markup=keyboards.more_menu()
        )
        return True

    # ========== خيارات المزيد ==========
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

    # ========== خيارات القناة ==========
    elif data == "select_type":
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

    elif data.startswith("channel_"):
        channel_id = data.split("_")[1]
        channel_name = channel_id.upper()
        await query.edit_message_text(
            f"**خيارات القناة: {channel_name}**\n\n"
            f"نوع الأسئلة: 🔴 اختيارات\n"
            f"اللعب التلقائي: 🔴 معطل",
            reply_markup=keyboards.channel_options_menu(channel_name, "اختيارات", False)
        )
        return True

    elif data == "manage_channels":
        await query.edit_message_text(
            "📋 **إدارة القنوات**\n\n"
            "هذه الميزة قيد التطوير...",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "change_question_type":
        await query.edit_message_text(
            "🔄 **تغيير نوع الأسئلة**\n\n"
            "هذه الميزة قيد التطوير...",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "create_game_now":
        await query.edit_message_text(
            "🎮 **تم إنشاء اللعبة!**\n\n"
            "اختر حركتك:",
            reply_markup=keyboards.game_play_buttons(broadcast=True)
        )
        return True

    elif data == "enable_auto_play":
        await query.edit_message_text(
            "⚡ **تم تفعيل اللعب التلقائي!**\n\n"
            "سيتم إنشاء ألعاب تلقائياً في هذه القناة.",
            reply_markup=keyboards.back_button()
        )
        return True

    elif data == "toggle_auto_play":
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
