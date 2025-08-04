#!/usr/bin/env python3
"""
震旦HR系統專門視覺化測試程式

這是獨立的視覺化測試工具，與主程式(main.py)分離：
- main.py：純粹的自動打卡主程式，只進行基本登入測試
- main_visual.py：專門的視覺化測試工具，包含截圖、報告生成等功能

提供完整的視覺化測試功能和報告生成
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 將src目錄加入Python路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from src.config import config_manager
from src.visual_test import VisualTestRunner
from src.models import PunchAction


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


def save_test_result_json(test_result, output_path: Path):
    """將測試結果保存為JSON格式"""
    try:
        # 準備可序列化的資料
        result_data = {
            "test_name": test_result.test_name,
            "start_time": test_result.start_time.isoformat(),
            "end_time": test_result.end_time.isoformat() if test_result.end_time else None,
            "duration": test_result.duration,
            "overall_success": test_result.overall_success,
            "success_rate": test_result.success_rate,
            "steps": [
                {
                    "step_name": step.step_name,
                    "description": step.description,
                    "success": step.success,
                    "timestamp": step.timestamp.isoformat(),
                    "screenshot_path": str(step.screenshot_path) if step.screenshot_path else None,
                    "error_message": step.error_message
                }
                for step in test_result.steps
            ],
            "screenshots": [
                {
                    "path": str(screenshot.path),
                    "step_name": screenshot.step_name,
                    "description": screenshot.description,
                    "timestamp": screenshot.timestamp.isoformat()
                }
                for screenshot in test_result.screenshots
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"測試結果已保存至: {output_path}")
        
    except Exception as e:
        logger.error(f"保存測試結果失敗: {e}")


async def run_comprehensive_test(args):
    """執行全面的視覺化測試"""
    test_type = "真實打卡" if args.real_punch else "模擬"
    print(f"🎯 震旦HR系統專門視覺化測試 - {test_type}模式")
    print("=" * 50)
    
    # 檢查配置檔案
    if not Path("config.json").exists():
        print("⚠️  未找到配置檔案，正在建立範例配置...")
        config_manager.create_example_config()
        print("📝 已建立 config.example.json，請複製為 config.json 並填入您的資訊")
        return False
    
    try:
        # 載入配置
        config = config_manager.load_config()
        credentials = config_manager.get_login_credentials()
        
        # 確定打卡動作
        punch_action = None
        if args.sign_in and args.sign_out:
            print("❌ 不能同時指定 --sign-in 和 --sign-out")
            return False
        elif args.sign_in:
            punch_action = PunchAction.SIGN_IN
        elif args.sign_out:
            punch_action = PunchAction.SIGN_OUT
        
        # 顯示測試參數
        print(f"🔧 測試配置:")
        print(f"   測試模式: {test_type}")
        print(f"   無頭模式: {'否' if args.show_browser else '是'}")
        print(f"   互動模式: {'是' if args.interactive else '否'}")
        print(f"   截圖目錄: {args.screenshots_dir}")
        print(f"   日誌等級: {args.log_level}")
        if punch_action:
            action_name = "簽到" if punch_action == PunchAction.SIGN_IN else "簽退"
            print(f"   指定動作: {action_name}")
        if args.output_json:
            print(f"   JSON輸出: {args.output_json}")
        if args.output_html:
            print(f"   HTML報告: {args.output_html}")
        
        if args.real_punch:
            print("\n⚠️ 警告：真實打卡模式已啟用！")
            print("💡 系統將詢問您確認後才會實際點擊打卡按鈕")
        
        print()
        
        # 創建測試執行器
        test_runner = VisualTestRunner(
            headless=not args.show_browser,
            interactive_mode=args.interactive,
            gps_config=config.gps
        )
        
        # 執行對應的測試
        if args.real_punch:
            test_result = await test_runner.run_real_punch_test(credentials, punch_action)
        else:
            test_result = await test_runner.run_login_test(credentials)
        
        # 保存結果
        if args.output_json:
            save_test_result_json(test_result, Path(args.output_json))
        
        # 生成HTML報告
        if args.output_html:
            success = test_runner.generate_html_report(Path(args.output_html), test_result)
            if success:
                print(f"📄 HTML報告已生成: {args.output_html}")
            else:
                print("❌ HTML報告生成失敗")
        
        # 顯示最終結果
        print("\n🎊 測試完成!")
        if test_result.overall_success:
            if args.real_punch:
                print("✅ 真實打卡測試成功執行")
            else:
                print("✅ 所有測試步驟均成功執行")
        else:
            print("❌ 部分測試步驟失敗，請查看詳細報告")
        
        return test_result.overall_success
        
    except KeyboardInterrupt:
        print("\n⚠️  測試被使用者中斷")
        return False
    except Exception as e:
        logger.error(f"測試執行異常: {e}")
        return False


def parse_arguments():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(
        description="🎯 震旦HR系統專門視覺化測試工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 模擬測試（預設）
  python main_visual.py                           # 基本視覺化測試
  python main_visual.py --show-browser           # 顯示瀏覽器窗口
  python main_visual.py --interactive            # 互動模式
  python main_visual.py --output-html report.html # 生成HTML報告
  
  # 真實打卡測試
  python main_visual.py --real-punch              # 真實打卡測試
  python main_visual.py --real-punch --sign-in    # 僅測試真實簽到
  python main_visual.py --real-punch --sign-out   # 僅測試真實簽退
  python main_visual.py --real-punch --show-browser --interactive  # 真實打卡+可視化
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
    
    return parser.parse_args()


def main():
    """主程式入口"""
    args = parse_arguments()
    
    # 設置日誌
    setup_logger(args.log_level, args.log_file)
    
    # 執行測試
    try:
        success = asyncio.run(run_comprehensive_test(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 再見！")
        sys.exit(130)  # SIGINT exit code


if __name__ == "__main__":
    main()