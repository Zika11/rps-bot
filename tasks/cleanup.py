import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)

async def run_cleanup():
    """
    مهمة خلفية: تنظيف الألعاب العالقة والمباريات المعلقة كل دقيقة.
    """
    while True:
        await asyncio.sleep(60)
        try:
            conn = sqlite3.connect(config.DB_NAME)
            cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
            
            # حذف الألعاب النشطة التي مضى عليها أكثر من 5 دقائق
            conn.execute("DELETE FROM active_games WHERE created_at < ?", (cutoff,))
            
            # حذف المباريات المعلقة القديمة فقط (منذ أكثر من 5 دقائق)
            try:
                conn.execute("DELETE FROM pending_matches WHERE created_at < ?", (cutoff,))
            except sqlite3.OperationalError:
                # لو العمود مش موجود (نسخة قديمة)، نضيفه أولاً
                try:
                    conn.execute("ALTER TABLE pending_matches ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                    conn.commit()
                    # ثم نحذف القديمة
                    conn.execute("DELETE FROM pending_matches WHERE created_at < ?", (cutoff,))
                except:
                    # لو مشتغلتش، نحذف الكل (حل أخير)
                    logger.warning("⚠️ pending_matches لا يحتوي على created_at، حذف الكل")
                    conn.execute("DELETE FROM pending_matches")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطأ في تنظيف الألعاب: {e}")
