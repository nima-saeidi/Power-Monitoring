import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)


class ModbusReader:
    def __init__(self, host: str, port: int = 502, timeout: int = 3, retries: int = 3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.client = AsyncModbusTcpClient(self.host, port=self.port, timeout=self.timeout)

    # امکان استفاده از async with برای بستن خودکار کانکشن
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> bool:
        if not self.client.connected:
            await self.client.connect()
        return self.client.connected

    async def read_data(self, address: int, count: int, slave_id: int = 1):
        for attempt in range(self.retries):
            try:
                is_connected = await self.connect()
                if not is_connected:
                    logger.error(f"Failed to connect to {self.host}")
                    continue

                # اصلاح: اضافه شدن پارامتر slave
                result = await self.client.read_holding_registers(
                    address=address,
                    count=count,
                    slave=slave_id
                )

                if result.isError():
                    logger.warning(f"Modbus error on {self.host}: {result}")
                else:
                    return result.registers

            except asyncio.TimeoutError:
                logger.warning(f"Timeout reading from {self.host} (Attempt {attempt + 1}/{self.retries})")
            except ModbusException as e:
                logger.error(f"Modbus exception on {self.host}: {e}")

            await asyncio.sleep(1)

        logger.error(f"All {self.retries} attempts failed for {self.host}")
        return None

    async def write_coil(self, address: int, value: bool, slave_id: int = 1) -> bool:
        """
        ارسال فرمان قطع/وصل (True/False) به یک کویل در تجهیز
        """
        for attempt in range(self.retries):
            try:
                is_connected = await self.connect()
                if not is_connected:
                    logger.error(f"Failed to connect to {self.host} for writing")
                    continue

                # اصلاح: اضافه شدن پارامتر slave
                result = await self.client.write_coil(
                    address=address,
                    value=value,
                    slave=slave_id
                )

                if result.isError():
                    logger.warning(f"Modbus write error on {self.host}, address {address}: {result}")
                else:
                    logger.info(f"Successfully wrote {value} to coil {address} on {self.host} (Slave {slave_id})")
                    return True

            except asyncio.TimeoutError:
                logger.warning(f"Timeout writing to {self.host} (Attempt {attempt + 1}/{self.retries})")
            except ModbusException as e:
                logger.error(f"Modbus exception writing to {self.host}: {e}")

            await asyncio.sleep(1)

        logger.error(f"All {self.retries} attempts failed for writing to {self.host}, address {address}")
        return False

    async def close(self):
        if self.client.connected:
            self.client.close()
