from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient('127.0.0.1', port=502)

if client.connect():
    print("اتصال به شبیه‌ساز با موفقیت انجام شد!\n")
    
    for i in range(5):
        # فقط address را می‌شود مستقیم داد، بقیه باید با نام (count, slave) باشند
        response = client.read_holding_registers(address=2, count=1)
        
        if not response.isError():
            value = response.registers[0]
            print(f"تست {i+1} - مقدار خوانده شده از آدرس 0: {value}")
        else:
            print(f"تست {i+1} - خطا در خواندن دیتا! (کد خطا: {response})")
            
        time.sleep(1)
        
    client.close()
else:
    print("خطا در اتصال به شبیه‌ساز. بررسی کنید سرور در حال اجرا باشد.")
