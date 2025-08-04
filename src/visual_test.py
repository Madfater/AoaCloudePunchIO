"""
視覺化測試核心模組
"""

import asyncio
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from loguru import logger

from .models import (
    LoginCredentials, 
    VisualTestResult, 
    TestStep, 
    ScreenshotInfo,
    PunchAction,
    PunchResult,
    GPSConfig
)
from .punch_clock import AoaCloudPunchClock


class VisualTestRunner:
    """視覺化測試執行器"""
    
    def __init__(self, headless: bool = False, interactive_mode: bool = False, gps_config: Optional[GPSConfig] = None):
        self.headless = headless
        self.interactive_mode = interactive_mode
        self.gps_config = gps_config or GPSConfig()  # 使用傳入的GPS配置或預設值
        self.current_test: Optional[VisualTestResult] = None
        
    def _create_test_result(self, test_name: str) -> VisualTestResult:
        """創建新的測試結果記錄"""
        return VisualTestResult(
            test_name=test_name,
            start_time=datetime.now()
        )
    
    def _add_test_step(self, step_name: str, description: str, 
                      success: bool, screenshot_path: Optional[Path] = None,
                      error_message: Optional[str] = None) -> None:
        """添加測試步驟記錄"""
        if not self.current_test:
            return
            
        step = TestStep(
            step_name=step_name,
            description=description,
            success=success,
            timestamp=datetime.now(),
            screenshot_path=screenshot_path,
            error_message=error_message
        )
        
        self.current_test.steps.append(step)
        
        # 記錄到日誌
        status = "✅" if success else "❌"
        logger.info(f"{status} {description}")
        if error_message:
            logger.error(f"   錯誤: {error_message}")
        if screenshot_path:
            logger.info(f"   截圖: {screenshot_path}")
    
    async def _wait_for_user_input(self, prompt: str) -> None:
        """在互動模式下等待用戶輸入"""
        if not self.interactive_mode:
            return
            
        print(f"\n🔍 {prompt}")
        print("   按 Enter 繼續，或輸入 'q' 退出...")
        
        try:
            user_input = input().strip().lower()
            if user_input == 'q':
                logger.info("使用者選擇退出測試")
                raise KeyboardInterrupt("使用者中斷測試")
        except KeyboardInterrupt:
            logger.info("測試被使用者中斷")
            raise
    
    def _update_screenshots(self, screenshots: List[Path]) -> None:
        """更新截圖列表"""
        current_screenshot_paths = {s.path for s in self.current_test.screenshots}
        
        for screenshot_path in screenshots:
            if screenshot_path not in current_screenshot_paths:
                screenshot_info = ScreenshotInfo(
                    path=screenshot_path,
                    step_name="auto_screenshot",
                    description=f"自動截圖: {screenshot_path.name}",
                    timestamp=datetime.now()
                )
                self.current_test.screenshots.append(screenshot_info)
    
    async def run_login_test(self, credentials: LoginCredentials) -> VisualTestResult:
        """執行登入視覺化測試"""
        self.current_test = self._create_test_result("Complete Punch Clock Test")
        
        try:
            logger.info("🚀 開始執行完整打卡系統視覺化測試")
            await self._wait_for_user_input("準備開始完整測試流程")
            
            # 創建打卡系統實例，啟用截圖功能
            async with AoaCloudPunchClock(
                headless=self.headless, 
                enable_screenshots=True,
                gps_config=self.gps_config
            ) as punch_clock:
                
                # 記錄瀏覽器初始化步驟
                self._add_test_step(
                    "browser_init", 
                    "瀏覽器初始化",
                    True
                )
                
                # 立即記錄初始截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                await self._wait_for_user_input("瀏覽器已初始化，準備執行登入")
                
                # 步驟1: 執行登入測試
                login_success = await punch_clock.login(credentials)
                
                # 記錄登入結果和截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                self._add_test_step(
                    "login_attempt",
                    "執行登入操作",
                    login_success,
                    error_message=None if login_success else "登入失敗"
                )
                
                if not login_success:
                    logger.error("登入失敗，無法繼續測試打卡功能")
                    return self.current_test
                
                await self._wait_for_user_input("登入成功，準備導航到打卡頁面")
                
                # 步驟2: 導航到打卡頁面
                navigation_success = await punch_clock.navigate_to_punch_page()
                
                # 記錄導航截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                self._add_test_step(
                    "navigate_to_punch",
                    "導航到出勤打卡頁面",
                    navigation_success,
                    error_message=None if navigation_success else "導航失敗"
                )
                
                if not navigation_success:
                    logger.error("導航到打卡頁面失敗")
                    return self.current_test
                
                await self._wait_for_user_input("已到達打卡頁面，準備檢查頁面狀態")
                
                # 步驟3: 檢查打卡頁面狀態
                page_status = await punch_clock.check_punch_page_status()
                
                # 記錄狀態檢查截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                # 修改成功條件：只要有簽到或簽退按鈕可用就算成功
                status_success = (page_status.get("sign_in_available", False) or 
                                page_status.get("sign_out_available", False)) and not page_status.get("error")
                
                self._add_test_step(
                    "check_page_status",
                    "檢查打卡頁面狀態",
                    status_success,
                    error_message=page_status.get("error") if page_status.get("error") else 
                                 ("打卡按鈕不可用" if not status_success else None)
                )
                
                if not status_success:
                    logger.error("打卡頁面狀態檢查失敗")
                    return self.current_test
                
                await self._wait_for_user_input("頁面狀態檢查完成，準備模擬簽到")
                
                # 步驟4: 模擬簽到操作
                sign_in_success = await punch_clock.simulate_punch_action("sign_in")
                
                # 記錄簽到截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                self._add_test_step(
                    "simulate_sign_in",
                    "模擬簽到操作",
                    sign_in_success,
                    error_message=None if sign_in_success else "簽到模擬失敗"
                )
                
                await self._wait_for_user_input("簽到模擬完成，準備模擬簽退")
                
                # 步驟5: 模擬簽退操作
                sign_out_success = await punch_clock.simulate_punch_action("sign_out")
                
                # 記錄簽退截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                self._add_test_step(
                    "simulate_sign_out",
                    "模擬簽退操作",
                    sign_out_success,
                    error_message=None if sign_out_success else "簽退模擬失敗"
                )
                
                await self._wait_for_user_input("完整測試流程完成，查看結果")
                
        except Exception as e:
            error_msg = f"測試執行異常: {str(e)}"
            logger.error(error_msg)
            self._add_test_step(
                "test_error",
                "測試執行異常",
                False,
                error_message=str(e)
            )
        
        finally:
            # 完成測試記錄
            self.current_test.end_time = datetime.now()
            self.current_test.overall_success = all(step.success for step in self.current_test.steps)
            
            # 顯示測試摘要
            self._print_test_summary()
            
        return self.current_test
    
    def _print_test_summary(self) -> None:
        """打印測試摘要"""
        if not self.current_test:
            return
            
        print("\n" + "=" * 60)
        print("📊 視覺化測試結果摘要")
        print("=" * 60)
        print(f"測試名稱: {self.current_test.test_name}")
        print(f"開始時間: {self.current_test.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"結束時間: {self.current_test.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.current_test.end_time else '未完成'}")
        print(f"持續時間: {self.current_test.duration:.2f} 秒" if self.current_test.duration else "N/A")
        print(f"整體結果: {'✅ 成功' if self.current_test.overall_success else '❌ 失敗'}")
        print(f"成功率: {self.current_test.success_rate:.1%}")
        print(f"截圖數量: {len(self.current_test.screenshots)}")
        
        print("\n📋 測試步驟詳情:")
        for i, step in enumerate(self.current_test.steps, 1):
            status = "✅" if step.success else "❌"
            print(f"  {i}. {status} {step.description}")
            if step.error_message:
                print(f"     錯誤: {step.error_message}")
        
        if self.current_test.screenshots:
            print("\n📸 截圖檔案:")
            for screenshot in self.current_test.screenshots:
                print(f"  • {screenshot.path}")
        
        print("=" * 60)
    
    def _image_to_base64(self, image_path: Path) -> str:
        """將圖片轉換為base64編碼"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"圖片轉換失敗 {image_path}: {e}")
            return ""
    
    def generate_html_report(self, output_path: Path, test_result: VisualTestResult) -> bool:
        """生成HTML測試報告"""
        try:
            # 使用更簡單的HTML模板，避免格式化衝突
            html_parts = [
                '<!DOCTYPE html>',
                '<html lang="zh-TW">',
                '<head>',
                '    <meta charset="UTF-8">',
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                '    <title>震旦HR自動打卡 - 視覺化測試報告</title>',
                '    <style>',
                '        body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }',
                '        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }',
                '        .header { text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #eee; }',
                '        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }',
                '        .summary-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }',
                '        .summary-card.success { border-left: 4px solid #28a745; }',
                '        .summary-card.error { border-left: 4px solid #dc3545; }',
                '        .summary-card .value { font-size: 2em; font-weight: bold; color: #2c3e50; }',
                '        .step { border: 1px solid #dee2e6; border-radius: 8px; margin-bottom: 15px; }',
                '        .step-header { padding: 15px 20px; background: #f8f9fa; cursor: pointer; }',
                '        .step-header.success { border-left: 4px solid #28a745; }',
                '        .step-header.error { border-left: 4px solid #dc3545; }',
                '        .step-content { padding: 20px; display: none; }',
                '        .step-content.show { display: block; }',
                '        .screenshot { max-width: 100%; border: 1px solid #dee2e6; border-radius: 4px; margin: 10px 0; }',
                '        .status-badge { padding: 4px 12px; border-radius: 4px; color: white; font-size: 0.9em; font-weight: bold; }',
                '        .status-success { background-color: #28a745; }',
                '        .status-error { background-color: #dc3545; }',
                '        .screenshots-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 30px; }',
                '        .screenshot-card { border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; }',
                '        .screenshot-card img { width: 100%; height: auto; }',
                '        .screenshot-info { padding: 15px; background: #f8f9fa; }',
                '    </style>',
                '    <script>',
                '        function toggleStep(element) {',
                '            const content = element.nextElementSibling;',
                '            content.classList.toggle("show");',
                '        }',
                '    </script>',
                '</head>',
                '<body>',
                '    <div class="container">',
                '        <div class="header">',
                '            <h1>🤖 震旦HR自動打卡 - 視覺化測試報告</h1>',
                '            <p>測試時間: ' + test_result.start_time.strftime('%Y-%m-%d %H:%M:%S') + ' - ' + (test_result.end_time.strftime('%Y-%m-%d %H:%M:%S') if test_result.end_time else '進行中') + '</p>',
                '        </div>',
                '        <div class="summary">',
                '            <div class="summary-card ' + ('success' if test_result.overall_success else 'error') + '">',
                '                <h3>整體結果</h3>',
                '                <div class="value">' + ('✅ 成功' if test_result.overall_success else '❌ 失敗') + '</div>',
                '            </div>',
                '            <div class="summary-card">',
                '                <h3>執行時間</h3>',
                '                <div class="value">' + ('{:.2f}秒'.format(test_result.duration) if test_result.duration else 'N/A') + '</div>',
                '            </div>',
                '            <div class="summary-card ' + ('success' if test_result.success_rate >= 0.8 else 'error') + '">',
                '                <h3>成功率</h3>',
                '                <div class="value">' + '{:.1%}'.format(test_result.success_rate) + '</div>',
                '            </div>',
                '            <div class="summary-card">',
                '                <h3>截圖數量</h3>',
                '                <div class="value">' + str(len(test_result.screenshots)) + '</div>',
                '            </div>',
                '        </div>',
                '        <div class="steps">',
                '            <h2>📋 測試步驟詳情</h2>'
            ]
            
            # 生成步驟HTML
            for i, step in enumerate(test_result.steps, 1):
                status_class = "success" if step.success else "error"
                status_text = "成功" if step.success else "失敗"
                status_badge_class = "status-success" if step.success else "status-error"
                
                screenshot_html = ""
                if step.screenshot_path and step.screenshot_path.exists():
                    img_base64 = self._image_to_base64(step.screenshot_path)
                    if img_base64:
                        screenshot_html = '<img src="data:image/png;base64,' + img_base64 + '" class="screenshot" alt="步驟截圖">'
                
                error_html = ""
                if step.error_message:
                    error_html = '<p><strong>錯誤訊息:</strong> ' + step.error_message + '</p>'
                
                html_parts.extend([
                    '            <div class="step">',
                    '                <div class="step-header ' + status_class + '" onclick="toggleStep(this)">',
                    '                    <div>',
                    '                        <strong>' + str(i) + '. ' + step.description + '</strong>',
                    '                        <small style="color: #6c757d; margin-left: 10px;">' + step.timestamp.strftime('%H:%M:%S') + '</small>',
                    '                    </div>',
                    '                    <span class="status-badge ' + status_badge_class + '">' + status_text + '</span>',
                    '                </div>',
                    '                <div class="step-content">',
                    '                    <p><strong>步驟名稱:</strong> ' + step.step_name + '</p>',
                    '                    ' + error_html,
                    '                    ' + screenshot_html,
                    '                </div>',
                    '            </div>'
                ])
            
            html_parts.extend([
                '        </div>',
                '        <div class="screenshots-section">',
                '            <h2>📸 截圖預覽</h2>',
                '            <div class="screenshots-grid">'
            ])
            
            # 生成截圖HTML
            for screenshot in test_result.screenshots:
                if screenshot.path.exists():
                    img_base64 = self._image_to_base64(screenshot.path)
                    if img_base64:
                        html_parts.extend([
                            '                <div class="screenshot-card">',
                            '                    <img src="data:image/png;base64,' + img_base64 + '" alt="' + screenshot.description + '">',
                            '                    <div class="screenshot-info">',
                            '                        <strong>' + screenshot.description + '</strong><br>',
                            '                        <small>' + screenshot.timestamp.strftime('%H:%M:%S') + '</small>',
                            '                    </div>',
                            '                </div>'
                        ])
            
            html_parts.extend([
                '            </div>',
                '        </div>',
                '    </div>',
                '</body>',
                '</html>'
            ])
            
            # 組合HTML內容
            html_content = '\n'.join(html_parts)
            
            # 寫入檔案
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML測試報告已生成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成HTML報告失敗: {e}")
            return False

    async def run_real_punch_test(self, credentials: LoginCredentials, 
                                 punch_action: Optional[PunchAction] = None) -> VisualTestResult:
        """執行真實打卡視覺化測試
        
        Args:
            credentials: 登入憑證
            punch_action: 指定要執行的打卡動作，None表示測試所有可用動作
        """
        test_name = f"Real Punch Test - {punch_action.value if punch_action else 'All Actions'}"
        self.current_test = self._create_test_result(test_name)
        
        try:
            logger.info("🚀 開始執行真實打卡視覺化測試")
            logger.warning("⚠️ 警告：這將執行真實的打卡操作！")
            
            await self._wait_for_user_input("準備開始真實打卡測試（將實際點擊按鈕）")
            
            # 創建打卡系統實例，啟用截圖功能
            async with AoaCloudPunchClock(
                headless=self.headless, 
                enable_screenshots=True,
                gps_config=self.gps_config
            ) as punch_clock:
                
                # 設定交互式模式
                punch_clock.set_interactive_mode(True)
                
                # 記錄瀏覽器初始化步驟
                self._add_test_step(
                    "browser_init", 
                    "瀏覽器初始化",
                    True
                )
                
                # 立即記錄初始截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                await self._wait_for_user_input("瀏覽器已初始化，準備執行登入")
                
                # 步驟1: 執行登入測試
                login_success = await punch_clock.login(credentials)
                
                # 記錄登入結果和截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                self._add_test_step(
                    "login_attempt",
                    "執行登入操作",
                    login_success,
                    error_message=None if login_success else "登入失敗"
                )
                
                if not login_success:
                    logger.error("登入失敗，無法繼續測試真實打卡")
                    return self.current_test
                
                await self._wait_for_user_input("登入成功，準備導航到打卡頁面")
                
                # 步驟2: 導航到打卡頁面
                navigation_success = await punch_clock.navigate_to_punch_page()
                
                # 記錄導航截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                self._add_test_step(
                    "navigate_to_punch",
                    "導航到出勤打卡頁面",
                    navigation_success,
                    error_message=None if navigation_success else "導航失敗"
                )
                
                if not navigation_success:
                    logger.error("導航到打卡頁面失敗")
                    return self.current_test
                
                await self._wait_for_user_input("已到達打卡頁面，準備檢查頁面狀態")
                
                # 步驟3: 檢查打卡頁面狀態
                page_status = await punch_clock.check_punch_page_status()
                
                # 記錄狀態檢查截圖
                screenshots = punch_clock.get_screenshots_taken()
                self._update_screenshots(screenshots)
                
                # 檢查成功條件
                status_success = (page_status.get("sign_in_available", False) or 
                                page_status.get("sign_out_available", False)) and not page_status.get("error")
                
                self._add_test_step(
                    "check_page_status",
                    "檢查打卡頁面狀態",
                    status_success,
                    error_message=page_status.get("error") if page_status.get("error") else 
                                 ("打卡按鈕不可用" if not status_success else None)
                )
                
                if not status_success:
                    logger.error("打卡頁面狀態檢查失敗")
                    return self.current_test
                
                # 步驟4: 執行真實打卡操作
                if punch_action:
                    # 執行指定的打卡動作
                    await self._execute_real_punch_action(punch_clock, punch_action, page_status)
                else:
                    # 測試所有可用的打卡動作
                    if page_status.get('sign_in_available'):
                        await self._execute_real_punch_action(punch_clock, PunchAction.SIGN_IN, page_status)
                    
                    if page_status.get('sign_out_available'):
                        await self._execute_real_punch_action(punch_clock, PunchAction.SIGN_OUT, page_status)
                
                await self._wait_for_user_input("真實打卡測試完成，查看結果")
                
        except Exception as e:
            error_msg = f"真實打卡測試執行異常: {str(e)}"
            logger.error(error_msg)
            self._add_test_step(
                "test_error",
                "測試執行異常",
                False,
                error_message=str(e)
            )
        
        finally:
            # 完成測試記錄
            self.current_test.end_time = datetime.now()
            self.current_test.overall_success = all(step.success for step in self.current_test.steps)
            
            # 顯示測試摘要
            self._print_test_summary()
            
        return self.current_test

    async def _execute_real_punch_action(self, punch_clock: AoaCloudPunchClock, 
                                       action: PunchAction, page_status: dict) -> None:
        """執行單個真實打卡動作"""
        action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
        available_key = 'sign_in_available' if action == PunchAction.SIGN_IN else 'sign_out_available'
        
        if not page_status.get(available_key, False):
            logger.warning(f"⚠️ {action_name} 按鈕不可用，跳過測試")
            self._add_test_step(
                f"skip_{action.value}",
                f"跳過{action_name}操作（按鈕不可用）",
                True
            )
            return
        
        await self._wait_for_user_input(f"準備執行真實{action_name}操作")
        
        try:
            # 執行真實打卡操作
            logger.info(f"🎯 準備執行真實 {action_name} 操作...")
            
            # 等待用戶確認
            confirm = await punch_clock.wait_for_punch_confirmation(action)
            result = await punch_clock.execute_real_punch_action(action, confirm=confirm)
            
            # 記錄操作結果和截圖
            screenshots = punch_clock.get_screenshots_taken()
            self._update_screenshots(screenshots)
            
            # 添加測試步驟記錄
            step_name = f"real_{action.value}"
            if result.is_simulation:
                description = f"模擬{action_name}操作（用戶取消真實操作）"
                success = result.success
                error_message = None if result.success else result.message
            else:
                description = f"真實{action_name}操作"
                success = result.success
                error_message = None if result.success else result.message
                
                # 如果是真實操作，添加額外的成功/失敗信息
                if result.success:
                    logger.info(f"🎉 真實{action_name}成功執行！")
                    if result.server_response:
                        logger.info(f"   系統回應: {result.server_response}")
                else:
                    logger.error(f"❌ 真實{action_name}執行失敗")
                    if result.server_response:
                        logger.error(f"   系統回應: {result.server_response}")
            
            self._add_test_step(
                step_name,
                description,
                success,
                screenshot_path=result.screenshot_path,
                error_message=error_message
            )
            
        except Exception as e:
            error_msg = f"執行真實{action_name}時發生異常: {str(e)}"
            logger.error(error_msg)
            self._add_test_step(
                f"error_{action.value}",
                f"真實{action_name}操作異常",
                False,
                error_message=str(e)
            )