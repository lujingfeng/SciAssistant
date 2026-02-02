# Copyright (c) 2026 South China Sea Institute of Oceanology, Chinese Academy of Sciences (SCSIO, CAS). All rights reserved.
"""
统一的日志配置模块
提供项目级别的日志管理和配置
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 日志格式
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
SIMPLE_FORMAT = '%(levelname)s - %(message)s'

class LoggerManager:
    """日志管理器 - 单例模式"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._loggers = {}
            self._log_dir = None
            self._default_level = logging.INFO
            self._console_level = logging.INFO
            self._file_level = logging.DEBUG
            LoggerManager._initialized = True
    
    def setup_logging(
        self,
        log_dir: Optional[str] = None,
        default_level: str = 'INFO',
        console_level: str = 'INFO',
        file_level: str = 'DEBUG',
        log_format: str = DEFAULT_FORMAT,
        enable_file_logging: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        配置全局日志设置
        
        Args:
            log_dir: 日志文件目录
            default_level: 默认日志级别
            console_level: 控制台日志级别
            file_level: 文件日志级别
            log_format: 日志格式
            enable_file_logging: 是否启用文件日志
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的日志文件数量
        """
        self._default_level = LOG_LEVELS.get(default_level.upper(), logging.INFO)
        self._console_level = LOG_LEVELS.get(console_level.upper(), logging.INFO)
        self._file_level = LOG_LEVELS.get(file_level.upper(), logging.DEBUG)
        
        if log_dir and enable_file_logging:
            self._log_dir = Path(log_dir)
            self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(self._default_level)
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._console_level)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 添加文件处理器
        if self._log_dir and enable_file_logging:
            file_handler = RotatingFileHandler(
                self._log_dir / 'app.log',
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self._file_level)
            file_formatter = logging.Formatter(DETAILED_FORMAT)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str, level: Optional[str] = None) -> logging.Logger:
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称（通常使用 __name__）
            level: 可选的日志级别，覆盖默认级别
            
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            if level:
                logger.setLevel(LOG_LEVELS.get(level.upper(), self._default_level))
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_level(self, name: str, level: str):
        """设置指定日志记录器的级别"""
        if name in self._loggers:
            self._loggers[name].setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    
    def disable_module_logging(self, module_name: str):
        """禁用指定模块的日志"""
        logging.getLogger(module_name).setLevel(logging.CRITICAL + 1)


# 全局日志管理器实例
_logger_manager = LoggerManager()


def setup_logging(**kwargs):
    """
    配置全局日志 - 便捷函数
    
    使用示例:
        setup_logging(
            log_dir='logs',
            default_level='INFO',
            console_level='INFO',
            file_level='DEBUG'
        )
    """
    _logger_manager.setup_logging(**kwargs)


def get_logger(name: str = __name__, level: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器 - 便捷函数
    
    使用示例:
        logger = get_logger(__name__)
        logger.info("这是一条信息")
        logger.debug("这是调试信息")
        logger.warning("这是警告")
        logger.error("这是错误")
    
    Args:
        name: 日志记录器名称
        level: 可选的日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return _logger_manager.get_logger(name, level)


def disable_third_party_logs():
    """禁用或降低第三方库的日志级别"""
    # 常见的第三方库日志
    noisy_loggers = [
        'urllib3',
        'requests',
        'httpx',
        'httpcore',
        'asyncio',
        'aiohttp',
        'litellm',
        'openai',
        'anthropic',
        'faiss',
        'transformers',
        'torch'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# 快速配置预设
def quick_setup(
    environment: str = 'development',
    log_dir: Optional[str] = 'logs',
    enable_file_logging: bool = True
):
    """
    快速配置日志系统
    
    Args:
        environment: 环境类型 ('development', 'production', 'testing')
        log_dir: 日志目录
        enable_file_logging: 是否启用文件日志
    """
    if environment == 'development':
        setup_logging(
            log_dir=log_dir,
            default_level='DEBUG',
            console_level='DEBUG',
            file_level='DEBUG',
            log_format=DETAILED_FORMAT,
            enable_file_logging=enable_file_logging
        )
    elif environment == 'production':
        setup_logging(
            log_dir=log_dir,
            default_level='INFO',
            console_level='INFO',
            file_level='DEBUG',
            log_format=DEFAULT_FORMAT,
            enable_file_logging=enable_file_logging
        )
    elif environment == 'testing':
        setup_logging(
            log_dir=log_dir,
            default_level='WARNING',
            console_level='WARNING',
            file_level='INFO',
            log_format=SIMPLE_FORMAT,
            enable_file_logging=enable_file_logging
        )
    
    # 降低第三方库日志级别
    disable_third_party_logs()


if __name__ == '__main__':
    # 测试示例
    quick_setup('development')
    
    logger = get_logger(__name__)
    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
