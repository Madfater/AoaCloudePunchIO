"""
錯誤處理和重試機制模組
"""

import asyncio
from typing import Any, Callable, Optional, Union, Type, Tuple
from functools import wraps
from datetime import datetime, timedelta
from loguru import logger
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import Error as PlaywrightError


class RetryConfig:
    """重試配置"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class PunchClockError(Exception):
    """打卡系統自定義錯誤基類"""
    pass


class LoginError(PunchClockError):
    """登入錯誤"""
    pass


class NavigationError(PunchClockError):
    """頁面導航錯誤"""
    pass


class PunchActionError(PunchClockError):
    """打卡動作錯誤"""
    pass


class NetworkError(PunchClockError):
    """網路連線錯誤"""
    pass


class BrowserError(PunchClockError):
    """瀏覽器錯誤"""
    pass


class RetryHandler:
    """重試處理器"""
    
    # 可重試的錯誤類型
    RETRYABLE_ERRORS = (
        PlaywrightTimeoutError,
        PlaywrightError,
        NetworkError,
        BrowserError,
        ConnectionError,
        TimeoutError,
    )
    
    # 不可重試的錯誤類型
    NON_RETRYABLE_ERRORS = (
        LoginError,  # 登入憑證錯誤，重試無意義
        ValueError,  # 參數錯誤
        TypeError,   # 類型錯誤
    )
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int) -> float:
        """計算延遲時間（指數退避 + 抖動）"""
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            # 添加 ±25% 的隨機抖動
            jitter = random.uniform(-0.25, 0.25) * delay
            delay += jitter
        
        return max(0, delay)
    
    def is_retryable_error(self, error: Exception) -> bool:
        """判斷錯誤是否可重試"""
        # 檢查不可重試的錯誤
        if isinstance(error, self.NON_RETRYABLE_ERRORS):
            return False
        
        # 檢查可重試的錯誤
        if isinstance(error, self.RETRYABLE_ERRORS):
            return True
        
        # 對於未知錯誤，檢查錯誤訊息中的關鍵字
        error_message = str(error).lower()
        retryable_keywords = [
            'timeout', 'connection', 'network', 'disconnected',
            'reset', 'refused', 'unreachable', 'aborted'
        ]
        
        return any(keyword in error_message for keyword in retryable_keywords)
    
    async def retry_async(
        self,
        func: Callable,
        *args,
        error_context: str = "",
        **kwargs
    ) -> Any:
        """異步重試裝飾器"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.debug(f"嘗試執行 {error_context or func.__name__} (第 {attempt}/{self.config.max_attempts} 次)")
                result = await func(*args, **kwargs)
                
                if attempt > 1:
                    logger.success(f"{error_context or func.__name__} 在第 {attempt} 次嘗試後成功")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 記錄錯誤
                logger.warning(f"{error_context or func.__name__} 第 {attempt} 次嘗試失敗: {e}")
                
                # 檢查是否可重試
                if not self.is_retryable_error(e):
                    logger.error(f"遇到不可重試錯誤，停止重試: {e}")
                    raise e
                
                # 如果是最後一次嘗試，拋出錯誤
                if attempt == self.config.max_attempts:
                    logger.error(f"{error_context or func.__name__} 在 {self.config.max_attempts} 次嘗試後仍然失敗")
                    break
                
                # 計算延遲時間並等待
                delay = self.calculate_delay(attempt)
                logger.info(f"等待 {delay:.2f} 秒後重試...")
                await asyncio.sleep(delay)
        
        # 如果所有嘗試都失敗，拋出最後一個錯誤
        raise last_exception


def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    error_context: str = ""
):
    """重試裝飾器"""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            handler = RetryHandler(config)
            return await handler.retry_async(
                func, *args, error_context=error_context or func.__name__, **kwargs
            )
        return wrapper
    return decorator


class CircuitBreaker:
    """熔斷器模式實現"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """檢查是否可以執行操作"""
        if self.state == 'CLOSED':
            return True
        
        if self.state == 'OPEN':
            # 檢查是否可以嘗試恢復
            if (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.info("熔斷器進入半開狀態，嘗試恢復")
                return True
            return False
        
        # HALF_OPEN 狀態允許一次嘗試
        return self.state == 'HALF_OPEN'
    
    def record_success(self):
        """記錄成功"""
        self.failure_count = 0
        self.state = 'CLOSED'
        if self.last_failure_time:
            logger.success("熔斷器恢復正常狀態")
            self.last_failure_time = None
    
    def record_failure(self, exception: Exception):
        """記錄失敗"""
        if isinstance(exception, self.expected_exception):
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"熔斷器觸發，連續失敗 {self.failure_count} 次")
    
    async def call(self, func: Callable, *args, **kwargs):
        """執行函數（帶熔斷器保護）"""
        if not self.can_execute():
            raise PunchClockError("熔斷器開啟，暫時無法執行操作")
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise


# 全域重試處理器實例
default_retry_handler = RetryHandler()
default_circuit_breaker = CircuitBreaker()