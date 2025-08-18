#!/usr/bin/env python3
"""
震旦HR系統自動打卡主程式（整合視覺化測試功能）
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 將src目錄加入Python路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from src.punch_clock import PunchClockService
from src.config import config_manager
from src.models import PunchAction, PunchResult
from src.scheduler import scheduler_manager


def setup_logger(log_level: str = "INFO", log_file: str = None):
    """設置日誌記錄"""
    logger.remove()  # 移除默認處理器
    
    # 控制台輸出
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        colorize=True
    )
    
    # 檔案輸出（如果指定）
    if log_file:
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            rotation="1 day",
            retention="7 days"
        )


# save_test_result_json 函數已移至 PunchClockService


async def run_visual_test(args):
    """執行視覺化測試"""
    test_type = "真實打卡" if args.real_punch else "模擬"
    logger.info(f"🎯 視覺化測試模式 - {test_type}")
    
    try:
        # 載入配置
        config = config_manager.load_config()
        credentials = config_manager.get_login_credentials()
        
        # 確定打卡動作
        punch_action = None
        if args.sign_in and args.sign_out:
            logger.error("❌ 不能同時指定 --sign-in 和 --sign-out")
            return False
        elif args.sign_in:
            punch_action = PunchAction.SIGN_IN
        elif args.sign_out:
            punch_action = PunchAction.SIGN_OUT
        
        # 顯示測試參數
        logger.info("🔧 測試配置:")
        logger.info(f"   測試模式: {test_type}")
        logger.info(f"   無頭模式: {'否' if args.show_browser else '是'}")
        logger.info(f"   互動模式: {'是' if args.interactive else '否'}")
        logger.info(f"   截圖目錄: {args.screenshots_dir}")
        if punch_action:
            action_name = "簽到" if punch_action == PunchAction.SIGN_IN else "簽退"
            logger.info(f"   指定動作: {action_name}")
        if args.output_json:
            logger.info(f"   JSON輸出: {args.output_json}")
        if args.output_html:
            logger.info(f"   HTML報告: {args.output_html}")
        
        if args.real_punch:
            logger.warning("⚠️ 警告：真實打卡模式已啟用！")
            logger.info("💡 系統將詢問您確認後才會實際點擊打卡按鈕")
        
        # 直接使用 PunchClockService
        service = PunchClockService(
            headless=not args.show_browser,
            enable_screenshots=True,
            screenshots_dir=args.screenshots_dir,
            gps_config=config.gps,
            webhook_config=config.webhook,
            interactive_mode=args.interactive or args.real_punch  # 真實打卡強制開啟互動模式
        )
        
        # 執行視覺化測試
        test_result = await service.execute_punch_flow(credentials, punch_action, "visual")
        
        # 保存結果
        if args.output_json:
            success = service.save_json_report(test_result, Path(args.output_json))
            if success:
                logger.info(f"📄 JSON報告已生成: {args.output_json}")
            else:
                logger.error("❌ JSON報告生成失敗")
        
        # 生成HTML報告
        if args.output_html:
            success = service.generate_html_report(test_result, Path(args.output_html))
            if success:
                logger.info(f"📄 HTML報告已生成: {args.output_html}")
            else:
                logger.error("❌ HTML報告生成失敗")
        
        # 顯示最終結果
        logger.info("🎊 視覺化測試完成!")
        if test_result.overall_success:
            if args.real_punch:
                logger.info("✅ 真實打卡測試成功執行")
            else:
                logger.info("✅ 所有測試步驟均成功執行")
        else:
            logger.error("❌ 部分測試步驟失敗，請查看詳細報告")
        
        return test_result.overall_success
        
    except KeyboardInterrupt:
        logger.warning("⚠️  測試被使用者中斷")
        return False
    except Exception as e:
        logger.error(f"視覺化測試執行異常: {e}")
        return False


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
        
        # 確定打卡動作
        action = None
        if punch_action == "sign_in":
            action = PunchAction.SIGN_IN
        elif punch_action == "sign_out":
            action = PunchAction.SIGN_OUT
        
        # 創建打卡服務
        service = PunchClockService(
            headless=True,
            enable_screenshots=real_punch,
            gps_config=config.gps,
            webhook_config=config.webhook,
            interactive_mode=real_punch
        )
        
        # 執行打卡流程
        mode = "real" if real_punch else "simulate"
        result = await service.execute_punch_flow(credentials, action, mode)
        
        # 顯示結果
        if result.success:
            if real_punch:
                logger.info("🎉 真實打卡操作完成")
                logger.info(f"   結果: ✅ 成功 - {result.message}")
                if result.server_response:
                    logger.info(f"   系統回應: {result.server_response}")
            else:
                logger.info("🔄 模擬測試完成")
                logger.info(f"   結果: ✅ 成功 - {result.message}")
        else:
            logger.error(f"❌ 操作失敗: {result.message}")
        
        return result.success
                
    except Exception as e:
        logger.error(f"測試過程發生錯誤: {e}")
        return False


# execute_punch_operation 函數已經不再需要，由新的 PunchClockService 統一處理


async def punch_callback(action: PunchAction) -> PunchResult:
    """排程器打卡回調函數"""
    logger.info(f"排程器觸發打卡: {action.value}")
    
    try:
        # 載入配置
        config = config_manager.load_config()
        credentials = config_manager.get_login_credentials()
        
        # 創建打卡服務（排程模式直接執行真實打卡）
        service = PunchClockService(
            headless=True,
            enable_screenshots=True,
            gps_config=config.gps,
            webhook_config=config.webhook,
            interactive_mode=False,
            scheduler_mode=True  # 啟用排程器模式，直接執行真實打卡
        )
        
        # 執行真實打卡操作
        result = await service.execute_punch_flow(credentials, action, "real")
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


async def test_webhook_functionality():
    """測試 webhook 通知功能"""
    logger.info("🧪 開始測試 webhook 通知功能...")
    
    try:
        # 載入配置
        config = config_manager.load_config()
        
        # 檢查 webhook 是否已啟用
        if not config.webhook.enabled:
            logger.warning("⚠️ Webhook 功能未啟用，請在 .env 中設定 WEBHOOK_ENABLED=true")
            print("💡 要啟用 webhook 功能，請設定以下環境變數:")
            print("   WEBHOOK_ENABLED=true")
            print("   DISCORD_WEBHOOK_URL=<你的 Discord webhook URL>")
            return
        
        # 檢查是否有配置的 webhook URL
        has_webhooks = any([
            config.webhook.discord_url,
            config.webhook.slack_url,
            config.webhook.teams_url
        ])
        
        if not has_webhooks:
            logger.warning("⚠️ 未找到任何 webhook URL 配置")
            print("💡 請在 .env 中設定至少一個 webhook URL:")
            print("   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
            return
        
        logger.info("✅ Webhook 配置檢查通過")
        
        # 顯示配置資訊
        logger.info(f"📋 Webhook 配置資訊:")
        logger.info(f"   啟用狀態: {'是' if config.webhook.enabled else '否'}")
        if config.webhook.discord_url:
            logger.info(f"   Discord: 已配置")
        if config.webhook.slack_url:
            logger.info(f"   Slack: 已配置（未來支援）")
        if config.webhook.teams_url:
            logger.info(f"   Teams: 已配置（未來支援）")
        
        logger.info(f"   通知設定:")
        logger.info(f"     成功通知: {'是' if config.webhook.notify_success else '否'}")
        logger.info(f"     失敗通知: {'是' if config.webhook.notify_failure else '否'}")
        logger.info(f"     排程通知: {'是' if config.webhook.notify_scheduler else '否'}")
        logger.info(f"     錯誤通知: {'是' if config.webhook.notify_errors else '否'}")
        
        # 創建 PunchClockService 來測試 webhook
        service = PunchClockService(
            headless=True,
            enable_screenshots=False,
            webhook_config=config.webhook
        )
        
        # 執行 webhook 測試
        logger.info("🔄 執行 webhook 連線測試...")
        success = await service.test_webhook_notifications()
        
        if success:
            logger.info("🎉 Webhook 測試成功！")
            print("✅ 所有配置的 webhook 都能正常連線和發送訊息")
            
            # 發送額外的測試通知
            logger.info("📤 發送測試打卡通知...")
            await service.send_scheduler_notification(
                "測試",
                "這是一條測試訊息，用於驗證打卡系統的 webhook 通知功能正常運作。",
                {"測試時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            )
            
        else:
            logger.error("❌ Webhook 測試失敗")
            print("💥 請檢查 webhook URL 配置和網路連線")
            print("📋 常見問題:")
            print("   1. 確認 Discord webhook URL 格式正確")
            print("   2. 確認網路連線正常")
            print("   3. 確認 Discord 伺服器 webhook 仍然有效")
        
    except Exception as e:
        logger.error(f"Webhook 測試過程發生錯誤: {e}")
        print(f"💥 測試失敗: {e}")
        print("📋 請檢查配置檔案和錯誤日誌")


def main():
    """主程式入口"""
    import argparse
    
    # 解析命令行參數
    parser = argparse.ArgumentParser(
        description="🤖 震旦HR系統自動打卡工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 基本功能
  python main.py                          # 模擬測試模式
  python main.py --real-punch             # 真實打卡模式（需要確認）
  python main.py --real-punch --sign-in   # 執行真實簽到
  python main.py --real-punch --sign-out  # 執行真實簽退
  python main.py --schedule               # 啟動排程器（自動打卡）
  
  # 視覺化測試模式
  python main.py --visual                                # 基本視覺化測試
  python main.py --visual --show-browser                # 顯示瀏覽器窗口
  python main.py --visual --interactive                 # 互動模式
  python main.py --visual --output-html report.html    # 生成HTML報告
  python main.py --visual --real-punch --show-browser  # 視覺化真實打卡
  
  # Webhook 測試
  python main.py --test-webhook                          # 測試 webhook 連線
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
    
    parser.add_argument(
        '--test-webhook',
        action='store_true',
        help='測試 webhook 通知功能'
    )
    
    # 視覺化測試相關參數
    parser.add_argument(
        '--visual',
        action='store_true',
        help='啟用視覺化測試模式'
    )
    
    parser.add_argument(
        '--show-browser',
        action='store_true',
        help='顯示瀏覽器窗口（非無頭模式）'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='啟用互動模式，在關鍵步驟等待用戶確認'
    )
    
    parser.add_argument(
        '--screenshots-dir',
        default='screenshots',
        help='截圖保存目錄 (預設: screenshots)'
    )
    
    parser.add_argument(
        '--output-json',
        help='將測試結果保存為JSON檔案'
    )
    
    parser.add_argument(
        '--output-html',
        help='生成HTML視覺化測試報告'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日誌等級 (預設: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='日誌檔案路徑'
    )
    
    args = parser.parse_args()
    
    # 設置日誌（如果指定了日誌參數）
    if hasattr(args, 'log_level') and hasattr(args, 'log_file'):
        setup_logger(args.log_level, args.log_file)
    
    print("🤖 震旦HR系統自動打卡工具")
    print("=" * 40)
    
    # 檢查環境變數檔案是否存在
    if not Path(".env").exists():
        print("⚠️  未找到環境變數檔案，請建立 .env 檔案")
        print("📝 請複製 .env.example 為 .env 並填入您的資訊：")
        print("   cp .env.example .env")
        return
    
    # 檢查 webhook 測試模式
    if args.test_webhook:
        if args.visual or args.real_punch or args.sign_in or args.sign_out or args.schedule:
            print("❌ Webhook 測試模式不能與其他選項同時使用")
            return
        
        print("🧪 Webhook 通知測試模式")
        print("💡 系統將測試所有已配置的 webhook 連線")
        print()
        
        # 運行 webhook 測試
        asyncio.run(test_webhook_functionality())
        return
    
    # 檢查排程模式
    if args.schedule:
        if args.visual or args.real_punch or args.sign_in or args.sign_out:
            print("❌ 排程模式不能與其他選項同時使用")
            return
        
        print("🕐 啟動排程器模式")
        print("💡 系統將根據配置檔案自動執行打卡")
        print()
        
        # 運行排程器
        asyncio.run(run_scheduler())
        return
    
    # 檢查視覺化測試模式
    if args.visual:
        print("🎯 視覺化測試模式")
        if args.real_punch:
            print("⚠️ 真實打卡視覺化測試")
        else:
            print("🔄 模擬視覺化測試")
        print()
        
        # 運行視覺化測試
        success = asyncio.run(run_visual_test(args))
        if success:
            print("🎉 視覺化測試完成！")
        else:
            print("💥 視覺化測試失敗，請檢查日誌")
        return
    
    # 檢查視覺化參數是否在非視覺化模式下使用
    visual_only_params = [
        args.show_browser, args.interactive, args.output_json, args.output_html
    ]
    if any(visual_only_params):
        print("❌ 視覺化參數 (--show-browser, --interactive, --output-json, --output-html) 只能在 --visual 模式下使用")
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
        print("📋 如需視覺化測試，請使用: python main.py --visual --show-browser")
    else:
        print("💥 操作失敗，請檢查配置檔案和網路連線狀態")


if __name__ == "__main__":
    main()
