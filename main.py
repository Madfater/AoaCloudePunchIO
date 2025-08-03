#!/usr/bin/env python3
"""
震旦HR系統自動打卡主程式
"""

import asyncio
import sys
from pathlib import Path

# 將src目錄加入Python路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from src.punch_clock import AoaCloudPunchClock
from src.config import config_manager


async def test_login():
    """測試登入功能"""
    try:
        # 載入配置
        credentials = config_manager.get_login_credentials()
        
        logger.info("開始測試登入功能...")
        
        async with AoaCloudPunchClock(headless=True) as punch_clock:
            success = await punch_clock.login(credentials)
            if success:
                logger.info("✅ 登入測試成功！")
                return True
            else:
                logger.error("❌ 登入測試失敗")
                return False
                
    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        return False


def main():
    """主程式入口"""
    print("🤖 震旦HR系統自動打卡工具")
    print("=" * 40)
    
    # 檢查配置檔案是否存在
    if not Path("config.json").exists():
        print("⚠️  未找到配置檔案，正在建立範例配置...")
        config_manager.create_example_config()
        print("📝 已建立 config.example.json，請複製為 config.json 並填入您的資訊")
        return
    
    # 執行登入測試
    print("🔍 執行登入測試...")
    success = asyncio.run(test_login())
    
    if success:
        print("🎉 系統設置完成，可以開始使用自動打卡功能！")
    else:
        print("💥 登入測試失敗，請檢查配置檔案中的帳號密碼是否正確")


if __name__ == "__main__":
    main()
