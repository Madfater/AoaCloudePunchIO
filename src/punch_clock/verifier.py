"""
結果驗證模組
負責驗證打卡操作的結果
"""

import asyncio
from typing import Optional
from playwright.async_api import Page
from loguru import logger

from src.models import PunchAction


class ResultVerifier:
    """結果驗證器"""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def verify_punch_result(self, action: PunchAction, timeout: int = 10000) -> dict:
        """驗證打卡操作結果"""
        try:
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            logger.info(f"🔍 驗證 {action_name} 操作結果...")
            
            # 成功和失敗指示器
            success_indicators = [
                'text="打卡成功"',
                'text="簽到成功"',
                'text="簽退成功"',
                '.success-message',
                'ion-toast[color="success"]',
                '.alert-success'
            ]
            
            error_indicators = [
                'text="打卡失敗"',
                'text="簽到失敗"',
                'text="簽退失敗"',
                '.error-message',
                'ion-toast[color="danger"]',
                '.alert-danger'
            ]
            
            
            # 等待成功或失敗指示器出現
            wait_time = timeout / 1000
            check_interval = 0.5
            elapsed_time = 0.0
            
            while elapsed_time < wait_time:
                # 檢查成功指示器
                for indicator in success_indicators:
                    result = await self._check_indicator(indicator, True, action_name)
                    if result:
                        return result
                
                # 檢查失敗指示器
                for indicator in error_indicators:
                    result = await self._check_indicator(indicator, False, action_name)
                    if result:
                        return result
                
                # 檢查一般提示訊息
                result = await self._check_toast_messages(action_name)
                if result:
                    return result
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
            
            # 如果沒有明確指示器，嘗試通過按鈕狀態判斷
            logger.info("🔄 未檢測到明確結果指示器，嘗試通過按鈕狀態判斷...")
            return await self._verify_by_button_state(action, action_name)
            
        except Exception as e:
            logger.error(f"驗證 {action.value} 結果時發生錯誤: {e}")
            return {
                "success": False,
                "message": f"驗證結果時發生錯誤: {str(e)}",
                "server_response": None
            }
    
    async def _check_indicator(self, selector: str, is_success: bool, action_name: str) -> Optional[dict]:
        """檢查特定指示器"""
        try:
            element = await self.page.query_selector(selector)
            if element and await element.is_visible():
                text_content = await element.text_content()
                status = "✅" if is_success else "❌"
                logger.info(f"{status} 檢測到{'成功' if is_success else '失敗'}指示器: {text_content}")
                
                return {
                    "success": is_success,
                    "message": f"{action_name} {'成功' if is_success else '失敗'}",
                    "server_response": text_content
                }
        except Exception:
            pass
        return None
    
    async def _check_toast_messages(self, action_name: str) -> Optional[dict]:
        """檢查提示訊息"""
        try:
            toast_elements = await self.page.query_selector_all('ion-toast')
            for toast in toast_elements:
                if await toast.is_visible():
                    toast_text = await toast.text_content()
                    if toast_text and (action_name in toast_text or "打卡" in toast_text):
                        logger.info(f"📄 檢測到提示訊息: {toast_text}")
                        
                        # 根據訊息內容判斷成功或失敗
                        if "成功" in toast_text:
                            return {
                                "success": True,
                                "message": f"{action_name} 成功",
                                "server_response": toast_text
                            }
                        elif "失敗" in toast_text or "錯誤" in toast_text:
                            return {
                                "success": False,
                                "message": f"{action_name} 失敗",
                                "server_response": toast_text
                            }
                        else:
                            return {
                                "success": None,  # 未知狀態
                                "message": f"{action_name} 結果: {toast_text}",
                                "server_response": toast_text
                            }
        except Exception:
            pass
        return None
    
    async def _verify_by_button_state(self, action: PunchAction, action_name: str) -> dict:
        """通過按鈕狀態變化判斷結果"""
        try:
            from .checker import StatusChecker
            checker = StatusChecker(self.page)
            current_status = await checker.check_punch_page_status()
            
            if action == PunchAction.SIGN_IN:
                # 簽到後，簽到按鈕應該變為不可用，簽退按鈕變為可用
                if (not current_status.get('sign_in_available', True) and 
                    current_status.get('sign_out_available', False)):
                    return {
                        "success": True,
                        "message": "根據按鈕狀態判斷簽到成功",
                        "server_response": "按鈕狀態已更新"
                    }
                else:
                    return {
                        "success": False,
                        "message": "根據按鈕狀態判斷簽到可能失敗",
                        "server_response": "按鈕狀態未如預期更新"
                    }
            
            elif action == PunchAction.SIGN_OUT:
                # 簽退後，簽退按鈕應該變為不可用
                if not current_status.get('sign_out_available', True):
                    return {
                        "success": True,
                        "message": "根據按鈕狀態判斷簽退成功",
                        "server_response": "按鈕狀態已更新"
                    }
                else:
                    return {
                        "success": False,
                        "message": "根據按鈕狀態判斷簽退可能失敗",
                        "server_response": "按鈕狀態未如預期更新"
                    }
                    
        except Exception as status_error:
            logger.warning(f"無法檢查按鈕狀態: {status_error}")
        
        logger.warning(f"⚠️ {action_name} 結果驗證超時或未明確")
        return {
            "success": False,
            "message": f"{action_name} 結果驗證超時",
            "server_response": None
        }
    
    async def wait_for_page_response(self, timeout: int = 5000) -> Optional[str]:
        """等待頁面回應（任何形式的提示訊息）"""
        try:
            wait_time = timeout / 1000
            check_interval = 0.5
            elapsed_time = 0.0
            
            while elapsed_time < wait_time:
                # 檢查各種可能的回應元素
                response_selectors = [
                    'ion-toast',
                    '.success-message',
                    '.error-message',
                    '.alert',
                    '.notification'
                ]
                
                for selector in response_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            if element and await element.is_visible():
                                text = await element.text_content()
                                if text and text.strip():
                                    logger.info(f"檢測到頁面回應: {text.strip()}")
                                    return text.strip()
                    except Exception:
                        continue
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
            
            return None
            
        except Exception as e:
            logger.error(f"等待頁面回應時發生錯誤: {e}")
            return None