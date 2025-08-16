"""
打卡服務主接口
提供統一的打卡流程執行接口
"""

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from loguru import logger

from src.models import LoginCredentials, PunchAction, PunchResult, GPSConfig, VisualTestResult, TestStep, ScreenshotInfo
from .browser import BrowserManager
from .auth import AuthHandler
from .navigation import NavigationHandler
from .executor import PunchExecutor
from .checker import StatusChecker
from .screenshot import ScreenshotManager


class PunchClockService:
    """打卡服務主接口"""
    
    def __init__(self, headless: bool = True, enable_screenshots: bool = False, 
                 screenshots_dir: str = "screenshots", gps_config: Optional[GPSConfig] = None,
                 interactive_mode: bool = False):
        self.headless = headless
        self.enable_screenshots = enable_screenshots
        self.screenshots_dir = screenshots_dir
        self.gps_config = gps_config or GPSConfig()
        self.interactive_mode = interactive_mode
        
        # 管理器實例（初始化時為None）
        self.browser_manager: Optional[BrowserManager] = None
        self.auth_handler: Optional[AuthHandler] = None
        self.navigation_handler: Optional[NavigationHandler] = None
        self.punch_executor: Optional[PunchExecutor] = None
        self.status_checker: Optional[StatusChecker] = None
        self.screenshot_manager: Optional[ScreenshotManager] = None
    
    async def execute_punch_flow(self, credentials: LoginCredentials, 
                                action: Optional[PunchAction] = None,
                                mode: str = "simulate") -> Union[PunchResult, VisualTestResult]:
        """統一的打卡流程執行接口
        
        Args:
            credentials: 登入憑證
            action: 指定的打卡動作，None表示測試所有可用動作
            mode: 執行模式 ("simulate", "real", "visual")
        
        Returns:
            根據模式返回 PunchResult 或 VisualTestResult
        """
        if mode == "visual":
            return await self._execute_visual_test(credentials, action)
        else:
            return await self._execute_standard_flow(credentials, action, mode == "real")
    
    async def _execute_standard_flow(self, credentials: LoginCredentials, 
                                   action: Optional[PunchAction], 
                                   real_punch: bool) -> PunchResult:
        """執行標準打卡流程"""
        start_time = datetime.now()
        
        try:
            async with self:
                # 步驟1: 登入
                logger.info("🔐 執行登入...")
                if not self.auth_handler:
                    return self._create_error_result(action, start_time, "AuthHandler 未初始化")
                login_success = await self.auth_handler.login(credentials)
                if not login_success:
                    return self._create_error_result(action, start_time, "登入失敗")
                
                # 步驟2: 導航到打卡頁面
                logger.info("🧭 導航到打卡頁面...")
                if not self.navigation_handler:
                    return self._create_error_result(action, start_time, "NavigationHandler 未初始化")
                navigation_success = await self.navigation_handler.navigate_to_punch_page()
                if not navigation_success:
                    return self._create_error_result(action, start_time, "導航到打卡頁面失敗")
                
                # 步驟3: 檢查頁面狀態
                logger.info("🔍 檢查打卡頁面狀態...")
                if not self.status_checker:
                    return self._create_error_result(action, start_time, "StatusChecker 未初始化")
                page_status = await self.status_checker.check_punch_page_status()
                if page_status.get("error"):
                    return self._create_error_result(action, start_time, f"頁面狀態檢查失敗: {page_status['error']}")
                
                # 步驟4: 執行打卡操作
                if action:
                    # 執行指定動作
                    return await self._execute_single_action(action, real_punch, page_status)
                else:
                    # 測試所有可用動作（僅模擬模式）
                    return await self._execute_available_actions(page_status, real_punch)
                
        except Exception as e:
            logger.error(f"打卡流程執行異常: {e}")
            return self._create_error_result(action, start_time, f"執行異常: {str(e)}")
    
    async def _execute_visual_test(self, credentials: LoginCredentials, 
                                 action: Optional[PunchAction]) -> VisualTestResult:
        """執行視覺化測試流程"""
        test_name = f"Visual Test - {action.value if action else 'All Actions'}"
        test_result = VisualTestResult(test_name=test_name, start_time=datetime.now())
        
        try:
            async with self:
                # 記錄瀏覽器初始化
                await self._add_test_step(test_result, "browser_init", "瀏覽器初始化", True)
                await self._wait_for_user_input("瀏覽器已初始化，準備執行登入")
                
                # 步驟1: 登入測試
                if not self.auth_handler:
                    await self._add_test_step(test_result, "auth_error", "AuthHandler 未初始化", False, "AuthHandler 未初始化")
                    return self._finalize_test_result(test_result)
                login_success = await self.auth_handler.login(credentials)
                await self._add_test_step(test_result, "login", "執行登入操作", login_success, 
                                  None if login_success else "登入失敗")
                
                if not login_success:
                    return self._finalize_test_result(test_result)
                
                await self._wait_for_user_input("登入成功，準備導航到打卡頁面")
                
                # 步驟2: 導航測試
                if not self.navigation_handler:
                    await self._add_test_step(test_result, "navigation_error", "NavigationHandler 未初始化", False, "NavigationHandler 未初始化")
                    return self._finalize_test_result(test_result)
                navigation_success = await self.navigation_handler.navigate_to_punch_page()
                await self._add_test_step(test_result, "navigation", "導航到出勤打卡頁面", navigation_success,
                                  None if navigation_success else "導航失敗")
                
                if not navigation_success:
                    return self._finalize_test_result(test_result)
                
                await self._wait_for_user_input("已到達打卡頁面，準備檢查頁面狀態")
                
                # 步驟3: 狀態檢查測試
                if not self.status_checker:
                    await self._add_test_step(test_result, "status_error", "StatusChecker 未初始化", False, "StatusChecker 未初始化")
                    return self._finalize_test_result(test_result)
                page_status = await self.status_checker.check_punch_page_status()
                status_success: bool = not page_status.get("error") and bool(
                    page_status.get("sign_in_available") or page_status.get("sign_out_available")
                )
                error_msg = page_status.get("error")
                await self._add_test_step(test_result, "status_check", "檢查打卡頁面狀態", status_success,
                                  error_msg if isinstance(error_msg, str) else None)
                
                if not status_success:
                    return self._finalize_test_result(test_result)
                
                # 步驟4: 打卡測試
                if action:
                    await self._test_single_action(test_result, action, page_status)
                else:
                    await self._test_available_actions(test_result, page_status)
                
                await self._wait_for_user_input("完整測試流程完成，查看結果")
                
        except Exception as e:
            logger.error(f"視覺化測試執行異常: {e}")
            await self._add_test_step(test_result, "test_error", "測試執行異常", False, str(e))
        
        return self._finalize_test_result(test_result)
    
    async def _execute_single_action(self, action: PunchAction, real_punch: bool, 
                                   page_status: dict) -> PunchResult:
        """執行單個打卡動作"""
        action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
        available_key = 'sign_in_available' if action == PunchAction.SIGN_IN else 'sign_out_available'
        
        if not page_status.get(available_key, False):
            logger.warning(f"⚠️ {action_name} 按鈕不可用")
            return PunchResult(
                success=False,
                action=action,
                timestamp=datetime.now(),
                message=f"{action_name} 按鈕不可用",
                is_simulation=True
            )
        
        # 設定交互式模式
        if not self.punch_executor:
            return PunchResult(
                success=False,
                action=action,
                timestamp=datetime.now(),
                message="PunchExecutor 未初始化",
                is_simulation=True
            )
        self.punch_executor.set_interactive_mode(self.interactive_mode)
        
        if real_punch:
            # 等待用戶確認
            confirm = await self.punch_executor.wait_for_punch_confirmation(action)
            return await self.punch_executor.execute_punch_action(action, True, confirm)
        else:
            # 模擬模式
            return await self.punch_executor.execute_punch_action(action, False, False)
    
    async def _execute_available_actions(self, page_status: dict, real_punch: bool) -> PunchResult:
        """執行所有可用的打卡動作（僅模擬模式）"""
        if real_punch:
            return PunchResult(
                success=False,
                action=PunchAction.SIMULATE,
                timestamp=datetime.now(),
                message="真實打卡模式必須指定具體動作",
                is_simulation=False
            )
        
        if not self.punch_executor:
            return PunchResult(
                success=False,
                action=PunchAction.SIMULATE,
                timestamp=datetime.now(),
                message="PunchExecutor 未初始化",
                is_simulation=True
            )
        
        results = []
        
        # 測試簽到
        if page_status.get('sign_in_available'):
            result = await self.punch_executor.execute_punch_action(PunchAction.SIGN_IN, False, False)
            results.append(result)
        
        # 測試簽退
        if page_status.get('sign_out_available'):
            result = await self.punch_executor.execute_punch_action(PunchAction.SIGN_OUT, False, False)
            results.append(result)
        
        if not results:
            return PunchResult(
                success=False,
                action=PunchAction.SIMULATE,
                timestamp=datetime.now(),
                message="沒有可用的打卡按鈕",
                is_simulation=True
            )
        
        # 返回綜合結果
        overall_success = all(result.success for result in results)
        action_names = [f"{'簽到' if r.action == PunchAction.SIGN_IN else '簽退'}" for r in results]
        
        return PunchResult(
            success=overall_success,
            action=PunchAction.SIMULATE,
            timestamp=datetime.now(),
            message=f"測試完成: {', '.join(action_names)}",
            is_simulation=True
        )
    
    async def _test_single_action(self, test_result: VisualTestResult, action: PunchAction, 
                                page_status: dict) -> None:
        """測試單個打卡動作"""
        action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
        available_key = 'sign_in_available' if action == PunchAction.SIGN_IN else 'sign_out_available'
        
        if not page_status.get(available_key, False):
            await self._add_test_step(test_result, f"skip_{action.value}", f"跳過{action_name}（按鈕不可用）", True)
            return
        
        await self._wait_for_user_input(f"準備模擬{action_name}操作")
        if not self.punch_executor:
            await self._add_test_step(test_result, f"error_{action.value}", f"{action_name}執行器未初始化", False, "PunchExecutor 未初始化")
            return
        result = await self.punch_executor.execute_punch_action(action, False, False)
        await self._add_test_step(test_result, f"test_{action.value}", f"模擬{action_name}操作", result.success,
                          None if result.success else result.message)
    
    async def _test_available_actions(self, test_result: VisualTestResult, page_status: dict) -> None:
        """測試所有可用的打卡動作"""
        if page_status.get('sign_in_available'):
            await self._test_single_action(test_result, PunchAction.SIGN_IN, page_status)
        
        if page_status.get('sign_out_available'):
            await self._test_single_action(test_result, PunchAction.SIGN_OUT, page_status)
    
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
    
    async def _add_test_step(self, test_result: VisualTestResult, step_name: str, description: str, 
                      success: bool, error_message: Optional[str] = None) -> None:
        """添加測試步驟記錄並自動截圖"""
        # 自動截圖（如果啟用）
        screenshot_path = None
        if self.screenshot_manager and self.screenshot_manager.is_enabled():
            screenshot_path = await self.screenshot_manager.take_screenshot(step_name, description)
        
        step = TestStep(
            step_name=step_name,
            description=description,
            success=success,
            timestamp=datetime.now(),
            screenshot_path=screenshot_path,
            error_message=error_message
        )
        test_result.steps.append(step)
        
        status = "✅" if success else "❌"
        logger.info(f"{status} {description}")
        if error_message:
            logger.error(f"   錯誤: {error_message}")
        if screenshot_path:
            logger.info(f"   截圖: {screenshot_path}")
    
    def _finalize_test_result(self, test_result: VisualTestResult) -> VisualTestResult:
        """完成測試結果記錄"""
        test_result.end_time = datetime.now()
        test_result.overall_success = all(step.success for step in test_result.steps)
        
        # 更新截圖列表
        if self.screenshot_manager:
            screenshots = self.screenshot_manager.get_screenshots_taken()
            for screenshot_path in screenshots:
                # 避免重複添加已經關聯到步驟的截圖
                existing_paths = {s.path for s in test_result.screenshots}
                if screenshot_path not in existing_paths:
                    screenshot_info = ScreenshotInfo(
                        path=screenshot_path,
                        step_name="auto_screenshot",
                        description=f"自動截圖: {screenshot_path.name}",
                        timestamp=datetime.now()
                    )
                    test_result.screenshots.append(screenshot_info)
        
        return test_result
    
    def save_json_report(self, test_result: VisualTestResult, output_path: Path) -> bool:
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
            
            logger.info(f"JSON測試報告已保存至: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON報告失敗: {e}")
            return False
    
    def _image_to_base64(self, image_path: Path) -> str:
        """將圖片轉換為base64編碼"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"圖片轉換失敗 {image_path}: {e}")
            return ""
    
    def generate_html_report(self, test_result: VisualTestResult, output_path: Path) -> bool:
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
    
    def _create_error_result(self, action: Optional[PunchAction], start_time: datetime, 
                           message: str) -> PunchResult:
        """創建錯誤結果"""
        return PunchResult(
            success=False,
            action=action or PunchAction.SIMULATE,
            timestamp=start_time,
            message=message,
            is_simulation=True
        )
    
    async def __aenter__(self):
        """異步上下文管理器進入"""
        # 初始化瀏覽器管理器
        self.browser_manager = BrowserManager(self.headless, self.gps_config)
        page = await self.browser_manager.initialize()
        
        # 初始化截圖管理器
        self.screenshot_manager = ScreenshotManager(page, self.enable_screenshots, self.screenshots_dir)
        
        # 初始化其他處理器
        self.auth_handler = AuthHandler(page)
        self.navigation_handler = NavigationHandler(page)
        self.punch_executor = PunchExecutor(page, self.interactive_mode)
        self.status_checker = StatusChecker(page)
        
        # 導航到基礎URL
        await self.browser_manager.navigate_to_base_url()
        
        # 初始截圖
        if self.screenshot_manager:
            await self.screenshot_manager.take_screenshot("page_loaded", "登入頁面載入完成")
        
        logger.info("打卡服務初始化完成")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        _ = exc_type, exc_val, exc_tb  # 忽略未使用的參數
        if self.browser_manager:
            await self.browser_manager.cleanup()
        logger.info("打卡服務已清理")