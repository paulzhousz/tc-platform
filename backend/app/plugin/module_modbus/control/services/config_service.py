"""
Modbus 配置服务

从 Redis 缓存获取系统配置（由 System 模块管理）。
配置通过管理后台修改后自动生效。

使用方式：
    # 异步获取单个配置
    value = await ModbusConfigService.get(redis, "modbus_poll_interval")

    # 批量获取配置（推荐用于同步场景）
    config = await ModbusConfigService.get_all(redis)
    model_name = config["modbus_llm_model_name"]
"""
from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio.client import Redis

from app.common.enums import RedisInitKeyConfig
from app.core.redis_crud import RedisCURD

logger = logging.getLogger(__name__)


class ModbusConfigService:
    """Modbus 配置服务 - 从 Redis 获取运行时配置"""

    # 配置键及其默认值
    DEFAULTS: dict[str, Any] = {
        # LLM 配置
        "modbus_llm_model_name": "moonshotai/Kimi-K2.5",
        "modbus_llm_temperature": 0.0,
        "modbus_llm_session_ttl_minutes": 10,
        "modbus_llm_max_history_turns": 20,
        # 重试配置
        "modbus_retry_enabled": True,
        "modbus_retry_times": 3,
        "modbus_retry_interval": 1.0,
        # 轮询配置
        "modbus_poll_enabled": True,
        "modbus_poll_interval": 5,
        # 待确认配置
        "modbus_pending_expire_minutes": 10,
        # FunASR 配置
        "modbus_funasr_mode": "2pass-offline",
        "modbus_silence_threshold": 0.03,
        "modbus_silence_duration": 5,
        # 聊天历史配置
        "modbus_chat_save_min_messages": 2,
    }

    # 类型转换配置
    FLOAT_KEYS = ("modbus_llm_temperature", "modbus_retry_interval", "modbus_silence_threshold")
    INT_KEYS = (
        "modbus_llm_session_ttl_minutes", "modbus_llm_max_history_turns",
        "modbus_retry_times", "modbus_poll_interval",
        "modbus_pending_expire_minutes", "modbus_silence_duration",
        "modbus_chat_save_min_messages",
    )
    BOOL_KEYS = ("modbus_retry_enabled", "modbus_poll_enabled")

    @classmethod
    def _get_redis_key(cls, config_key: str) -> str:
        """构建 Redis 键名"""
        return f"{RedisInitKeyConfig.SYSTEM_CONFIG.key}:{config_key}"

    @classmethod
    def _convert_value(cls, key: str, value: Any) -> Any:
        """根据配置键名转换值类型"""
        if value is None:
            return cls.DEFAULTS.get(key)

        if key in cls.FLOAT_KEYS:
            return float(value)
        elif key in cls.INT_KEYS:
            return int(float(value))
        elif key in cls.BOOL_KEYS:
            return str(value).lower() in ("true", "1", "yes")
        return value

    @classmethod
    async def get(cls, redis: Redis, key: str, default: Any = None) -> Any:
        """从 Redis 获取配置值

        参数:
            redis: Redis 客户端实例
            key: 配置键名（如 modbus_poll_interval）
            default: 默认值（可选，未设置时使用 DEFAULTS）

        返回:
            配置值（已类型转换）
        """
        try:
            redis_key = cls._get_redis_key(key)
            data = await RedisCURD(redis).get(redis_key)
            if data:
                config = json.loads(data)
                return cls._convert_value(key, config.get("config_value"))
        except Exception as e:
            logger.warning(f"从 Redis 获取配置失败 [{key}]: {e}")

        # 返回默认值
        if default is not None:
            return default
        return cls.DEFAULTS.get(key)

    @classmethod
    async def get_all(cls, redis: Redis) -> dict[str, Any]:
        """获取所有 Modbus 配置

        从 Redis 批量读取 modbus_* 开头的配置。
        返回已类型转换的配置字典，可直接用于同步代码。
        """
        result = cls.DEFAULTS.copy()
        try:
            # 获取所有 modbus_* 配置的 Redis 键
            pattern = cls._get_redis_key("modbus_*")
            keys = await RedisCURD(redis).get_keys(pattern)

            if keys:
                values = await RedisCURD(redis).mget(keys)
                for _, value in zip(keys, values):
                    if value:
                        config = json.loads(value)
                        config_key = config.get("config_key", "")
                        if config_key.startswith("modbus_"):
                            result[config_key] = cls._convert_value(
                                config_key, config.get("config_value")
                            )
        except Exception as e:
            logger.warning(f"从 Redis 获取所有 Modbus 配置失败: {e}")

        return result
