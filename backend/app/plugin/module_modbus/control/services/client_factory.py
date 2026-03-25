"""
Modbus 客户端抽象接口和实现

提供统一的 Modbus 客户端接口，支持 TCP 和 RTU_OVER_TCP 连接类型。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)


class IModbusClient(ABC):
    """Modbus 客户端抽象接口"""

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass

    @abstractmethod
    def read_holding_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        """读取保持寄存器"""
        pass

    @abstractmethod
    def read_input_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        """读取输入寄存器"""
        pass

    @abstractmethod
    def read_coils(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        """读取线圈"""
        pass

    @abstractmethod
    def read_discrete_inputs(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        """读取离散输入"""
        pass

    @abstractmethod
    def write_single_register(
        self, address: int, value: int, slave: int = 1
    ) -> dict[str, Any]:
        """写入单个寄存器"""
        pass

    @abstractmethod
    def write_single_coil(
        self, address: int, value: bool, slave: int = 1
    ) -> dict[str, Any]:
        """写入单个线圈"""
        pass


class TcpModbusClient(IModbusClient):
    """Modbus TCP 客户端"""

    def __init__(self, host: str, port: int = 502, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client: ModbusTcpClient | None = None

    def connect(self) -> bool:
        try:
            self._client = ModbusTcpClient(
                host=self.host, port=self.port, timeout=self.timeout
            )
            return self._client.connect()
        except Exception as e:
            logger.error(f"TCP 连接失败 {self.host}:{self.port} - {e}")
            return False

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def is_connected(self) -> bool:
        return self._client is not None and self._client.connected

    def read_holding_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_holding_registers(
                address=address, count=count, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.registers}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_input_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_input_registers(
                address=address, count=count, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.registers}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_coils(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_coils(address=address, count=count, slave=slave)
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.bits[:count]}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_discrete_inputs(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_discrete_inputs(
                address=address, count=count, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.bits[:count]}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_single_register(
        self, address: int, value: int, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.write_register(
                address=address, value=value, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_single_coil(
        self, address: int, value: bool, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.write_coil(address=address, value=value, slave=slave)
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class RtuOverTcpClient(IModbusClient):
    """
    RTU over TCP 客户端

    通过 TCP 连接串口服务器，但使用 RTU 帧格式。
    """

    def __init__(self, host: str, port: int = 502, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client: ModbusTcpClient | None = None

    def connect(self) -> bool:
        try:
            from pymodbus.transaction import ModbusRtuFramer

            self._client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
                framer=ModbusRtuFramer,  # 使用 RTU 帧格式
            )
            return self._client.connect()
        except Exception as e:
            logger.error(f"RTU over TCP 连接失败 {self.host}:{self.port} - {e}")
            return False

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def is_connected(self) -> bool:
        return self._client is not None and self._client.connected

    def read_holding_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_holding_registers(
                address=address, count=count, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.registers}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_input_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_input_registers(
                address=address, count=count, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.registers}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_coils(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_coils(address=address, count=count, slave=slave)
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.bits[:count]}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_discrete_inputs(
        self, address: int, count: int = 1, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.read_discrete_inputs(
                address=address, count=count, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True, "values": result.bits[:count]}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_single_register(
        self, address: int, value: int, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.write_register(
                address=address, value=value, slave=slave
            )
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_single_coil(
        self, address: int, value: bool, slave: int = 1
    ) -> dict[str, Any]:
        try:
            result = self._client.write_coil(address=address, value=value, slave=slave)
            if result.isError():
                return {"success": False, "error": str(result)}
            return {"success": True}
        except ModbusException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ModbusClientFactory:
    """Modbus 客户端工厂"""

    @staticmethod
    def create(
        connection_type: str,
        host: str,
        port: int = 502,
        timeout: int = 5,
        **kwargs,
    ) -> IModbusClient:
        """
        根据连接类型创建对应的客户端

        Args:
            connection_type: 连接类型 (TCP, RTU_OVER_TCP)
            host: IP 地址
            port: 端口
            timeout: 超时时间
            **kwargs: 额外参数（如 baud_rate, parity 等）

        Returns:
            IModbusClient 实例

        Raises:
            ValueError: 不支持的连接类型
        """
        connection_type = connection_type.upper()

        if connection_type == "TCP":
            return TcpModbusClient(host=host, port=port, timeout=timeout)
        elif connection_type == "RTU_OVER_TCP":
            return RtuOverTcpClient(host=host, port=port, timeout=timeout)
        else:
            raise ValueError(f"不支持的连接类型: {connection_type}")