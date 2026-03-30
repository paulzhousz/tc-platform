"""
多从站 Modbus TCP PLC 仿真器

在同一个端口上模拟多个 Modbus 从站设备，使用不同的 slave ID。

使用方法:
    python scripts/modbus_simulator_multi.py
    python scripts/modbus_simulator_multi.py --port 15502 --slave-ids 1 2
"""

import argparse
import asyncio
import logging
import struct

try:
    from pymodbus.datastore import (
        ModbusDeviceContext,
        ModbusSequentialDataBlock,
        ModbusServerContext,
    )
    from pymodbus.pdu.device import ModbusDeviceIdentification
    from pymodbus.server import ModbusTcpServer
except ImportError:
    print("错误: pymodbus 未安装")
    print("请运行: uv add pymodbus>=3.8.0")
    exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultiSlaveSimulator")


def float_to_registers(value: float) -> tuple[int, int]:
    """将浮点数转换为两个 16 位寄存器值 (大端序)"""
    packed = struct.pack('>f', value)
    return struct.unpack('>HH', packed)


def int32_to_registers(value: int) -> tuple[int, int]:
    """将 32 位整数转换为两个 16 位寄存器值 (大端序)"""
    packed = struct.pack('>I', value)
    return struct.unpack('>HH', packed)


# Slave ID 1 的点位配置（简单测试设备）
SLAVE_1_CONFIG = {
    "name": "测试PLC设备",
    "holding": {
        0: ("温度设定值", 25.0, "FLOAT"),
        2: ("湿度设定值", 60.0, "FLOAT"),
        4: ("风机频率", 30.0, "FLOAT"),
        6: ("阀门开度", 50.0, "FLOAT"),
    },
    "input": {
        0: ("当前温度", 24.5, "FLOAT"),
        2: ("当前湿度", 58.0, "FLOAT"),
        4: ("当前频率", 30.0, "FLOAT"),
        6: ("压力值", 1013.0, "FLOAT"),
    },
    "coil": {
        0: ("运行状态", True),
        1: ("故障状态", False),
        2: ("自动模式", True),
    },
    "discrete": {}
}

# Slave ID 2 的点位配置（智能空调系统）
SLAVE_2_CONFIG = {
    "name": "智能空调系统 PLC",
    "holding": {
        # 地址偏移: (名称, 初始值, 数据类型)
        0: ("室内温度", 25.5, "FLOAT"),
        2: ("室内湿度", 60.0, "FLOAT"),
        4: ("设定温度", 24.0, "FLOAT"),
        6: ("风机频率", 30.0, "FLOAT"),
        8: ("阀门开度", 50.0, "FLOAT"),
        10: ("回风温度", 26.0, "FLOAT"),
        12: ("送风温度", 18.0, "FLOAT"),
        14: ("运行模式", 1, "INT16"),  # 0=停机,1=制冷,2=制热,3=通风
        15: ("设备状态", 1, "INT16"),  # 0=故障,1=正常运行,2=待机
    },
    "input": {
        0: ("压缩机电流", 5.2, "FLOAT"),
        2: ("风机电流", 1.5, "FLOAT"),
        4: ("运行时长", 1200, "INT32"),  # 分钟
        6: ("故障代码", 0, "INT16"),
    },
    "coil": {
        0: ("电源开关", True),
        1: ("风机启动", True),
        2: ("压缩机启动", True),
        3: ("加热器", False),
        4: ("新风阀", True),
    },
    "discrete": {
        0: ("高温报警", False),
        1: ("低温报警", False),
        2: ("滤网报警", False),
        3: ("漏水报警", False),
    }
}


class MultiSlavePLC:
    """多从站虚拟 PLC"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 15502,
        slave_ids: list[int] = [1, 2]
    ):
        self.host = host
        self.port = port
        self.slave_ids = slave_ids
        self.context = None

        # 从站配置映射
        self.slave_configs = {
            1: SLAVE_1_CONFIG,
            2: SLAVE_2_CONFIG
        }

    def create_slave_context(self, slave_id: int) -> ModbusDeviceContext:
        """创建单个从站的数据存储区"""
        holding_registers = ModbusSequentialDataBlock(0, [0] * 100)
        input_registers = ModbusSequentialDataBlock(0, [0] * 100)
        coils = ModbusSequentialDataBlock(0, [False] * 100)
        discrete_inputs = ModbusSequentialDataBlock(0, [False] * 100)

        return ModbusDeviceContext(
            di=discrete_inputs,
            co=coils,
            hr=holding_registers,
            ir=input_registers
        )

    def create_datastore(self) -> ModbusServerContext:
        """创建多从站数据存储区"""
        devices = {}
        for slave_id in self.slave_ids:
            devices[slave_id] = self.create_slave_context(slave_id)

        # single=False 表示支持多从站
        context = ModbusServerContext(devices=devices, single=False)
        self.context = context
        return context

    def set_initial_values(self):
        """设置所有从站的初始值"""
        for slave_id in self.slave_ids:
            config = self.slave_configs.get(slave_id)
            if not config:
                continue

            slave = self.context[slave_id]
            name = config.get("name", f"Slave {slave_id}")

            logger.info("=" * 50)
            logger.info("Slave ID %d: %s", slave_id, name)
            logger.info("=" * 50)

            # 设置保持寄存器
            holding = config.get("holding", {})
            if holding:
                logger.info("\n保持寄存器 (Holding Registers):")
                for addr, (tag_name, value, dtype) in holding.items():
                    if dtype == "FLOAT":
                        reg1, reg2 = float_to_registers(float(value))
                        slave.setValues(3, addr, [reg1, reg2])
                        logger.info(f"  地址 {40001 + addr}: {tag_name} = {value}")
                    else:
                        slave.setValues(3, addr, [int(value)])
                        logger.info(f"  地址 {40001 + addr}: {tag_name} = {value}")

            # 设置输入寄存器
            inputs = config.get("input", {})
            if inputs:
                logger.info("\n输入寄存器 (Input Registers):")
                for addr, (tag_name, value, dtype) in inputs.items():
                    if dtype == "FLOAT":
                        reg1, reg2 = float_to_registers(float(value))
                        slave.setValues(4, addr, [reg1, reg2])
                        logger.info(f"  地址 {30001 + addr}: {tag_name} = {value}")
                    elif dtype == "INT32":
                        reg1, reg2 = int32_to_registers(int(value))
                        slave.setValues(4, addr, [reg1, reg2])
                        logger.info(f"  地址 {30001 + addr}: {tag_name} = {value}")
                    else:
                        slave.setValues(4, addr, [int(value)])
                        logger.info(f"  地址 {30001 + addr}: {tag_name} = {value}")

            # 设置线圈
            coils = config.get("coil", {})
            if coils:
                logger.info("\n线圈 (Coils):")
                for addr, (tag_name, value) in coils.items():
                    slave.setValues(1, addr, [value])
                    logger.info(f"  地址 {addr + 1}: {tag_name} = {'ON' if value else 'OFF'}")

            # 设置离散输入
            discrete = config.get("discrete", {})
            if discrete:
                logger.info("\n离散输入 (Discrete Inputs):")
                for addr, (tag_name, value) in discrete.items():
                    slave.setValues(2, addr, [value])
                    logger.info(f"  地址 {addr + 1}: {tag_name} = {'ON' if value else 'OFF'}")

            logger.info("")

    def get_identity(self) -> ModbusDeviceIdentification:
        """获取设备标识"""
        identity = ModbusDeviceIdentification()
        identity.VendorName = "Virtual Multi-Slave PLC"
        identity.ProductCode = "VMPLC"
        identity.ProductName = "多从站 Modbus 仿真器"
        identity.ModelName = "VMPLC-200"
        identity.MajorMinorRevision = "1.0.0"
        return identity

    async def start(self):
        """启动服务器"""
        context = self.create_datastore()
        self.set_initial_values()

        slave_list = ", ".join(map(str, self.slave_ids))
        logger.info(f"启动 Modbus TCP 服务器: {self.host}:{self.port}")
        logger.info(f"从站 ID 列表: [{slave_list}]")
        logger.info("按 Ctrl+C 停止服务器\n")

        server = ModbusTcpServer(
            context=context,
            identity=self.get_identity(),
            address=(self.host, self.port)
        )
        await server.serve_forever()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多从站 Modbus TCP PLC 仿真器"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=15502,
        help="监听端口 (默认: 15502)"
    )
    parser.add_argument(
        "--slave-ids",
        nargs="+",
        type=int,
        default=[1, 2],
        help="从站 ID 列表 (默认: 1 2)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试日志"
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    plc = MultiSlavePLC(
        host=args.host,
        port=args.port,
        slave_ids=args.slave_ids
    )

    try:
        asyncio.run(plc.start())
    except KeyboardInterrupt:
        logger.info("\n服务器已停止")


if __name__ == "__main__":
    main()
