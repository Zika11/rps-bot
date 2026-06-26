import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import config.settings as settings

def setup_logging():
    """إعداد نظام Logging متقدم"""
    # إنشاء مجلد logs إذا مش موجود
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # إعداد الـ Root Logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

    # تنسيق الرسائل
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # معالج للملفات (تدوير تلقائي)
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10_000_000,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # معالج للكونسول
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # منع الـ propagation (تجنب التكرار)
    logger.propagate = False

    return logger

# Logger جاهز للاستخدام
logger = setup_logging()
