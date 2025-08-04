#!/usr/bin/env python3
"""
震旦HR系統自動打卡主程式
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 將src目錄加入Python路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from src.punch_clock import AoaCloudPunchClock
from src.config import config_manager
from src.models import PunchAction, PunchResult
from src.scheduler import scheduler_manager


async def test_complete_flow(real_punch: bool = False, punch_action: str = None):
    """測試完整的打卡流程
    
    Args:
        real_punch: 是否執行真實打卡操作
        punch_action: 指定要執行的打卡動作 ("sign_in", "sign_out", None為測試兩種)
    """
    try:
        # 載入配置
        config = config_manager.load_config()
        credentials = config_manager.get_login_credentials()
        
        logger.info("開始測試完整打卡流程...")
        logger.info(f"GPS定位設定: {config.gps.address} ({config.gps.latitude}, {config.gps.longitude})")
        if real_punch:
            logger.warning("⚠️ 真實打卡模式已啟用")
        else:
            logger.info("🔄 模擬測試模式")
        
        async with AoaCloudPunchClock(headless=True, enable_screenshots=real_punch, gps_config=config.gps) as punch_clock:
            # 設定交互式模式（如果是真實打卡）
            if real_punch:
                punch_clock.set_interactive_mode(True)
            
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
            
            # 步驟4: 執行打卡操作（真實或模擬）
            test_results = []
            
            if punch_action:
                # 執行指定的打卡動作
                if punch_action == "sign_in":
                    result = await execute_punch_operation(punch_clock, PunchAction.SIGN_IN, real_punch, page_status)
                    test_results.append(result)
                elif punch_action == "sign_out":
                    result = await execute_punch_operation(punch_clock, PunchAction.SIGN_OUT, real_punch, page_status)
                    test_results.append(result)
                else:
                    logger.error(f"❌ 不支援的打卡動作: {punch_action}")
                    return False
            else:
                # 測試兩種打卡動作
                if page_status.get('sign_in_available'):
                    result = await execute_punch_operation(punch_clock, PunchAction.SIGN_IN, real_punch, page_status)
                    test_results.append(result)
                
                if page_status.get('sign_out_available'):
                    result = await execute_punch_operation(punch_clock, PunchAction.SIGN_OUT, real_punch, page_status)
                    test_results.append(result)
                
                if not test_results:
                    logger.warning("⚠️ 沒有可用的打卡按鈕進行測試")
                    return False
            
            # 整體成功判斷
            overall_success = (login_success and navigation_success and 
                             not page_status.get("error") and 
                             any(result.success for result in test_results))
            
            # 顯示最終結果
            if real_punch and any(not result.is_simulation for result in test_results):
                logger.info("🎉 真實打卡操作完成")
                for result in test_results:
                    if not result.is_simulation:
                        status = "✅ 成功" if result.success else "❌ 失敗"
                        logger.info(f"   {result.action.value}: {status} - {result.message}")
            else:
                logger.info("🔄 模擬測試完成")
            
            return overall_success
                
    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        return False


async def execute_punch_operation(punch_clock, action: PunchAction, real_punch: bool, page_status: dict):
    """執行打卡操作（真實或模擬）"""
    action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
    available_key = 'sign_in_available' if action == PunchAction.SIGN_IN else 'sign_out_available'
    
    if not page_status.get(available_key, True):
        logger.warning(f"⚠️ {action_name} 按鈕不可用，跳過測試")
        return PunchResult(
            success=False,
            action=action,
            timestamp=datetime.now(),
            message=f"{action_name} 按鈕不可用",
            is_simulation=True
        )
    
    if real_punch:
        # 執行真實打卡操作
        logger.info(f"🎯 準備執行真實 {action_name} 操作...")
        
        # 等待用戶確認
        confirm = await punch_clock.wait_for_punch_confirmation(action)
        result = await punch_clock.execute_real_punch_action(action, confirm=confirm)
        
        if result.is_simulation:
            logger.info(f"🔄 {action_name} 以模擬模式執行")
        else:
            status = "✅ 成功" if result.success else "❌ 失敗"
            logger.info(f"🚀 真實 {action_name} 結果: {status}")
            if result.server_response:
                logger.info(f"   系統回應: {result.server_response}")
    else:
        # 執行模擬操作
        logger.info(f"🎯 模擬 {action_name} 操作...")
        simulate_success = await punch_clock.simulate_punch_action(action.value)
        
        result = PunchResult(
            success=simulate_success,
            action=action,
            timestamp=datetime.now(),
            message=f"模擬 {action_name} {'成功' if simulate_success else '失敗'}",
            is_simulation=True
        )
        
        if simulate_success:
            logger.info(f"✅ {action_name} 模擬成功")
        else:
            logger.warning(f"⚠️ {action_name} 模擬失敗")
    
    return result


async def punch_callback(action: PunchAction) -> PunchResult:
    """排程器打卡回調函數"""
    logger.info(f"排程器觸發打卡: {action.value}")
    
    try:
        # 載入配置
        config = config_manager.load_config()
        credentials = config_manager.get_login_credentials()
        
        async with AoaCloudPunchClock(headless=True, enable_screenshots=True, gps_config=config.gps) as punch_clock:
            # 登入
            login_success = await punch_clock.login(credentials)
            if not login_success:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=datetime.now(),
                    message="登入失敗",
                    is_simulation=False
                )
            
            # 導航到打卡頁面
            navigation_success = await punch_clock.navigate_to_punch_page()
            if not navigation_success:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=datetime.now(),
                    message="導航到打卡頁面失敗",
                    is_simulation=False
                )
            
            # 執行真實打卡操作（排程模式自動確認）
            result = await punch_clock.execute_real_punch_action(action, confirm=True)
            return result
            
    except Exception as e:
        logger.error(f"排程打卡過程發生錯誤: {e}")
        return PunchResult(
            success=False,
            action=action,
            timestamp=datetime.now(),
            message=f"排程打卡錯誤: {e}",
            is_simulation=False
        )


async def run_scheduler():
    """運行排程器"""
    logger.info("🕐 啟動自動打卡排程器...")
    
    try:
        # 初始化排程器
        await scheduler_manager.initialize(punch_callback)
        
        # 顯示排程狀態
        status = scheduler_manager.scheduler.get_job_status()
        if status['jobs']:
            logger.info("📅 已設定的排程任務:")
            for job in status['jobs']:
                logger.info(f"  • {job['name']}: {job['next_run']}")
        else:
            logger.warning("⚠️ 未找到任何排程任務")
            return
        
        logger.info("⏰ 排程器運行中... 按 Ctrl+C 停止")
        
        # 保持程式運行
        try:
            while True:
                await asyncio.sleep(60)  # 每分鐘檢查一次
                
                # 可以在這裡添加狀態檢查邏輯
                next_runs = scheduler_manager.scheduler.get_next_runs()
                if next_runs:
                    logger.debug(f"下次執行時間: {next_runs}")
                    
        except KeyboardInterrupt:
            logger.info("💤 收到停止信號，正在關閉排程器...")
        
    except Exception as e:
        logger.error(f"排程器運行錯誤: {e}")
    finally:
        await scheduler_manager.shutdown()
        logger.info("📴 排程器已停止")


def main():
    """主程式入口"""
    import argparse
    
    # 解析命令行參數
    parser = argparse.ArgumentParser(
        description="🤖 震旦HR系統自動打卡工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python main.py                          # 模擬測試模式
  python main.py --real-punch             # 真實打卡模式（需要確認）
  python main.py --real-punch --sign-in   # 執行真實簽到
  python main.py --real-punch --sign-out  # 執行真實簽退
  python main.py --schedule               # 啟動排程器（自動打卡）
        """
    )
    
    parser.add_argument(
        '--real-punch',
        action='store_true',
        help='啟用真實打卡模式（實際點擊按鈕）'
    )
    
    parser.add_argument(
        '--sign-in',
        action='store_true',
        help='僅執行簽到操作'
    )
    
    parser.add_argument(
        '--sign-out',
        action='store_true',
        help='僅執行簽退操作'
    )
    
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='啟動排程器模式（根據配置檔案自動打卡）'
    )
    
    args = parser.parse_args()
    
    print("🤖 震旦HR系統自動打卡工具")
    print("=" * 40)
    
    # 檢查配置檔案是否存在
    if not Path("config.json").exists():
        print("⚠️  未找到配置檔案，正在建立範例配置...")
        config_manager.create_example_config()
        print("📝 已建立 config.example.json，請複製為 config.json 並填入您的資訊")
        return
    
    # 檢查排程模式
    if args.schedule:
        if args.real_punch or args.sign_in or args.sign_out:
            print("❌ 排程模式不能與其他打卡選項同時使用")
            return
        
        print("🕐 啟動排程器模式")
        print("💡 系統將根據配置檔案自動執行打卡")
        print()
        
        # 運行排程器
        asyncio.run(run_scheduler())
        return
    
    # 確定要執行的打卡動作
    punch_action = None
    if args.sign_in and args.sign_out:
        print("❌ 不能同時指定 --sign-in 和 --sign-out")
        return
    elif args.sign_in:
        punch_action = "sign_in"
    elif args.sign_out:
        punch_action = "sign_out"
    
    # 顯示執行模式
    if args.real_punch:
        print("⚠️ 真實打卡模式已啟用")
        print("💡 系統將詢問您確認後才會實際點擊打卡按鈕")
        if punch_action:
            action_name = "簽到" if punch_action == "sign_in" else "簽退"
            print(f"🎯 將執行: {action_name}")
    else:
        print("🔄 模擬測試模式（不會實際打卡）")
        if punch_action:
            action_name = "簽到" if punch_action == "sign_in" else "簽退"
            print(f"🎯 將測試: {action_name}")
    
    print()
    
    # 執行完整流程測試
    print("🔍 執行完整打卡流程...")
    success = asyncio.run(test_complete_flow(real_punch=args.real_punch, punch_action=punch_action))
    
    if success:
        if args.real_punch:
            print("🎉 打卡操作完成！")
            print("📋 如需查看詳細過程，請使用視覺化測試工具")
        else:
            print("🎉 完整打卡流程測試成功！")
            print("💡 注意：這是模擬測試，未實際點擊按鈕")
            print("🚀 如需執行真實打卡，請使用: python main.py --real-punch")
        print("📋 如需視覺化測試，請使用: uv run python main_visual.py --show-browser")
    else:
        print("💥 操作失敗，請檢查配置檔案和網路連線狀態")


if __name__ == "__main__":
    main()
