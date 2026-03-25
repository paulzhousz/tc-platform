"""
Modbus 连接池管理

为每个设备维护独立的连接池，支持并发访问。
"""

import logging
import threading
from queue import Empty, Queue
from typing import Any

from app.config.setting import settings
from app.plugin.module_modbus.models import DeviceModel
from app.plugin.module_modbus.control.services.client_factory import (
    IModbusClient,
    ModbusClientFactory,
)

logger = logging.getLogger(__name__)


class ModbusConnectionPool:
    """
    Modbus 连接池

    为每个设备维护独立的连接池，支持并发访问。
    """

    def __init__(self, max_connections_per_device: int | None = None):
        self.max_connections = max_connections_per_device or settings.MODBUS_POOL_SIZE
        # {device_id: Queue[IModbusClient]}
        self._pools: dict[int, Queue] = {}
        # {device_id: DeviceModel} 设备配置缓存
        self._device_configs: dict[int, DeviceModel] = {}
        self._lock = threading.Lock()

    def initialize(self, devices: list[DeviceModel]) -> None:
        """
        初始化连接池

        Args:
            devices: 设备列表
        """
        with self._lock:
            for device in devices:
                self._init_device_pool(device)

    def _init_device_pool(self, device: DeviceModel) -> bool:
        """
        初始化单个设备的连接池

        Args:
            device: 设备模型

        Returns:
            bool: 是否成功建立至少一个连接
        """
        pool = Queue(maxsize=self.max_connections)
        connected_count = 0

        for i in range(self.max_connections):
            try:
                client = ModbusClientFactory.create(
                    connection_type=device.connection_type,
                    host=device.host,
                    port=device.port,
                    timeout=settings.MODBUS_CONNECT_TIMEOUT,
                )
                if client.connect():
                    pool.put(client)
                    connected_count += 1
                else:
                    logger.warning(f"设备 {device.name} 连接 {i+1} 初始化失败")
            except Exception as e:
                logger.error(f"设备 {device.name} 连接初始化异常: {e}")

        # 只有至少有一个成功连接才添加到池中
        if connected_count > 0:
            self._pools[device.id] = pool
            self._device_configs[device.id] = device
            logger.info(
                f"设备 {device.name} 连接池初始化完成: "
                f"{connected_count}/{self.max_connections} 连接"
            )
            return True
        else:
            logger.error(f"设备 {device.name} 连接池初始化失败: 无法建立任何连接")
            return False

    def add_device(self, device: DeviceModel) -> bool:
        """
        添加设备到连接池

        Args:
            device: 设备模型

        Returns:
            bool: 是否成功建立连接

        Raises:
            ConnectionError: 无法建立任何连接时抛出
        """
        with self._lock:
            if device.id in self._pools:
                # 已存在，检查是否有可用连接
                return self._pools[device.id].qsize() > 0

            success = self._init_device_pool(device)
            if not success:
                raise ConnectionError(
                    f"无法连接到设备 {device.name}，请确认设备已启动"
                )
            return True

    def remove_device(self, device_id: int) -> None:
        """
        移除设备的连接池

        Args:
            device_id: 设备 ID
        """
        with self._lock:
            if device_id in self._pools:
                pool = self._pools.pop(device_id)
                # 关闭所有连接
                while not pool.empty():
                    try:
                        client = pool.get_nowait()
                        client.close()
                    except Exception:
                        pass
                self._device_configs.pop(device_id, None)

    def acquire(
        self, device_id: int, timeout: float | None = None
    ) -> IModbusClient | None:
        """
        获取连接

        Args:
            device_id: 设备 ID
            timeout: 超时时间（秒）

        Returns:
            IModbusClient 或 None
        """
        timeout = timeout or settings.MODBUS_READ_TIMEOUT

        if device_id not in self._pools:
            logger.error(f"设备 {device_id} 未初始化连接池")
            return None

        try:
            client = self._pools[device_id].get(timeout=timeout)
            return client
        except Empty:
            logger.warning(f"设备 {device_id} 获取连接超时")
            return None

    def release(self, device_id: int, client: IModbusClient) -> None:
        """
        释放连接回池

        Args:
            device_id: 设备 ID
            client: Modbus 客户端
        """
        if device_id in self._pools:
            try:
                self._pools[device_id].put_nowait(client)
            except Exception:
                # 队列已满，关闭连接
                client.close()

    def health_check(self, device_id: int) -> dict[str, Any]:
        """
        健康检查

        Args:
            device_id: 设备 ID

        Returns:
            健康状态字典
        """
        if device_id not in self._pools:
            return {"healthy": False, "reason": "设备未初始化"}

        pool = self._pools[device_id]
        available = pool.qsize()

        return {
            "healthy": available > 0,
            "available_connections": available,
            "max_connections": self.max_connections,
        }

    def get_all_status(self) -> dict[int, dict[str, Any]]:
        """
        获取所有设备的连接状态

        Returns:
            {device_id: health_check_result}
        """
        result = {}
        for device_id in self._pools:
            result[device_id] = self.health_check(device_id)
        return result

    def close_all(self) -> None:
        """关闭所有连接"""
        with self._lock:
            for _device_id, pool in self._pools.items():
                while not pool.empty():
                    try:
                        client = pool.get_nowait()
                        client.close()
                    except Exception:
                        pass
            self._pools.clear()
            self._device_configs.clear()


# 全局连接池实例
connection_pool = ModbusConnectionPool()