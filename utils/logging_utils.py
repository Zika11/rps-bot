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

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(settings.LOG_FORMAT)

    # معالج للملفات (تدوير تلقائي)
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # معالج للكونسول
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # إضافة معالج للأخطاء فقط
    class ErrorFilter(logging.Filter):
        def filter(self, record):
            return record.levelno >= logging.ERROR
    
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"),
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    error_handler.addFilter(ErrorFilter())
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    logger.propagate = False
    return logger

# Logger جاهز للاستخدام
logger = setup_logging()

# دوال مساعدة للـ logging
def log_error(error: Exception, context: str = ""):
    """تسجيل خطأ مع السياق"""
    logger.error(f"{context}: {error.__class__.__name__}: {str(error)}", exc_info=True)

def log_info(message: str):
    logger.info(message)

def log_warning(message: str):
    logger.warning(message)

def log_debug(message: str):
    logger.debug(message)
