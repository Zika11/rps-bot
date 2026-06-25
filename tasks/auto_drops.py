import asyncio
import logging
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
import state

logger = logging.getLogger(__name__)

async def run_auto_drops(app):
    """
    مهمة خلفية: إسقاط صناديق مفاجئة في القنوات النشطة كل 10 دقائق.
    """
    while True:
        await asyncio.sleep(600)  # 10 دقائق
        if random.random() < config.DROP_CHANCE:
            async with state.channel_settings_lock:
                active_channels = list(state.channel_settings.keys())
            
            for chat_id in active_channels:
                reward = random.choice(config.DROP_REWARDS)
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 افتح الصندوق!", callback_data=f"claim_drop_{reward[0]}_{reward[1]}")]
                ])
                try:
                    await app.bot.send_message(
                        chat_id,
                        "💥 صندوق مفاجئ! أول واحد يضغط يربح:",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"فشل إرسال صندوق مفاجئ للقناة {chat_id}: {e}")
