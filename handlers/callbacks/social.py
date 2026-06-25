import logging
from telegram import Update
from telegram.ext import ContextTypes
import handlers.social_handlers as social_h

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الأصدقاء والعشائر"""
    data = update.callback_query.data

    # ===== الأصدقاء =====
    if data == "friends":
        await social_h.friends_menu_handler(update, context)
        return True

    elif data == "add_friend":
        await social_h.add_friend_start(update, context)
        return True

    elif data == "friend_requests":
        await social_h.friend_requests_list(update, context)
        return True

    elif data == "friend_list":
        await social_h.friend_list_display(update, context)
        return True

    elif data.startswith("accept_friend_") or data.startswith("reject_friend_"):
        await social_h.handle_friend_action(update, context)
        return True

    # ===== العشائر =====
    elif data == "clans":
        await social_h.clans_menu_handler(update, context)
        return True

    elif data == "clan_create":
        await social_h.clan_create(update, context)
        return True

    elif data == "clan_join":
        await social_h.clan_join(update, context)
        return True

    elif data == "clan_ranking":
        await social_h.clan_ranking(update, context)
        return True

    elif data == "clan_treasury":
        await social_h.clan_treasury_menu(update, context)
        return True

    elif data.startswith("treasury_view_"):
        await social_h.treasury_view(update, context)
        return True

    elif data.startswith("treasury_donate_points_"):
        await social_h.treasury_donate_points(update, context)
        return True

    elif data.startswith("treasury_donate_gems_"):
        await social_h.treasury_donate_gems(update, context)
        return True

    elif data.startswith("treasury_upgrade_"):
        await social_h.treasury_upgrade(update, context)
        return True

    elif data.startswith("do_upgrade_"):
        await social_h.do_upgrade(update, context)
        return True

    elif data == "clan_war_info":
        await social_h.clan_war_info(update, context)
        return True

    return False
