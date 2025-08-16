"""
頁面導航模組
負責處理頁面導航和GPS定位
"""

import asyncio
from playwright.async_api import Page
from loguru import logger

from src.retry_handler import retry_on_error, NavigationError


class NavigationHandler:
    """頁面導航處理器"""
    
    def __init__(self, page: Page):
        self.page = page
    
    @retry_on_error(max_attempts=3, base_delay=1.5, error_context="導航到打卡頁面")
    async def navigate_to_punch_page(self) -> bool:
        """導航到出勤打卡頁面"""
        try:
            logger.info("準備導航到出勤打卡頁面...")
            
            # 等待主頁面載入完成
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # 尋找並點擊出勤打卡圖示
            if not await self._click_punch_card_icon():
                raise NavigationError("無法找到或點擊出勤打卡圖示")
            
            # 等待打卡頁面基本載入
            await self.page.wait_for_load_state('domcontentloaded', timeout=15000)
            
            # 驗證是否成功到達打卡頁面
            if not await self._verify_punch_page():
                raise NavigationError("無法確認是否成功導航到打卡頁面")
            
            # 處理GPS定位和地圖載入
            await self._handle_gps_loading()
            
            # 等待loading完成
            await self._wait_for_loading_complete()
            
            logger.info("成功導航到打卡頁面")
            return True
            
        except NavigationError:
            raise
        except Exception as e:
            logger.error(f"導航過程中發生錯誤: {e}")
            raise NavigationError(f"導航失敗: {e}")
    
    async def _click_punch_card_icon(self) -> bool:
        """尋找並點擊出勤打卡圖示"""
        try:
            # 主要選擇器
            punch_card_selector = 'ion-col:has(p:text("出勤打卡"))'
            
            # 嘗試主要選擇器
            try:
                await self.page.wait_for_selector(punch_card_selector, timeout=10000)
                logger.info("找到出勤打卡圖示")
            except Exception:
                # 如果找不到，嘗試替代選擇器
                alternative_selector = 'ion-col:has(img[src*="home_01"])'
                await self.page.wait_for_selector(alternative_selector, timeout=5000)
                punch_card_selector = alternative_selector
                logger.info("使用替代選擇器找到出勤打卡圖示")
            
            # 點擊出勤打卡圖示
            await self.page.click(punch_card_selector)
            logger.info("已點擊出勤打卡圖示")
            return True
            
        except Exception as e:
            logger.error(f"點擊出勤打卡圖示失敗: {e}")
            return False
    
    async def _verify_punch_page(self) -> bool:
        """驗證是否成功到達打卡頁面"""
        try:
            # 等待頁面標題出現，確認已到達打卡頁面
            try:
                await self.page.wait_for_selector('.toolbar-title', timeout=10000)
                page_title = await self.page.text_content('.toolbar-title')
                if page_title and "打卡" in page_title:
                    logger.info("透過頁面標題確認已到達打卡頁面")
                    return True
            except Exception:
                pass
            
            # 備用驗證：查找打卡按鈕
            try:
                await self.page.wait_for_selector('button:has-text("簽到")', timeout=5000)
                logger.info("透過簽到按鈕確認已到達打卡頁面")
                return True
            except Exception:
                pass
            
            logger.warning("無法確認是否到達打卡頁面")
            return False
            
        except Exception as e:
            logger.error(f"驗證打卡頁面失敗: {e}")
            return False
    
    async def _handle_gps_loading(self) -> None:
        """處理GPS定位和地圖載入"""
        try:
            logger.info("等待GPS定位和地圖元素載入...")
            
            # 等待地圖容器出現
            try:
                await self.page.wait_for_selector('#divImap', timeout=8000)
                logger.info("地圖容器已載入")
            except Exception:
                logger.warning("地圖容器載入超時")
            
            # 主動觸發GPS定位（點擊定位按鈕）
            await self._trigger_gps_location()
            
            # 等待GPS定位完成
            await asyncio.sleep(3)
            logger.info("GPS定位等待完成")
            
        except Exception as e:
            logger.warning(f"GPS定位處理失敗，但繼續執行: {e}")
    
    async def _trigger_gps_location(self) -> None:
        """主動觸發GPS定位"""
        try:
            locate_button = await self.page.query_selector('ion-fab button[ion-fab]')
            if locate_button and await locate_button.is_visible():
                logger.info("找到定位按鈕，主動觸發GPS定位")
                await locate_button.click()
                await asyncio.sleep(2)  # 等待定位請求
                logger.info("已觸發GPS定位")
            else:
                logger.info("未找到定位按鈕")
        except Exception as e:
            logger.warning(f"無法主動觸發GPS定位: {e}")
    
    async def _wait_for_loading_complete(self) -> None:
        """等待loading spinner消失"""
        try:
            loading_selector = 'ion-loading'
            loading_element = await self.page.query_selector(loading_selector)
            if loading_element:
                logger.info("檢測到loading狀態，等待完成...")
                await self.page.wait_for_selector(loading_selector, state='detached', timeout=10000)
                logger.info("Loading完成")
            else:
                logger.info("沒有檢測到loading狀態")
        except Exception as e:
            logger.info(f"Loading等待超時或完成: {e}")
    
    async def get_current_page_info(self) -> dict:
        """獲取當前頁面資訊"""
        try:
            # 獲取基本頁面資訊
            current_url = self.page.url
            page_title = ""
            
            try:
                title_element = await self.page.query_selector('.toolbar-title')
                if title_element:
                    page_title = await title_element.text_content() or ""
            except Exception:
                pass
            
            # 檢查是否在打卡頁面
            is_punch_page = False
            if "打卡" in page_title or await self.page.query_selector('button:has-text("簽到")'):
                is_punch_page = True
            
            # 檢查GPS地圖狀態
            gps_loaded = False
            try:
                map_element = await self.page.query_selector('#divImap iframe')
                if map_element:
                    gps_loaded = True
            except Exception:
                pass
            
            return {
                "url": current_url,
                "title": page_title.strip(),
                "is_punch_page": is_punch_page,
                "gps_loaded": gps_loaded
            }
            
        except Exception as e:
            logger.error(f"獲取頁面資訊失敗: {e}")
            return {
                "url": self.page.url if self.page else "",
                "title": "",
                "is_punch_page": False,
                "gps_loaded": False,
                "error": str(e)
            }
    
    async def refresh_page(self) -> bool:
        """重新整理頁面"""
        try:
            await self.page.reload(wait_until='networkidle')
            logger.info("頁面重新整理完成")
            return True
        except Exception as e:
            logger.error(f"頁面重新整理失敗: {e}")
            return False
    
    async def go_back(self) -> bool:
        """返回上一頁"""
        try:
            await self.page.go_back(wait_until='networkidle')
            logger.info("已返回上一頁")
            return True
        except Exception as e:
            logger.error(f"返回上一頁失敗: {e}")
            return False