import logging
from telegram import Update
from telegram.ext import ContextTypes
import keyboards
import handlers.shop_handlers as shop_h
from bot import wheel_spin_handler, battlepass_command

logger = logging.getLogger(__name__)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار المتجر والاقتصاد"""
    query = update.callback_query
    data = query.data

    if data == "shop":
        await shop_h.shop_main(update, context)
    
    elif data == "frames_shop":
        await shop_h.frames_shop(update, context)
    
    elif data.startswith("buy_frame_"):
        await shop_h.buy_frame(update, context)
    
    elif data == "market":
        await shop_h.market_menu(update, context)
    
    elif data == "market_browse":
        await shop_h.market_browse(update, context)
    
    elif data.startswith("market_buy_"):
        await shop_h.market_buy(update, context)
    
    elif data == "market_sell":
        await shop_h.market_sell_prompt(update, context)
    
    elif data == "abilities_shop":
        await shop_h.abilities_shop(update, context)
    
    elif data.startswith("buy_ability_"):
        await shop_h.buy_ability(update, context)
    
    elif data == "shop_cards":
        await shop_h.shop_cards(update, context)
    
    elif data.startswith("buy_") and "title" not in data and "theme" not in data and "frame" not in data and "ability" not in data:
        await shop_h.buy_item(update, context)
    
    elif data == "shop_titles":
        await shop_h.shop_titles(update, context)
    
    elif data.startswith("buy_title_"):
        await shop_h.buy_title(update, context)
    
    elif data == "shop_themes":
        await shop_h.shop_themes(update, context)
    
    elif data.startswith("buy_theme_"):
        await shop_h.buy_theme(update, context)
    
    elif data == "treasure_box":
        await shop_h.treasure_box(update, context)

    # الميزات الجديدة
    elif data == "wheel":
        await query.edit_message_text("🎡 عجلة الحظ! تدوير بـ 5 جواهر.", reply_markup=keyboards.wheel_button())
    
    elif data == "wheel_spin":
        await wheel_spin_handler(update, context)
    
    elif data == "battlepass":
        await battlepass_command(update, context)
    
    elif data == "battlepass_progress":
        await battlepass_command(update, context)
    
    else:
        logger.warning(f"زر متجر غير معروف: {data}")
