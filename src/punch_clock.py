"""
震旦HR系統自動打卡核心模組
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Callable, Any
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from .models import LoginCredentials, PunchAction, PunchResult, GPSConfig


class AoaCloudPunchClock:
    """震旦HR系統自動打卡類別"""
    
    def __init__(self, headless: bool = True, enable_screenshots: bool = False, screenshots_dir: str = "screenshots", gps_config: Optional[GPSConfig] = None):
        self.headless = headless
        self.enable_screenshots = enable_screenshots
        self.screenshots_dir = Path(screenshots_dir)
        self.gps_config = gps_config or GPSConfig()  # 使用傳入的GPS配置或預設值
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._base_url = "https://erpline.aoacloud.com.tw"
        self._screenshot_counter = 0
        self._screenshots_taken: List[Path] = []
        
        # 建立截圖目錄
        if self.enable_screenshots:
            self.screenshots_dir.mkdir(exist_ok=True)
            logger.info(f"截圖將保存到: {self.screenshots_dir}")
        
    async def __aenter__(self):
        """異步上下文管理器進入"""
        await self._initialize_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器退出"""
        await self._cleanup()
        
    async def _initialize_browser(self) -> None:
        """初始化瀏覽器"""
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--use-fake-ui-for-media-stream',  # 自動允許媒體權限
                    '--use-fake-device-for-media-stream'  # 使用假設備
                ]
            )
            
            # 創建新的context以便設置權限
            context = await self.browser.new_context(
                permissions=['geolocation'],  # 授予地理位置權限
                geolocation={
                    'latitude': self.gps_config.latitude, 
                    'longitude': self.gps_config.longitude
                }  # 使用配置檔案的GPS座標
            )
            
            self.page = await context.new_page()
            
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # 監聽並自動處理權限對話框
            self.page.on('dialog', self._handle_dialog)
            
            logger.info("瀏覽器初始化完成")
            
        except Exception as e:
            logger.error(f"瀏覽器初始化失敗: {e}")
            raise
    
    async def _handle_dialog(self, dialog):
        """處理瀏覽器對話框（如權限請求）"""
        try:
            dialog_type = dialog.type
            message = dialog.message
            
            logger.info(f"檢測到對話框 - 類型: {dialog_type}, 訊息: {message}")
            
            # 自動接受所有對話框（包括權限請求）
            await dialog.accept()
            logger.info("已自動接受對話框")
            
        except Exception as e:
            logger.error(f"處理對話框時發生錯誤: {e}")
            try:
                await dialog.dismiss()
            except:
                pass
            
    async def _cleanup(self) -> None:
        """清理資源"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("資源清理完成")
        except Exception as e:
            logger.error(f"資源清理失敗: {e}")
    
    async def _take_screenshot(self, step_name: str, description: str = "") -> Optional[Path]:
        """截取頁面截圖"""
        if not self.enable_screenshots or not self.page:
            return None
            
        try:
            self._screenshot_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self._screenshot_counter:02d}_{timestamp}_{step_name}.png"
            screenshot_path = self.screenshots_dir / filename
            
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            self._screenshots_taken.append(screenshot_path)
            
            log_msg = f"截圖已保存: {screenshot_path}"
            if description:
                log_msg += f" - {description}"
            logger.info(log_msg)
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"截圖失敗: {e}")
            return None
    
    async def _retry_async_operation(self, operation: Callable, max_retries: int = 3, 
                                   delay: float = 1.0, operation_name: str = "操作") -> Any:
        """重試異步操作的通用方法"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"重試 {operation_name} (第 {attempt + 1} 次嘗試)")
                    await asyncio.sleep(delay * attempt)  # 遞增延遲
                
                result = await operation()
                
                if attempt > 0:
                    logger.info(f"{operation_name} 重試成功")
                
                return result
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"{operation_name} 失敗，將重試: {str(e)}")
                else:
                    logger.error(f"{operation_name} 重試 {max_retries} 次後仍然失敗: {str(e)}")
        
        raise last_exception
    
    async def _take_error_screenshot(self, error_context: str) -> Optional[Path]:
        """發生錯誤時截取頁面截圖"""
        return await self._take_screenshot("error", f"錯誤狀況: {error_context}")
    
    def get_screenshots_taken(self) -> List[Path]:
        """獲取已截取的截圖列表"""
        return self._screenshots_taken.copy()
            
    async def login(self, credentials: LoginCredentials) -> bool:
        """登入震旦HR系統"""
        try:
            logger.info("開始登入流程...")
            
            response = await self.page.goto(self._base_url, wait_until='networkidle')
            
            if not response or response.status != 200:
                logger.error(f"無法載入登入頁面，狀態碼: {response.status if response else 'None'}")
                await self._take_error_screenshot("頁面載入失敗")
                return False
            
            logger.info("登入頁面載入成功")
            await self._take_screenshot("page_loaded", "登入頁面載入完成")
            
            # 等待登入表單載入
            await self.page.wait_for_selector('input[name="CompId"]', timeout=10000)
            
            # 填入憑證
            await self.page.fill('input[name="CompId"]', credentials.company_id)
            await self.page.fill('input[name="UserId"]', credentials.user_id)
            await self.page.fill('input[name="Passwd"]', credentials.password)
            
            logger.info("已填入登入資訊")
            await self._take_screenshot("credentials_filled", "登入資訊填寫完成")
            
            # 點擊登入按鈕
            await self.page.click('button:has-text("登入")')
            logger.info("已點擊登入按鈕")
            
            # 等待頁面跳轉
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            
            current_url = self.page.url
            if current_url != self._base_url and "login" not in current_url.lower():
                logger.info(f"登入成功，當前URL: {current_url}")
                await self._take_screenshot("login_success", f"登入成功頁面 - {current_url}")
                return True
            else:
                logger.error("登入失敗：未能成功跳轉")
                await self._take_error_screenshot("登入失敗")
                return False
                
        except Exception as e:
            logger.error(f"登入過程中發生錯誤: {e}")
            await self._take_error_screenshot(f"登入異常: {str(e)}")
            return False
    
    async def navigate_to_punch_page(self) -> bool:
        """導航到出勤打卡頁面（帶重試機制）"""
        async def _do_navigation():
            logger.info("準備導航到出勤打卡頁面...")
            
            # 等待主頁面載入完成
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await self._take_screenshot("main_page", "主頁面載入完成")
            
            # 尋找並點擊出勤打卡圖示
            punch_card_selector = 'ion-col:has(p:text("出勤打卡"))'
            
            try:
                await self.page.wait_for_selector(punch_card_selector, timeout=10000)
                logger.info("找到出勤打卡圖示")
            except:
                # 如果找不到，嘗試其他選擇器
                alternative_selector = 'ion-col:has(img[src*="home_01"])'
                await self.page.wait_for_selector(alternative_selector, timeout=5000)
                punch_card_selector = alternative_selector
                logger.info("使用替代選擇器找到出勤打卡圖示")
            
            # 點擊出勤打卡圖示
            await self.page.click(punch_card_selector)
            logger.info("已點擊出勤打卡圖示")
            
            # 等待打卡頁面基本載入
            await self.page.wait_for_load_state('domcontentloaded', timeout=15000)
            
            # 等待頁面標題出現，確認已到達打卡頁面
            try:
                await self.page.wait_for_selector('.toolbar-title', timeout=10000)
                page_title = await self.page.text_content('.toolbar-title')
                if not (page_title and "打卡" in page_title):
                    raise Exception(f"頁面標題不符預期: {page_title}")
                logger.info("成功導航到打卡頁面")
            except Exception as title_error:
                logger.warning("無法找到頁面標題，嘗試其他方式驗證")
                # 嘗試查找打卡按鈕作為備用驗證
                try:
                    await self.page.wait_for_selector('button:has-text("簽到")', timeout=5000)
                    logger.info("透過簽到按鈕確認已到達打卡頁面")
                except:
                    raise Exception("無法確認是否成功導航到打卡頁面")
            
            # 等待GPS定位和地圖載入完成（容忍失敗）
            try:
                logger.info("等待GPS定位和地圖元素載入...")
                # 等待地圖容器出現
                await self.page.wait_for_selector('#divImap', timeout=8000)
                
                # 主動觸發GPS定位（點擊定位按鈕）
                try:
                    locate_button = await self.page.query_selector('ion-fab button[ion-fab]')
                    if locate_button and await locate_button.is_visible():
                        logger.info("找到定位按鈕，主動觸發GPS定位")
                        await locate_button.click()
                        await asyncio.sleep(2)  # 等待定位請求
                        logger.info("已觸發GPS定位")
                except Exception as loc_error:
                    logger.warning(f"無法主動觸發GPS定位: {loc_error}")
                
                # 等待一段時間讓GPS定位完成（不強制要求成功）
                await asyncio.sleep(3)
                logger.info("GPS定位等待完成")
            except:
                logger.warning("GPS定位載入超時，但繼續執行")
            
            # 等待loading spinner消失（如果存在）
            try:
                loading_selector = 'ion-loading'
                if await self.page.query_selector(loading_selector):
                    logger.info("檢測到loading狀態，等待完成...")
                    await self.page.wait_for_selector(loading_selector, state='detached', timeout=10000)
                    logger.info("Loading完成")
            except:
                logger.info("沒有檢測到loading狀態或已完成")
            
            # 最終截圖
            await self._take_screenshot("punch_page_ready", "打卡頁面準備完成")
            
            return True
        
        try:
            return await self._retry_async_operation(
                _do_navigation, 
                max_retries=2, 
                delay=2.0, 
                operation_name="導航到打卡頁面"
            )
        except Exception as e:
            logger.error(f"導航到打卡頁面最終失敗: {e}")
            await self._take_error_screenshot(f"導航失敗: {str(e)}")
            return False
    
    async def simulate_punch_action(self, action: str = "sign_in") -> bool:
        """模擬打卡動作（不會真的點擊按鈕）
        
        Args:
            action: 打卡動作類型 ("sign_in" 為簽到, "sign_out" 為簽退)
        """
        try:
            if action == "sign_in":
                button_text = "簽到"
                action_name = "簽到"
            elif action == "sign_out":
                button_text = "簽退"
                action_name = "簽退"
            else:
                logger.error(f"不支援的打卡動作: {action}")
                return False
                
            logger.info(f"模擬 {action_name} 動作...")
            
            # 等待打卡按鈕出現
            button_selector = f'button:has-text("{button_text}")'
            await self.page.wait_for_selector(button_selector, timeout=10000)
            
            # 檢查按鈕是否存在且可見
            button_element = await self.page.query_selector(button_selector)
            if not button_element:
                logger.error(f"找不到 {action_name} 按鈕")
                return False
            
            # 檢查按鈕狀態
            is_visible = await button_element.is_visible()
            is_enabled = await button_element.is_enabled()
            
            logger.info(f"{action_name} 按鈕狀態 - 可見: {is_visible}, 可用: {is_enabled}")
            
            # 截圖顯示當前狀態
            await self._take_screenshot(f"before_{action}", f"準備執行 {action_name} - 按鈕狀態檢查")
            
            if not is_visible:
                logger.warning(f"{action_name} 按鈕不可見")
                return False
            
            if not is_enabled:
                logger.warning(f"{action_name} 按鈕不可用")
                return False
            
            # 模擬點擊（不實際執行）
            logger.info(f"🔄 模擬 {action_name} 動作 - 實際上不會點擊按鈕")
            logger.info(f"✅ {action_name} 模擬完成 - 系統已識別到打卡功能可正常運作")
            
            # 截圖記錄
            await self._take_screenshot(f"simulated_{action}", f"模擬 {action_name} 完成")
            
            return True
            
        except Exception as e:
            logger.error(f"模擬 {action} 動作失敗: {e}")
            await self._take_error_screenshot(f"模擬{action}失敗: {str(e)}")
            return False
    
    async def _wait_for_stable_page(self, timeout: int = 10000) -> bool:
        """等待頁面穩定（處理GPS定位和loading狀態）"""
        try:
            logger.info("等待頁面穩定...")
            
            # 檢查並等待loading狀態消失
            max_wait_time = timeout / 1000  # 轉換為秒
            wait_interval = 0.5
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # 檢查是否有loading元素
                loading_element = await self.page.query_selector('ion-loading')
                if not loading_element:
                    # 檢查是否有其他loading指示器
                    spinner_element = await self.page.query_selector('.loading-spinner')
                    if not spinner_element:
                        logger.info("頁面載入狀態穩定")
                        break
                
                logger.info(f"檢測到載入中...等待 {wait_interval} 秒")
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

    async def check_punch_page_status(self) -> dict:
        """檢查打卡頁面狀態和資訊"""
        try:
            logger.info("檢查打卡頁面狀態...")
            
            # 首先等待頁面穩定
            await self._wait_for_stable_page()
            
            status_info = {
                "current_time": None,
                "current_date": None,
                "location_info": None,
                "sign_in_available": False,
                "sign_out_available": False,
                "page_loaded": False,
                "gps_loaded": False
            }
            
            # 檢查頁面是否載入完成
            try:
                page_title = await self.page.text_content('.toolbar-title')
                if page_title and "打卡" in page_title:
                    status_info["page_loaded"] = True
                    logger.info("打卡頁面載入確認")
                else:
                    # 透過簽到按鈕確認頁面載入
                    try:
                        sign_in_button = await self.page.query_selector('button:has-text("簽到")')
                        if sign_in_button and await sign_in_button.is_visible():
                            status_info["page_loaded"] = True
                            logger.info("透過簽到按鈕確認頁面載入")
                        else:
                            logger.warning("未找到頁面載入指標")
                    except Exception as btn_error:
                        logger.warning(f"按鈕檢查失敗: {btn_error}")
            except Exception as title_error:
                logger.warning(f"標題檢查失敗: {title_error}")
                # 透過簽到按鈕確認頁面載入作為備用方案
                try:
                    sign_in_button = await self.page.query_selector('button:has-text("簽到")')
                    if sign_in_button and await sign_in_button.is_visible():
                        status_info["page_loaded"] = True
                        logger.info("透過簽到按鈕確認頁面載入")
                    else:
                        logger.warning("無法確認頁面載入狀態")
                except:
                    logger.warning("無法確認頁面載入狀態")
            
            # 檢查GPS地圖是否載入
            try:
                map_element = await self.page.query_selector('#divImap iframe')
                if map_element:
                    status_info["gps_loaded"] = True
                    logger.info("GPS地圖載入確認")
                    
                    # 嘗試獲取地址資訊
                    try:
                        address_input = await self.page.query_selector('#addressDiv ion-input input')
                        if address_input:
                            address_value = await address_input.get_attribute('value')
                            if address_value:
                                status_info["location_info"] = address_value
                                logger.info(f"GPS地址資訊: {address_value}")
                    except:
                        logger.debug("無法獲取地址資訊")
            except:
                logger.warning("GPS地圖載入狀態未知")
            
            # 獲取當前時間和日期
            try:
                date_elements = await self.page.query_selector_all('.date')
                if len(date_elements) >= 2:
                    status_info["current_date"] = await date_elements[0].text_content()
                    status_info["current_time"] = await date_elements[1].text_content()
                    logger.info(f"獲取時間資訊: {status_info['current_date']} {status_info['current_time']}")
            except Exception as e:
                logger.warning(f"無法獲取時間資訊: {e}")
            
            # 檢查簽到按鈕狀態
            try:
                sign_in_button = await self.page.query_selector('button:has-text("簽到")')
                if sign_in_button:
                    is_visible = await sign_in_button.is_visible()
                    is_enabled = await sign_in_button.is_enabled()
                    status_info["sign_in_available"] = is_visible and is_enabled
                    logger.info(f"簽到按鈕狀態: 可見={is_visible}, 可用={is_enabled}")
            except Exception as e:
                logger.warning(f"無法檢查簽到按鈕狀態: {e}")
            
            # 檢查簽退按鈕狀態
            try:
                sign_out_button = await self.page.query_selector('button:has-text("簽退")')
                if sign_out_button:
                    is_visible = await sign_out_button.is_visible()
                    is_enabled = await sign_out_button.is_enabled()
                    status_info["sign_out_available"] = is_visible and is_enabled
                    logger.info(f"簽退按鈕狀態: 可見={is_visible}, 可用={is_enabled}")
            except Exception as e:
                logger.warning(f"無法檢查簽退按鈕狀態: {e}")
            
            # 截圖記錄當前狀態
            await self._take_screenshot("page_status", "打卡頁面狀態檢查")
            
            # 記錄狀態資訊
            logger.info(f"打卡頁面狀態總結:")
            logger.info(f"  - 頁面載入: {status_info['page_loaded']}")
            logger.info(f"  - GPS地圖: {status_info['gps_loaded']}")
            logger.info(f"  - 當前日期: {status_info['current_date']}")
            logger.info(f"  - 當前時間: {status_info['current_time']}")
            if status_info['location_info']:
                logger.info(f"  - 地址資訊: {status_info['location_info']}")
            logger.info(f"  - 簽到可用: {status_info['sign_in_available']}")
            logger.info(f"  - 簽退可用: {status_info['sign_out_available']}")
            
            return status_info
            
        except Exception as e:
            logger.error(f"檢查打卡頁面狀態失敗: {e}")
            await self._take_error_screenshot(f"狀態檢查失敗: {str(e)}")
            return {"error": str(e)}

    async def execute_real_punch_action(self, action: PunchAction, confirm: bool = False) -> PunchResult:
        """執行真實的打卡動作（實際點擊按鈕）
        
        Args:
            action: 打卡動作類型 (PunchAction.SIGN_IN 或 PunchAction.SIGN_OUT)
            confirm: 是否確認執行實際操作，預設為False以防誤操作
        
        Returns:
            PunchResult: 打卡操作結果
        """
        start_time = datetime.now()
        
        # 如果沒有確認，則執行模擬模式
        if not confirm:
            logger.warning("⚠️ 未確認實際操作，轉為模擬模式")
            simulate_success = await self.simulate_punch_action(action.value)
            return PunchResult(
                success=simulate_success,
                action=action,
                timestamp=start_time,
                message="模擬模式執行，未實際點擊按鈕",
                is_simulation=True
            )
        
        try:
            if action == PunchAction.SIGN_IN:
                button_text = "簽到"
                action_name = "簽到"
            elif action == PunchAction.SIGN_OUT:
                button_text = "簽退"
                action_name = "簽退"
            else:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=start_time,
                    message=f"不支援的打卡動作: {action}",
                    is_simulation=False
                )
            
            logger.info(f"🎯 準備執行真實 {action_name} 操作...")
            
            # 等待打卡按鈕出現
            button_selector = f'button:has-text("{button_text}")'
            await self.page.wait_for_selector(button_selector, timeout=10000)
            
            # 檢查按鈕是否存在且可見
            button_element = await self.page.query_selector(button_selector)
            if not button_element:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=start_time,
                    message=f"找不到 {action_name} 按鈕",
                    is_simulation=False
                )
            
            # 檢查按鈕狀態
            is_visible = await button_element.is_visible()
            is_enabled = await button_element.is_enabled()
            
            if not is_visible:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=start_time,
                    message=f"{action_name} 按鈕不可見",
                    is_simulation=False
                )
            
            if not is_enabled:
                return PunchResult(
                    success=False,
                    action=action,
                    timestamp=start_time,
                    message=f"{action_name} 按鈕不可用",
                    is_simulation=False
                )
            
            # 執行前截圖
            before_screenshot = await self._take_screenshot(f"before_real_{action.value}", f"準備執行真實 {action_name}")
            
            logger.info(f"🚀 執行真實 {action_name} 操作 - 點擊按鈕")
            
            # 實際點擊按鈕
            await button_element.click()
            
            logger.info(f"✅ 已點擊 {action_name} 按鈕，等待系統回應...")
            
            # 等待系統處理
            await asyncio.sleep(2)  # 給系統時間處理請求
            
            # 執行後截圖
            after_screenshot = await self._take_screenshot(f"after_real_{action.value}", f"執行 {action_name} 後的頁面狀態")
            
            # 驗證打卡結果
            verification_result = await self.verify_punch_result(action)
            
            return PunchResult(
                success=verification_result["success"],
                action=action,
                timestamp=start_time,
                message=verification_result["message"],
                server_response=verification_result.get("server_response"),
                screenshot_path=after_screenshot,
                is_simulation=False
            )
            
        except Exception as e:
            error_screenshot = await self._take_error_screenshot(f"真實{action_name}操作失敗: {str(e)}")
            logger.error(f"執行真實 {action_name} 操作失敗: {e}")
            
            return PunchResult(
                success=False,
                action=action,
                timestamp=start_time,
                message=f"執行 {action_name} 時發生錯誤: {str(e)}",
                screenshot_path=error_screenshot,
                is_simulation=False
            )

    async def verify_punch_result(self, action: PunchAction, timeout: int = 10000) -> dict:
        """驗證打卡操作結果
        
        Args:
            action: 執行的打卡動作
            timeout: 等待驗證的超時時間（毫秒）
        
        Returns:
            dict: 驗證結果，包含success, message, server_response等
        """
        try:
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            logger.info(f"🔍 驗證 {action_name} 操作結果...")
            
            # 等待可能出現的成功訊息或對話框
            success_indicators = [
                'text="打卡成功"',           # 成功訊息
                'text="簽到成功"',           # 簽到成功
                'text="簽退成功"',           # 簽退成功  
                '.success-message',           # 成功訊息CSS類別
                'ion-toast[color="success"]', # 成功提示框
                '.alert-success'              # 成功警告框
            ]
            
            error_indicators = [
                'text="打卡失敗"',           # 失敗訊息
                'text="簽到失敗"',           # 簽到失敗
                'text="簽退失敗"',           # 簽退失敗
                '.error-message',             # 錯誤訊息CSS類別
                'ion-toast[color="danger"]',  # 錯誤提示框
                '.alert-danger'               # 錯誤警告框
            ]
            
            verification_result = {
                "success": False,
                "message": f"{action_name} 結果未知",
                "server_response": None
            }
            
            # 等待成功或失敗指示器出現
            wait_time = timeout / 1000  # 轉換為秒
            check_interval = 0.5
            elapsed_time = 0
            
            while elapsed_time < wait_time:
                # 檢查成功指示器
                for indicator in success_indicators:
                    try:
                        element = await self.page.query_selector(indicator)
                        if element and await element.is_visible():
                            text_content = await element.text_content()
                            logger.info(f"✅ 檢測到成功指示器: {text_content}")
                            verification_result.update({
                                "success": True,
                                "message": f"{action_name} 成功",
                                "server_response": text_content
                            })
                            return verification_result
                    except:
                        continue
                
                # 檢查失敗指示器
                for indicator in error_indicators:
                    try:
                        element = await self.page.query_selector(indicator)
                        if element and await element.is_visible():
                            text_content = await element.text_content()
                            logger.warning(f"❌ 檢測到失敗指示器: {text_content}")
                            verification_result.update({
                                "success": False,
                                "message": f"{action_name} 失敗",
                                "server_response": text_content
                            })
                            return verification_result
                    except:
                        continue
                
                # 檢查頁面是否有任何提示訊息
                try:
                    # 查找一般的提示訊息
                    toast_elements = await self.page.query_selector_all('ion-toast')
                    for toast in toast_elements:
                        if await toast.is_visible():
                            toast_text = await toast.text_content()
                            if toast_text and (action_name in toast_text or "打卡" in toast_text):
                                logger.info(f"📄 檢測到提示訊息: {toast_text}")
                                # 根據訊息內容判斷成功或失敗
                                if "成功" in toast_text:
                                    verification_result.update({
                                        "success": True,
                                        "message": f"{action_name} 成功",
                                        "server_response": toast_text
                                    })
                                elif "失敗" in toast_text or "錯誤" in toast_text:
                                    verification_result.update({
                                        "success": False,
                                        "message": f"{action_name} 失敗",
                                        "server_response": toast_text
                                    })
                                else:
                                    verification_result.update({
                                        "message": f"{action_name} 結果: {toast_text}",
                                        "server_response": toast_text
                                    })
                                return verification_result
                except:
                    pass
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
            
            # 如果沒有明確的成功/失敗指示器，嘗試通過按鈕狀態變化判斷
            logger.info("🔄 未檢測到明確結果指示器，嘗試通過按鈕狀態判斷...")
            
            try:
                current_status = await self.check_punch_page_status()
                if action == PunchAction.SIGN_IN:
                    # 簽到後，簽到按鈕應該變為不可用，簽退按鈕變為可用
                    if not current_status.get('sign_in_available', True) and current_status.get('sign_out_available', False):
                        verification_result.update({
                            "success": True,
                            "message": "根據按鈕狀態判斷簽到成功",
                            "server_response": "按鈕狀態已更新"
                        })
                    else:
                        verification_result.update({
                            "success": False,
                            "message": "根據按鈕狀態判斷簽到可能失敗",
                            "server_response": "按鈕狀態未如預期更新"
                        })
                elif action == PunchAction.SIGN_OUT:
                    # 簽退後，簽退按鈕應該變為不可用，簽到按鈕變為可用（隔天）
                    if not current_status.get('sign_out_available', True):
                        verification_result.update({
                            "success": True,
                            "message": "根據按鈕狀態判斷簽退成功",
                            "server_response": "按鈕狀態已更新"
                        })
                    else:
                        verification_result.update({
                            "success": False,
                            "message": "根據按鈕狀態判斷簽退可能失敗",
                            "server_response": "按鈕狀態未如預期更新"
                        })
            except Exception as status_error:
                logger.warning(f"無法檢查按鈕狀態: {status_error}")
            
            logger.warning(f"⚠️ {action_name} 結果驗證超時或未明確")
            return verification_result
            
        except Exception as e:
            logger.error(f"驗證 {action_name} 結果時發生錯誤: {e}")
            return {
                "success": False,
                "message": f"驗證 {action_name} 結果時發生錯誤: {str(e)}",
                "server_response": None
            }

    async def wait_for_punch_confirmation(self, action: PunchAction, timeout: int = 30000) -> bool:
        """等待用戶確認執行真實打卡操作
        
        Args:
            action: 要執行的打卡動作
            timeout: 等待確認的超時時間（毫秒）
        
        Returns:
            bool: 是否確認執行
        """
        try:
            action_name = "簽到" if action == PunchAction.SIGN_IN else "簽退"
            
            logger.info(f"⚠️ 準備執行真實 {action_name} 操作")
            logger.info("🔔 這將會實際點擊打卡按鈕，請確認您要執行此操作")
            logger.info("💡 如果您只想測試功能，請使用模擬模式")
            
            # 在交互式模式下，詢問用戶確認
            if hasattr(self, '_interactive_mode') and self._interactive_mode:
                try:
                    import sys
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
        """設定是否為交互式模式
        
        Args:
            interactive: 是否啟用交互式模式
        """
        self._interactive_mode = interactive
        if interactive:
            logger.info("🤝 已啟用交互式模式，執行真實操作前將詢問確認")
        else:
            logger.info("🤖 已設定為非交互式模式，預設執行模擬操作")