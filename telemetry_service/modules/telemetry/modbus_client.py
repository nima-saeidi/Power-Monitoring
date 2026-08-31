import asyncio
import inspect
import logging
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)

# ترتیب اولویت نام‌هایی که pymodbus در نسخه‌های مختلف برای شناسه‌ی slave/unit استفاده کرده است
_SLAVE_KWARG_CANDIDATES = ("slave", "device_id", "unit")

class ModbusReader:
    def __init__(self, host: str, port: int = 502, timeout: int = 3, retries: int = 3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.client = AsyncModbusTcpClient(self.host, port=self.port, timeout=self.timeout)

        # تشخیص یک‌باره‌ی نام صحیح پارامتر بر اساس نسخه‌ی نصب‌شده‌ی pymodbus
        self._slave_kwarg = self._detect_slave_kwarg()
        logger.debug(f"Detected pymodbus slave-id kwarg: '{self._slave_kwarg}'")

    @staticmethod
    def _detect_slave_kwarg(candidates=_SLAVE_KWARG_CANDIDATES) -> str:
        """
        بررسی امضای متد read_holding_registers در نسخه‌ی نصب‌شده‌ی pymodbus
        جهت پشتیبانی از slave / device_id / unit
        """
        try:
            params = inspect.signature(AsyncModbusTcpClient.read_holding_registers).parameters
        except (TypeError, ValueError):
            return candidates[0]

        for name in candidates:
            if name in params:
                return name
        return candidates[0]

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> bool:
        if not self.client.connected:
            await self.client.connect()
        return self.client.connected

    async def read_data(self, address: int, count: int = 5, slave: int = 1):
        for attempt in range(self.retries):
            try:
                is_connected = await self.connect()
                if not is_connected:
                    logger.error(f"Failed to connect to {self.host}:{self.port}")
                    await asyncio.sleep(1)
                    continue

                kwargs = {"count": count, self._slave_kwarg: slave}
                result = await self.client.read_input_registers(address, **kwargs)

                if result.isError():
                    logger.warning(f"Modbus error on {self.host}:{self.port} - {result}")
                else:
                    return result.registers

            except asyncio.TimeoutError:
                logger.warning(f"Timeout reading from {self.host}:{self.port} (Attempt {attempt + 1}/{self.retries})")
            except ModbusException as e:
                logger.error(f"Modbus exception on {self.host}:{self.port} - {e}")
            except TypeError as e:
                logger.warning(f"Signature mismatch on {self.host}, re-detecting kwarg: {e}")
                self._slave_kwarg = self._detect_slave_kwarg(
                    tuple(c for c in _SLAVE_KWARG_CANDIDATES if c != self._slave_kwarg)
                    + (self._slave_kwarg,)
                )
            except Exception as e:
                logger.error(f"Unexpected error reading from {self.host}:{self.port} - {e}")

            await asyncio.sleep(1)

        logger.error(f"All {self.retries} attempts failed for {self.host}:{self.port}")
        return None

    async def write_coil(self, address: int, value: bool, slave: int = 1) -> bool:
        for attempt in range(self.retries):
            try:
                is_connected = await self.connect()
                if not is_connected:
                    logger.error(f"Failed to connect to {self.host}:{self.port} for writing")
                    await asyncio.sleep(1)
                    continue

                kwargs = {self._slave_kwarg: slave}
                result = await self.client.write_coil(address, value, **kwargs)

                if result.isError():
                    logger.warning(f"Modbus write error on {self.host}:{self.port}, address {address}: {result}")
                else:
                    logger.info(f"Successfully wrote {value} to coil {address} on {self.host}:{self.port}")
                    return True

            except asyncio.TimeoutError:
                logger.warning(f"Timeout writing to {self.host}:{self.port} (Attempt {attempt + 1}/{self.retries})")
            except ModbusException as e:
                logger.error(f"Modbus exception writing to {self.host}:{self.port}: {e}")
            except TypeError as e:
                logger.warning(f"Signature mismatch on {self.host}, re-detecting kwarg: {e}")
                self._slave_kwarg = self._detect_slave_kwarg(
                    tuple(c for c in _SLAVE_KWARG_CANDIDATES if c != self._slave_kwarg)
                    + (self._slave_kwarg,)
                )
            except Exception as e:
                logger.error(f"Unexpected error writing to {self.host}:{self.port}: {e}")

            await asyncio.sleep(1)

        logger.error(f"All {self.retries} attempts failed for writing to {self.host}:{self.port}, address {address}")
        return False

    async def close(self):
        if self.client.connected:
            self.client.close()
