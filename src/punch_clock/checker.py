"""
狀態檢查模組
負責檢查打卡頁面狀態和按鈕可用性
"""

import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import Page
from loguru import logger


class StatusChecker:
    """狀態檢查器"""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def check_punch_page_status(self) -> dict:
        """檢查打卡頁面狀態和資訊"""
        try:
            logger.info("檢查打卡頁面狀態...")
            
            # 首先等待頁面穩定
            await self._wait_for_stable_page()
            
            status_info: Dict[str, Any] = {
                "current_time": None,
                "current_date": None,
                "location_info": None,
                "sign_in_available": False,
                "sign_out_available": False,
                "page_loaded": False,
                "gps_loaded": False
            }
            
            # 檢查頁面載入狀態
            status_info["page_loaded"] = await self._check_page_loaded()
            
            # 檢查GPS地圖載入狀態
            status_info["gps_loaded"] = await self._check_gps_loaded()
            
            # 獲取時間和日期資訊
            time_info = await self._get_time_info()
            status_info.update(time_info)
            
            # 獲取地址資訊
            status_info["location_info"] = await self._get_location_info()
            
            # 檢查按鈕可用性
            button_status = await self._check_buttons_availability()
            status_info.update(button_status)
            
            # 記錄狀態資訊
            self._log_status_summary(status_info)
            
            return status_info
            
        except Exception as e:
            logger.error(f"檢查打卡頁面狀態失敗: {e}")
            return {"error": str(e)}
    
    async def _wait_for_stable_page(self, timeout: int = 10000) -> bool:
        """等待頁面穩定（處理GPS定位和loading狀態）"""
        try:
            logger.info("等待頁面穩定...")
            
            max_wait_time = timeout / 1000
            wait_interval = 0.5
            elapsed_time = 0.0
            
            while elapsed_time < max_wait_time:
                # 檢查是否有loading元素
                loading_element = await self.page.query_selector('ion-loading')
                if not loading_element:
                    spinner_element = await self.page.query_selector('.loading-spinner')
                    if not spinner_element:
                        logger.info("頁面載入狀態穩定")
                        break
                
                logger.debug(f"檢測到載入中...等待 {wait_interval} 秒")
                await asyncio.sleep(wait_interval)
                elapsed_time += wait_interval
            
            if elapsed_time >= max_wait_time:
                logger.warning("等待頁面穩定超時，但繼續執行")
            
            # 額外等待GPS定位完成
            await asyncio.sleep(2)
            return True
            
        except Exception as e:
            logger.warning(f"等待頁面穩定時發生錯誤: {e}")
            return False
    
    async def _check_page_loaded(self) -> bool:
        """檢查頁面是否載入完成"""
        try:
            # 首先檢查頁面標題
            page_title = await self.page.text_content('.toolbar-title')
            if page_title and "打卡" in page_title:
                logger.info("打卡頁面載入確認（透過標題）")
                return True
        except Exception:
            pass
        
        # 備用方案：透過簽到按鈕確認
        try:
            sign_in_button = await self.page.query_selector('button:has-text("簽到")')
            if sign_in_button and await sign_in_button.is_visible():
                logger.info("透過簽到按鈕確認頁面載入")
                return True
        except Exception:
            pass
        
        logger.warning("無法確認頁面載入狀態")
        return False
    
    async def _check_gps_loaded(self) -> bool:
        """檢查GPS地圖是否載入"""
        try:
            map_element = await self.page.query_selector('#divImap iframe')
            if map_element:
                logger.info("GPS地圖載入確認")
                return True
        except Exception:
            pass
        
        logger.warning("GPS地圖載入狀態未知")
        return False
    
    async def _get_time_info(self) -> dict:
        """獲取當前時間和日期"""
        try:
            date_elements = await self.page.query_selector_all('.date')
            if len(date_elements) >= 2:
                current_date = await date_elements[0].text_content()
                current_time = await date_elements[1].text_content()
                logger.info(f"獲取時間資訊: {current_date} {current_time}")
                return {
                    "current_date": current_date,
                    "current_time": current_time
                }
        except Exception as e:
            logger.warning(f"無法獲取時間資訊: {e}")
        
        return {"current_date": None, "current_time": None}
    
    async def _get_location_info(self) -> Optional[str]:
        """獲取地址資訊"""
        try:
            address_input = await self.page.query_selector('#addressDiv ion-input input')
            if address_input:
                address_value = await address_input.get_attribute('value')
                if address_value:
                    logger.info(f"GPS地址資訊: {address_value}")
                    return address_value
        except Exception:
            pass
        
        return None
    
    async def _check_buttons_availability(self) -> dict:
        """檢查簽到/簽退按鈕可用性"""
        button_status = {
            "sign_in_available": False,
            "sign_out_available": False
        }
        
        # 檢查簽到按鈕
        try:
            sign_in_button = await self.page.query_selector('button:has-text("簽到")')
            if sign_in_button:
                is_visible = await sign_in_button.is_visible()
                is_enabled = await sign_in_button.is_enabled()
                button_status["sign_in_available"] = is_visible and is_enabled
                logger.info(f"簽到按鈕狀態: 可見={is_visible}, 可用={is_enabled}")
        except Exception as e:
            logger.warning(f"無法檢查簽到按鈕狀態: {e}")
        
        # 檢查簽退按鈕
        try:
            sign_out_button = await self.page.query_selector('button:has-text("簽退")')
            if sign_out_button:
                is_visible = await sign_out_button.is_visible()
                is_enabled = await sign_out_button.is_enabled()
                button_status["sign_out_available"] = is_visible and is_enabled
                logger.info(f"簽退按鈕狀態: 可見={is_visible}, 可用={is_enabled}")
        except Exception as e:
            logger.warning(f"無法檢查簽退按鈕狀態: {e}")
        
        return button_status
    
    def _log_status_summary(self, status_info: dict) -> None:
        """記錄狀態資訊摘要"""
        logger.info("打卡頁面狀態總結:")
        logger.info(f"  - 頁面載入: {status_info['page_loaded']}")
        logger.info(f"  - GPS地圖: {status_info['gps_loaded']}")
        logger.info(f"  - 當前日期: {status_info['current_date']}")
        logger.info(f"  - 當前時間: {status_info['current_time']}")
        if status_info['location_info']:
            logger.info(f"  - 地址資訊: {status_info['location_info']}")
        logger.info(f"  - 簽到可用: {status_info['sign_in_available']}")
        logger.info(f"  - 簽退可用: {status_info['sign_out_available']}")
    
    async def check_button_availability(self, button_type: str) -> bool:
        """檢查特定按鈕的可用性"""
        try:
            if button_type == "sign_in":
                button_text = "簽到"
            elif button_type == "sign_out":
                button_text = "簽退"
            else:
                logger.error(f"不支援的按鈕類型: {button_type}")
                return False
            
            button_selector = f'button:has-text("{button_text}")'
            button_element = await self.page.query_selector(button_selector)
            
            if not button_element:
                return False
            
            is_visible = await button_element.is_visible()
            is_enabled = await button_element.is_enabled()
            
            return is_visible and is_enabled
            
        except Exception as e:
            logger.error(f"檢查 {button_type} 按鈕可用性失敗: {e}")
            return False