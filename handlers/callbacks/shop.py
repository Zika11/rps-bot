import logging
from telegram import Update
from telegram.ext import ContextTypes
import handlers.shop_handlers as shop_h

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار المتجر"""
    query = update.callback_query
    data = query.data

    # ===== القائمة الرئيسية للمتجر =====
    if data == "shop":
        await shop_h.shop_main(update, context)
        return True

    # ===== بطاقات =====
    elif data == "shop_cards":
        await shop_h.shop_cards(update, context)
        return True

    elif data.startswith("buy_") and "title" not in data and "theme" not in data and "frame" not in data and "ability" not in data:
        await shop_h.buy_item(update, context)
        return True

    # ===== الألقاب =====
    elif data == "shop_titles":
        await shop_h.shop_titles(update, context)
        return True

    elif data.startswith("buy_title_"):
        await shop_h.buy_title(update, context)
        return True

    # ===== الثيمات =====
    elif data == "shop_themes":
        await shop_h.shop_themes(update, context)
        return True

    elif data.startswith("buy_theme_"):
        await shop_h.buy_theme(update, context)
        return True

    # ===== الإطارات =====
    elif data == "frames_shop":
        await shop_h.frames_shop(update, context)
        return True

    elif data.startswith("buy_frame_"):
        await shop_h.buy_frame(update, context)
        return True

    # ===== القدرات =====
    elif data == "abilities_shop":
        await shop_h.abilities_shop(update, context)
        return True

    elif data.startswith("buy_ability_"):
        await shop_h.buy_ability(update, context)
        return True

    # ===== السوق =====
    elif data == "market":
        await shop_h.market_menu(update, context)
        return True

    elif data == "market_browse":
        await shop_h.market_browse(update, context)
        return True

    elif data.startswith("market_buy_"):
        await shop_h.market_buy(update, context)
        return True

    elif data == "market_sell":
        await shop_h.market_sell_prompt(update, context)
        return True

    # ===== صندوق الكنز =====
    elif data == "treasure_box":
        await shop_h.treasure_box(update, context)
        return True

    return False
