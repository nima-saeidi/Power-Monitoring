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

                # خواندن رجیسترهای نگه‌دارنده (آرگومان slave حذف شد تا خطای unexpected keyword argument رخ ندهد)
                result = await self.client.read_holding_registers(address=address, count=count)
                
                if result.isError():
                    logger.warning(f"Modbus error on {self.host}: {result}")
                else:
                    return result.registers

            except asyncio.TimeoutError:
                logger.warning(f"Timeout reading from {self.host} (Attempt {attempt + 1}/{self.retries})")
            except ModbusException as e:
                logger.error(f"Modbus exception on {self.host}: {e}")
            
            await asyncio.sleep(1) # تاخیر قبل از تلاش مجدد
            
        # ثبت رویداد قطعی در صورت شکست تمام تلاش‌ها (طبق سند معماری)
        logger.error(f"All {self.retries} attempts failed for {self.host}")
        return None

    async def close(self):
        if self.client.connected:
            self.client.close()
