import gspread
import json
import logging
from typing import Dict, List, Optional, Any
from google.oauth2.service_account import Credentials
import config.settings as settings

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    """عميل Google Sheets لقراءة وكتابة البيانات"""
    
    _instance = None
    _client = None
    _sheet = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None and settings.GOOGLE_SHEETS_CREDS and settings.GOOGLE_SHEET_ID:
            try:
                creds_dict = json.loads(settings.GOOGLE_SHEETS_CREDS)
                scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                self._client = gspread.authorize(creds)
                self._sheet = self._client.open_by_key(settings.GOOGLE_SHEET_ID)
            except Exception as e:
                logger.error(f"Google Sheets connection failed: {e}")
                self._client = None
                self._sheet = None

    def is_connected(self) -> bool:
        return self._sheet is not None

    def get_worksheet(self, name: str):
        """الحصول على ورقة عمل بالاسم"""
        if not self.is_connected():
            return None
        try:
            return self._sheet.worksheet(name)
        except:
            return None

    def get_all_records(self, sheet_name: str) -> List[Dict]:
        """قراءة جميع السجلات من ورقة معينة"""
        ws = self.get_worksheet(sheet_name)
        if not ws:
            return []
        try:
            return ws.get_all_records()
        except:
            return []

    def get_settings(self) -> Dict[str, Any]:
        """قراءة إعدادات البوت من جدول الإعدادات"""
        records = self.get_all_records("settings")
        settings_dict = {}
        for row in records:
            key = row.get("key", "")
            value = row.get("value", "")
            settings_dict[key] = value
        return settings_dict

    def get_shop_items(self) -> List[Dict]:
        """قراءة عناصر المتجر من الجدول"""
        return self.get_all_records("shop_items")

    def get_daily_rewards(self) -> List[Dict]:
        """قراءة المكافآت اليومية من الجدول"""
        return self.get_all_records("daily_rewards")

    def get_achievements(self) -> List[Dict]:
        """قراءة الإنجازات من الجدول"""
        return self.get_all_records("achievements")

    def update_cell(self, sheet_name: str, row: int, col: int, value: Any) -> bool:
        """تحديث خلية معينة"""
        ws = self.get_worksheet(sheet_name)
        if not ws:
            return False
        try:
            ws.update_cell(row, col, value)
            return True
        except:
            return False

# مثيل واحد للاستخدام
gsheets = GoogleSheetsClient()
