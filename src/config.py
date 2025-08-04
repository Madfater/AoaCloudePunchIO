"""
配置管理模組
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import json

from src.models import LoginCredentials, ScheduleConfig, AppConfig, GPSConfig


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._config: Optional[AppConfig] = None
        
        # 載入環境變數
        if Path(".env").exists():
            load_dotenv()
    
    def load_config(self) -> AppConfig:
        """載入配置"""
        if self._config is not None:
            return self._config
            
        config_data = {}
        
        # 嘗試從檔案載入
        if Path(self.config_file).exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        
        # 從環境變數補充/覆蓋
        if os.getenv('COMPANY_ID'):
            config_data.setdefault('login', {})['company_id'] = os.getenv('COMPANY_ID')
        if os.getenv('USER_ID'):
            config_data.setdefault('login', {})['user_id'] = os.getenv('USER_ID')
        if os.getenv('PASSWORD'):
            config_data.setdefault('login', {})['password'] = os.getenv('PASSWORD')
            
        self._config = AppConfig(**config_data)
        return self._config
    
    def get_login_credentials(self):
        """取得登入憑證"""
        config = self.load_config()
        return LoginCredentials(
            company_id=config.login.company_id,
            user_id=config.login.user_id,
            password=config.login.password
        )
    
    def create_example_config(self):
        """建立範例配置檔案"""
        example = {
            "login": {
                "company_id": "YOUR_COMPANY_ID",
                "user_id": "YOUR_USER_ID",
                "password": "YOUR_PASSWORD"
            },
            "schedule": {
                "clock_in_time": "09:00",
                "clock_out_time": "18:00",  
                "enabled": True,
                "weekdays_only": True
            },
            "gps": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "address": "台北市"
            },
            "debug": False,
            "headless": True
        }
        
        with open("config.example.json", 'w', encoding='utf-8') as f:
            json.dump(example, f, indent=2, ensure_ascii=False)


# 全域實例
config_manager = ConfigManager()