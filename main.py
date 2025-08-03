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


async def test_complete_flow():
    """測試完整的打卡流程"""
    try:
        # 載入配置
        credentials = config_manager.get_login_credentials()
        
        logger.info("開始測試完整打卡流程...")
        
        async with AoaCloudPunchClock(headless=True, enable_screenshots=False) as punch_clock:
            # 步驟1: 登入
            logger.info("🔐 執行登入...")
            login_success = await punch_clock.login(credentials)
            if not login_success:
                logger.error("❌ 登入失敗")
                return False
            
            logger.info("✅ 登入成功")
            
            # 步驟2: 導航到打卡頁面
            logger.info("🧭 導航到打卡頁面...")
            navigation_success = await punch_clock.navigate_to_punch_page()
            if not navigation_success:
                logger.error("❌ 導航到打卡頁面失敗")
                return False
            
            logger.info("✅ 成功到達打卡頁面")
            
            # 步驟3: 檢查頁面狀態
            logger.info("🔍 檢查打卡頁面狀態...")
            page_status = await punch_clock.check_punch_page_status()
            if page_status.get("error"):
                logger.error(f"❌ 頁面狀態檢查失敗: {page_status['error']}")
                return False
            
            logger.info("✅ 打卡頁面狀態正常")
            logger.info(f"   當前時間: {page_status.get('current_date')} {page_status.get('current_time')}")
            logger.info(f"   GPS地圖: {'✅' if page_status.get('gps_loaded') else '⚠️ 未載入'}")
            if page_status.get('location_info'):
                logger.info(f"   定位地址: {page_status.get('location_info')}")
            logger.info(f"   簽到可用: {page_status.get('sign_in_available')}")
            logger.info(f"   簽退可用: {page_status.get('sign_out_available')}")
            
            # 步驟4: 模擬打卡操作
            logger.info("🎯 模擬簽到操作...")
            sign_in_success = await punch_clock.simulate_punch_action("sign_in")
            if sign_in_success:
                logger.info("✅ 簽到模擬成功")
            else:
                logger.warning("⚠️ 簽到模擬失敗")
            
            logger.info("🌙 模擬簽退操作...")
            sign_out_success = await punch_clock.simulate_punch_action("sign_out")
            if sign_out_success:
                logger.info("✅ 簽退模擬成功")
            else:
                logger.warning("⚠️ 簽退模擬失敗")
            
            # 整體成功判斷
            overall_success = (login_success and navigation_success and 
                             not page_status.get("error") and 
                             (sign_in_success or sign_out_success))
            
            return overall_success
                
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
    
    # 執行完整流程測試
    print("🔍 執行完整打卡流程測試...")
    success = asyncio.run(test_complete_flow())
    
    if success:
        print("🎉 完整打卡流程測試成功！")
        print("💡 注意：這是模擬測試，實際打卡功能尚未實現")
        print("📋 如需視覺化測試，請使用: uv run python main_visual.py --show-browser")
    else:
        print("💥 完整流程測試失敗，請檢查配置檔案和網路連線狀態")


if __name__ == "__main__":
    main()
