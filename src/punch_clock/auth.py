"""
登入處理模組
負責處理震旦HR系統的登入流程
"""

from playwright.async_api import Page
from loguru import logger

from src.models import LoginCredentials
from src.retry_handler import retry_on_error, LoginError, NetworkError, BrowserError


class AuthHandler:
    """登入處理器"""
    
    def __init__(self, page: Page):
        self.page = page
    
    @retry_on_error(max_attempts=3, base_delay=2.0, error_context="登入流程")
    async def login(self, credentials: LoginCredentials) -> bool:
        """執行登入流程"""
        try:
            logger.info("開始登入流程...")
            
            # 等待登入表單載入
            await self.page.wait_for_selector('input[name="CompId"]', timeout=10000)
            
            # 填入憑證
            await self.page.fill('input[name="CompId"]', credentials.company_id)
            await self.page.fill('input[name="UserId"]', credentials.user_id)
            await self.page.fill('input[name="Passwd"]', credentials.password)
            
            logger.info("已填入登入資訊")
            
            # 點擊登入按鈕
            await self.page.click('button:has-text("登入")')
            logger.info("已點擊登入按鈕")
            
            # 等待頁面跳轉
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            
            # 驗證登入結果
            if await self._verify_login_success():
                logger.info("登入驗證成功")
                return True
            else:
                error_msg = "登入失敗：驗證未通過"
                logger.error(error_msg)
                raise LoginError(error_msg)
                
        except LoginError:
            # LoginError 已經在上面處理了，直接重新拋出
            raise
        except Exception as e:
            logger.error(f"登入過程中發生錯誤: {e}")
            # 根據錯誤類型決定是否要重試
            if "timeout" in str(e).lower() or "network" in str(e).lower():
                raise NetworkError(f"網路錯誤: {e}")
            else:
                raise BrowserError(f"瀏覽器錯誤: {e}")
    
    async def _verify_login_success(self) -> bool:
        """驗證登入是否成功"""
        try:
            current_url = self.page.url
            base_url = "https://erpline.aoacloud.com.tw"
            
            # 檢查URL是否已跳轉且不在登入頁面
            if current_url != base_url and "login" not in current_url.lower():
                logger.info(f"登入成功，當前URL: {current_url}")
                return True
            
            # 額外檢查：是否有登入錯誤訊息
            error_selectors = [
                'text="帳號或密碼錯誤"',
                'text="登入失敗"',
                '.error-message',
                '.alert-danger'
            ]
            
            for selector in error_selectors:
                try:
                    error_element = await self.page.query_selector(selector)
                    if error_element and await error_element.is_visible():
                        error_text = await error_element.text_content()
                        logger.error(f"檢測到登入錯誤: {error_text}")
                        return False
                except Exception:
                    continue
            
            # 如果沒有明確的錯誤，但URL沒有改變，也視為失敗
            logger.warning("登入後URL未改變，可能登入失敗")
            return False
            
        except Exception as e:
            logger.error(f"驗證登入狀態時發生錯誤: {e}")
            return False
    
    async def get_login_status(self) -> dict:
        """獲取當前登入狀態資訊"""
        try:
            current_url = self.page.url
            
            # 檢查是否在登入頁面
            is_login_page = (
                current_url == "https://erpline.aoacloud.com.tw" or 
                "login" in current_url.lower()
            )
            
            # 嘗試獲取使用者資訊（如果已登入）
            user_info = None
            if not is_login_page:
                try:
                    # 尋找可能包含使用者資訊的元素
                    user_elements = await self.page.query_selector_all('.toolbar-title, .user-name, .username')
                    for element in user_elements:
                        if element and await element.is_visible():
                            text = await element.text_content()
                            if text and text.strip():
                                user_info = text.strip()
                                break
                except Exception:
                    pass
            
            return {
                "is_logged_in": not is_login_page,
                "current_url": current_url,
                "user_info": user_info,
                "login_page": is_login_page
            }
            
        except Exception as e:
            logger.error(f"獲取登入狀態失敗: {e}")
            return {
                "is_logged_in": False,
                "current_url": self.page.url if self.page else "",
                "user_info": None,
                "login_page": True,
                "error": str(e)
            }
    
    async def logout(self) -> bool:
        """執行登出操作（如果支援）"""
        try:
            # 尋找登出按鈕或連結
            logout_selectors = [
                'button:has-text("登出")',
                'a:has-text("登出")',
                'button:has-text("Logout")',
                'a:has-text("Logout")',
                '.logout-btn',
                '#logout'
            ]
            
            for selector in logout_selectors:
                try:
                    logout_element = await self.page.query_selector(selector)
                    if logout_element and await logout_element.is_visible():
                        await logout_element.click()
                        logger.info("已點擊登出按鈕")
                        
                        # 等待跳轉到登入頁面
                        await self.page.wait_for_load_state('networkidle', timeout=10000)
                        
                        # 驗證是否回到登入頁面
                        current_url = self.page.url
                        if current_url == "https://erpline.aoacloud.com.tw" or "login" in current_url.lower():
                            logger.info("登出成功")
                            return True
                        break
                except Exception:
                    continue
            
            logger.warning("未找到登出按鈕或登出失敗")
            return False
            
        except Exception as e:
            logger.error(f"登出過程發生錯誤: {e}")
            return False