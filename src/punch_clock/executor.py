"""
打卡執行模組
負責處理真實和模擬的打卡操作
"""

import asyncio
from datetime import datetime
from playwright.async_api import Page
from loguru import logger

from src.models import PunchAction, PunchResult
from .verifier import ResultVerifier


class PunchExecutor:
    """打卡執行器"""
    
    def __init__(self, page: Page, interactive_mode: bool = False):
        self.page = page
        self.interactive_mode = interactive_mode
        self.verifier = ResultVerifier(page)
    
    async def execute_punch_action(self, action: PunchAction, real_punch: bool = False, 
                                  confirm: bool = False) -> PunchResult:
        """執行打卡動作（真實或模擬）"""
        start_time = datetime.now()
        
        if real_punch and confirm:
            return await self._execute_real_punch(action, start_time)
        else:
            return await self._execute_simulated_punch(action, start_time, not real_punch)
    
    async def _execute_real_punch(self, action: PunchAction, start_time: datetime) -> PunchResult:
        """執行真實打卡操作"""
        try:
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            logger.info(f"🎯 準備執行真實 {action_name} 操作...")
            
            # 檢查按鈕是否可用
            button_check = await self._check_button_availability(action)
            if not button_check["available"]:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=start_time,
                    message=button_check["message"],
                    is_simulation=False
                )
            
            logger.info(f"🚀 執行真實 {action_name} 操作 - 點擊按鈕")
            
            # 實際點擊按鈕
            button_text = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            button_selector = f'button:has-text("{button_text}")'
            await self.page.click(button_selector)
            
            logger.info(f"✅ 已點擊 {action_name} 按鈕，等待系統回應...")
            
            # 等待系統處理
            await asyncio.sleep(2)
            
            # 驗證打卡結果
            verification_result = await self.verifier.verify_punch_result(action)
            
            return PunchResult(
                success=verification_result["success"],
                action=action,
                timestamp=start_time,
                message=verification_result["message"],
                server_response=verification_result.get("server_response"),
                is_simulation=False
            )
            
        except Exception as e:
            logger.error(f"執行真實 {action.value} 操作失敗: {e}")
            return PunchResult(
                success=False,
                action=action,
                timestamp=start_time,
                message=f"執行時發生錯誤: {str(e)}",
                is_simulation=False
            )
    
    async def _execute_simulated_punch(self, action: PunchAction, start_time: datetime, 
                                     is_simulation: bool) -> PunchResult:
        """執行模擬打卡操作"""
        try:
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            logger.info(f"模擬 {action_name} 動作...")
            
            # 檢查按鈕是否可用
            button_check = await self._check_button_availability(action)
            if not button_check["available"]:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=start_time,
                    message=button_check["message"],
                    is_simulation=True
                )
            
            # 模擬點擊（不實際執行）
            logger.info(f"🔄 模擬 {action_name} 動作 - 實際上不會點擊按鈕")
            logger.info(f"✅ {action_name} 模擬完成 - 系統已識別到打卡功能可正常運作")
            
            return PunchResult(
                success=True,
                action=action,
                timestamp=start_time,
                message=f"模擬 {action_name} 成功" if is_simulation else "用戶取消真實操作，轉為模擬模式",
                is_simulation=True
            )
            
        except Exception as e:
            logger.error(f"模擬 {action.value} 動作失敗: {e}")
            return PunchResult(
                success=False,
                action=action,
                timestamp=start_time,
                message=f"模擬操作失敗: {str(e)}",
                is_simulation=True
            )
    
    async def _check_button_availability(self, action: PunchAction) -> dict:
        """檢查按鈕可用性"""
        try:
            button_text = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            
            # 等待按鈕出現
            button_selector = f'button:has-text("{button_text}")'
            await self.page.wait_for_selector(button_selector, timeout=10000)
            
            # 檢查按鈕狀態
            button_element = await self.page.query_selector(button_selector)
            if not button_element:
                return {
                    "available": False,
                    "message": f"找不到 {action_name} 按鈕"
                }
            
            is_visible = await button_element.is_visible()
            is_enabled = await button_element.is_enabled()
            
            logger.info(f"{action_name} 按鈕狀態 - 可見: {is_visible}, 可用: {is_enabled}")
            
            if not is_visible:
                return {
                    "available": False,
                    "message": f"{action_name} 按鈕不可見"
                }
            
            if not is_enabled:
                return {
                    "available": False,
                    "message": f"{action_name} 按鈕不可用"
                }
            
            return {
                "available": True,
                "message": f"{action_name} 按鈕可用"
            }
            
        except Exception as e:
            logger.error(f"檢查 {action.value} 按鈕可用性失敗: {e}")
            return {
                "available": False,
                "message": f"檢查按鈕時發生錯誤: {str(e)}"
            }
    
    async def wait_for_punch_confirmation(self, action: PunchAction, timeout: int = 30000) -> bool:
        """等待用戶確認執行真實打卡操作"""
        try:
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            
            logger.info(f"⚠️ 準備執行真實 {action_name} 操作")
            logger.info("🔔 這將會實際點擊打卡按鈕，請確認您要執行此操作")
            logger.info("💡 如果您只想測試功能，請使用模擬模式")
            
            # 在交互式模式下，詢問用戶確認
            if self.interactive_mode:
                try:
                    print(f"\n⚠️  警告：即將執行真實 {action_name} 操作")
                    print("這將會實際點擊震旦HR系統的打卡按鈕")
                    print("如果您不想實際打卡，請選擇 'n' 或直接按 Enter 取消")
                    
                    response = input(f"確定要執行真實 {action_name} 嗎？ (輸入 'yes' 確認，其他任何輸入都將取消): ").strip().lower()
                    
                    if response == 'yes':
                        logger.info(f"✅ 用戶確認執行真實 {action_name} 操作")
                        return True
                    else:
                        logger.info(f"❌ 用戶取消真實 {action_name} 操作")
                        return False
                        
                except Exception as input_error:
                    logger.error(f"獲取用戶輸入時發生錯誤: {input_error}")
                    return False
            
            # 非交互式模式下，預設不確認（安全機制）
            logger.warning("🛡️ 非交互式模式，預設不執行真實操作以確保安全")
            logger.info("💡 如需執行真實操作，請使用交互式模式或明確傳入 confirm=True 參數")
            return False
            
        except Exception as e:
            logger.error(f"等待用戶確認時發生錯誤: {e}")
            return False
    
    def set_interactive_mode(self, interactive: bool = True):
        """設定是否為交互式模式"""
        self.interactive_mode = interactive
        if interactive:
            logger.info("🤝 已啟用交互式模式，執行真實操作前將詢問確認")
        else:
            logger.info("🤖 已設定為非交互式模式，預設執行模擬操作")