"""
自動打卡排程系統模組
使用 APScheduler 實現自動化排程
"""

import asyncio
from datetime import datetime, time
from typing import Optional, Callable, Dict, Any
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from src.models import ScheduleConfig, PunchAction, PunchResult
from src.config import ConfigManager


class PunchScheduler:
    """自動打卡排程器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self._punch_callback: Optional[Callable] = None
        
        # 初始化排程器
        self._init_scheduler()
    
    def _init_scheduler(self):
        """初始化 APScheduler"""
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,  # 不合併錯過的任務
            'max_instances': 1,  # 同一時間只能有一個任務實例
            'misfire_grace_time': 30  # 錯過任務的容忍時間（秒）
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Taipei'  # 設定時區
        )
    
    def set_punch_callback(self, callback: Callable):
        """設定打卡回調函數
        
        Args:
            callback: 打卡函數，應該接受 PunchAction 參數並返回 PunchResult
        """
        self._punch_callback = callback
    
    async def start(self):
        """啟動排程器"""
        if self.is_running:
            logger.warning("排程器已在運行中")
            return
        
        try:
            # 載入配置
            config = self.config_manager.load_config()
            schedule_config = config.schedule
            
            if not schedule_config.enabled:
                logger.info("排程功能已停用")
                return
            
            # 添加排程任務
            await self._add_scheduled_jobs(schedule_config)
            
            # 啟動排程器
            self.scheduler.start()
            self.is_running = True
            
            logger.info("自動打卡排程器已啟動")
            logger.info(f"簽到時間: {schedule_config.clock_in_time}")
            logger.info(f"簽退時間: {schedule_config.clock_out_time}")
            logger.info(f"僅工作日: {schedule_config.weekdays_only}")
            
        except Exception as e:
            logger.error(f"啟動排程器失敗: {e}")
            raise
    
    async def stop(self):
        """停止排程器"""
        if not self.is_running:
            return
        
        if self.scheduler:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("自動打卡排程器已停止")
    
    async def _add_scheduled_jobs(self, schedule_config: ScheduleConfig):
        """添加排程任務"""
        if not self._punch_callback:
            raise ValueError("打卡回調函數未設定，請先調用 set_punch_callback()")
        
        # 解析簽到時間
        clock_in_hour, clock_in_minute = map(int, schedule_config.clock_in_time.split(':'))
        clock_out_hour, clock_out_minute = map(int, schedule_config.clock_out_time.split(':'))
        
        # 設定 cron 觸發器參數
        cron_kwargs = {
            'hour': clock_in_hour,
            'minute': clock_in_minute,
            'second': 0
        }
        
        if schedule_config.weekdays_only:
            cron_kwargs['day_of_week'] = '0-4'  # 週一到週五
        
        # 添加簽到任務
        self.scheduler.add_job(
            func=self._execute_punch_job,
            trigger=CronTrigger(**cron_kwargs),
            args=[PunchAction.SIGN_IN],
            id='clock_in_job',
            name='自動簽到',
            replace_existing=True
        )
        
        # 添加簽退任務
        cron_kwargs.update({
            'hour': clock_out_hour,
            'minute': clock_out_minute
        })
        
        self.scheduler.add_job(
            func=self._execute_punch_job,
            trigger=CronTrigger(**cron_kwargs),
            args=[PunchAction.SIGN_OUT],
            id='clock_out_job',
            name='自動簽退',
            replace_existing=True
        )
        
        logger.info(f"已添加排程任務: 簽到 {schedule_config.clock_in_time}, 簽退 {schedule_config.clock_out_time}")
    
    async def _execute_punch_job(self, action: PunchAction):
        """執行打卡任務"""
        logger.info(f"開始執行排程打卡任務: {action.value}")
        
        try:
            # 執行打卡回調
            result = await self._punch_callback(action)
            
            if result.success:
                logger.success(f"排程打卡成功: {action.value} - {result.message}")
            else:
                logger.error(f"排程打卡失敗: {action.value} - {result.message}")
                
        except Exception as e:
            logger.error(f"執行排程打卡任務時發生錯誤: {e}")
    
    def get_next_runs(self) -> Dict[str, Optional[datetime]]:
        """取得下次執行時間"""
        if not self.scheduler or not self.is_running:
            return {}
        
        result = {}
        for job in self.scheduler.get_jobs():
            result[job.name] = job.next_run_time
        
        return result
    
    def get_job_status(self) -> Dict[str, Any]:
        """取得排程器狀態"""
        if not self.scheduler:
            return {
                'running': False,
                'jobs': []
            }
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })
        
        return {
            'running': self.is_running,
            'jobs': jobs_info,
            'timezone': str(self.scheduler.timezone)
        }
    
    async def trigger_immediate_punch(self, action: PunchAction) -> PunchResult:
        """立即觸發打卡（手動觸發）"""
        logger.info(f"手動觸發打卡: {action.value}")
        
        if not self._punch_callback:
            raise ValueError("打卡回調函數未設定")
        
        try:
            result = await self._punch_callback(action)
            logger.info(f"手動打卡結果: {result.success}")
            return result
        except Exception as e:
            logger.error(f"手動打卡失敗: {e}")
            raise


class SchedulerManager:
    """排程管理器（單例模式）"""
    
    _instance: Optional['SchedulerManager'] = None
    _scheduler: Optional[PunchScheduler] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._scheduler is None:
            from .config import config_manager
            self._scheduler = PunchScheduler(config_manager)
    
    @property
    def scheduler(self) -> PunchScheduler:
        """取得排程器實例"""
        return self._scheduler
    
    async def initialize(self, punch_callback: Callable):
        """初始化排程器"""
        self._scheduler.set_punch_callback(punch_callback)
        await self._scheduler.start()
    
    async def shutdown(self):
        """關閉排程器"""
        if self._scheduler:
            await self._scheduler.stop()


# 全域排程管理器實例
scheduler_manager = SchedulerManager()