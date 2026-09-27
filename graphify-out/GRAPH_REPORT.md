# Graph Report - electro  (2026-09-27)

## Corpus Check
- Corpus is ~45,078 words - fits in a single context window. You may not need a graph.

## Summary
- 1322 nodes · 3161 edges · 84 communities (61 shown, 23 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 293 edges (avg confidence: 0.94)
- Token cost: 64,550 input · 0 output

## Community Hubs (Navigation)
- Audit Log Models & Services
- Feeder Excel Import
- Logging Service Consumer
- Docker Services & Requirements
- Locations Module
- Modbus Telemetry Reader
- Notification Models & Repo
- Migrations & Domain Constants
- Database Sessions
- Links Module
- Alert Dispatch
- Telemetry Service API
- Auth Schemas & Router
- Report Export (Excel/PDF)
- Auth Service & Password Reset
- User Management
- Main API App & Errors
- RabbitMQ Audit Logging
- Notification Service Logic
- JWT & Password Security
- Notification Providers
- User Repository & Lockout
- Service Configs
- Feeders Module
- Main API Telemetry Router
- Postgres Write Handlers
- RabbitMQ Publisher
- Background Audit Logging
- Feeders Router
- Telemetry Proxy Client
- Logging & Graylog Handlers
- Auth Endpoints
- System Settings Repo
- Telemetry Schemas
- Two-Step Feeder Commands
- Energy Analytics & Forecast
- Settings Router
- Live Load Monitor
- Main API Telemetry Repo
- Notification Service Config
- Feeder Create & Command Routes
- InfluxDB Telemetry Repo
- Telemetry Service Layer
- Postgres Storage Worker
- Feeder Service
- Timeseries Storage Worker
- InfluxDB Writer
- InfluxDB Connection Manager
- Email HTML Templates
- WebSocket Auth
- Feeder Status Reporting
- Dashboard Summary
- Notification WebSocket Manager
- Telemetry WebSocket Manager
- Telemetry WS Consumer
- Broker Dependencies
- User & Role Queries
- Alembic Env
- Graylog Client
- Rate Limiting
- Profile Read
- Profile Update
- Graylog Input Setup
- Docker Network

## God Nodes (most connected - your core abstractions)
1. `send_audit_log()` - 51 edges
2. `RabbitMQPublisher` - 50 edges
3. `AuthService` - 41 edges
4. `schedule_audit_log()` - 33 edges
5. `TelemetryService` - 30 edges
6. `Feeder` - 29 edges
7. `LocationService` - 28 edges
8. `UserRepository` - 25 edges
9. `NotificationRepository` - 24 edges
10. `NotificationPriority` - 23 edges

## Surprising Connections (you probably didn't know these)
- `root requirements (UTF-16 encoded)` --semantically_similar_to--> `main_api requirements`  [INFERRED] [semantically similar]
  req.txt → main_api/req.txt
- `Localhost-only Port Binding Policy` --semantically_similar_to--> `On-Premise Deployment on University Server/LAN`  [INFERRED] [semantically similar]
  docker-compose.yml → monitoring-1 - متن جلسه (فارسی).md
- `/telemetry/ws WebSocket Endpoint` --conceptually_related_to--> `api (Main API Service)`  [INFERRED]
  test.html → docker-compose.yml
- `Excel Bulk Import` --conceptually_related_to--> `reportlab + openpyxl (report export)`  [AMBIGUOUS]
  monitoring-1 - متن جلسه (فارسی).md → main_api/req.txt
- `aio-pika (RabbitMQ client)` --conceptually_related_to--> `rabbitmq (RabbitMQ Broker)`  [INFERRED]
  main_api/req.txt → docker-compose.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Telemetry Ingestion Pipeline via RabbitMQ** — docker_compose_telemetry, docker_compose_rabbitmq, docker_compose_postgres_storage, docker_compose_timeseries_storage, docker_compose_influxdb, docker_compose_db [INFERRED 0.85]
- **Centralized Logging Stack (Graylog)** — docker_compose_graylog, docker_compose_mongo, docker_compose_opensearch, docker_compose_graylog_init, docker_compose_logging [EXTRACTED 1.00]
- **Feeder Status Evaluation and Alerting Flow** — monitoring_1____________________five_parameters, monitoring_1____________________alpha_beta_thresholds, monitoring_1____________________notifications, monitoring_1____________________filters, monitoring_1____________________university_map [INFERRED 0.75]

## Communities (84 total, 23 thin omitted)

### Community 0 - "Audit Log Models & Services"
Cohesion: 0.06
Nodes (53): get_audit_log_service(), get_command_log_service(), get_device_test_log_service(), AsyncSession, AuditLog, CommandLog, DeviceTestLog, Base (+45 more)

### Community 1 - "Feeder Excel Import"
Cohesion: 0.06
Nodes (43): DataFrame, influxdb_client_client_write_api, normalize_energy_role(), تبدیل مقادیر آزاد (Producer، «تولیدکننده»، ...) به consumer / producer., _as_float(), _as_int(), _as_role(), _clean() (+35 more)

### Community 2 - "Logging Service Consumer"
Cohesion: 0.07
Nodes (44): ambiguous_python_import_5a1e92d63a81, ambiguous_python_import_8411280287f0, ambiguous_python_import_bc63c2f8b964, ambiguous_python_import_d57eca47521e, contextlib, fastapi_middleware_cors, _declare_logs_queue_with_dlq(), process_audit_message() (+36 more)

### Community 3 - "Docker Services & Requirements"
Cohesion: 0.07
Nodes (53): Alembic Migration on API Startup, api (Main API Service), db (TimescaleDB/PostgreSQL), graylog (Graylog 4.3), graylog-init (GELF Input Provisioning), influxdb (InfluxDB 2.7), InfluxDB Auto Setup (org/bucket/token from .env), Localhost-only Port Binding Policy (+45 more)

### Community 4 - "Locations Module"
Cohesion: 0.09
Nodes (29): Location, Base, LocationRepository, format_location(), AsyncSession, create_campus_with_subsections(), create_location(), delete_location() (+21 more)

### Community 5 - "Modbus Telemetry Reader"
Cohesion: 0.06
Nodes (23): ambiguous_python_import_7fb2a87b7352, inspect, modules_telemetry_modbus_client, pymodbus_client, pymodbus_exceptions, ModbusReader, بررسی امضای متد read_holding_registers در نسخه‌ی نصب‌شده‌ی pymodbus جهت…, apply_register_config() (+15 more)

### Community 6 - "Notification Models & Repo"
Cohesion: 0.08
Nodes (33): Notification, NotificationTemplate, Base, قالب‌های از پیش تعریف شده برای نوتیفیکیشن, NotificationRepository, Any, AsyncSession, datetime (+25 more)

### Community 7 - "Migrations & Domain Constants"
Cohesion: 0.07
Nodes (6): alembic, ambiguous_python_import_a868d1a0f2f0, httpx, مقادیر ثابت دامنه‌ی سامانه که بین چند ماژول مشترک است., sqlalchemy_dialects, typing

### Community 8 - "Database Sessions"
Cohesion: 0.14
Nodes (19): ambiguous_python_import_20bf2ce79bb5, ambiguous_python_import_90819600184b, ambiguous_python_import_d78722a24516, collections, datetime, logging_config, Run migrations in 'offline' mode. This configures the context with just a URL…, run_migrations_offline() (+11 more)

### Community 9 - "Links Module"
Cohesion: 0.12
Nodes (23): main_api_common_message_broker, Link, Base, LinkRepository, AsyncSession, حذف یک لینک از دیتابیس, create_link(), delete_link() (+15 more)

### Community 10 - "Alert Dispatch"
Cohesion: 0.13
Nodes (28): asyncio, enum, fastapi, main_api_core_rabbitmq_publisher, dispatch_alert(), Any, AsyncSession, ارسال هشدارهای سامانه (قطعی فیدر، وضعیت هشدار/بحرانی بار و ...) در دو کانال: -… (+20 more)

### Community 11 - "Telemetry Service API"
Cohesion: 0.09
Nodes (31): ambiguous_python_import_4a30b1523a17, hmac, modules_telemetry, modules_telemetry_service, re, CoilWriteRequest, create_telemetry_entry(), get_energy() (+23 more)

### Community 12 - "Auth Schemas & Router"
Cohesion: 0.20
Nodes (23): jose, get_db(), AdminRegisterRequest, ChangePasswordRequest, ForgotPasswordRequest, ForgotPasswordResponse, LoginRequest, BaseModel (+15 more)

### Community 13 - "Report Export (Excel/PDF)"
Cohesion: 0.11
Nodes (25): BytesIO, dataclasses, io, build_excel_report(), build_pdf_report(), _cell(), _clean_timestamp(), Any (+17 more)

### Community 14 - "Auth Service & Password Reset"
Cohesion: 0.13
Nodes (15): build_reset_code_email_html(), قالب HTML راست‌به‌چین (RTL) ایمیل کد تأیید بازیابی رمز عبور, اعتبارسنجی پسورد ورودی با پسورد هش‌شده, verify_password(), AuthService, _otp_digest(), _password_fingerprint(), BackgroundTasks (+7 more)

### Community 15 - "User Management"
Cohesion: 0.15
Nodes (16): hash_password(), هش کردن پسورد خام با استفاده از bcrypt, delete_user(), delete, put, update_user(), BaseModel, field_validator (+8 more)

### Community 16 - "Main API App & Errors"
Cohesion: 0.12
Nodes (24): Exception, exception_handler, fastapi_exceptions, fastapi_responses, IntegrityError, custom_rate_limit_handler(), global_exception_handler(), http_exception_handler() (+16 more)

### Community 17 - "RabbitMQ Audit Logging"
Cohesion: 0.11
Nodes (20): aio_pika, ambiguous_python_import_bb55f048d972, functools, json, AbstractChannel, Any, ارسال یک رویداد لاگ به صف logs_queue با همان ساختار LogCreate که…, send_service_log() (+12 more)

### Community 18 - "Notification Service Logic"
Cohesion: 0.15
Nodes (15): NotificationPreference, تنظیمات نوتیفیکیشن کاربر, دریافت تنظیمات نوتیفیکیشن کاربر, NotificationService, Any, AsyncSession, BackgroundTasks, ارسال هشدار سیستمی با ثبت لاگ (+7 more)

### Community 19 - "JWT & Password Security"
Cohesion: 0.11
Nodes (18): bcrypt, fastapi_security, jwt, jwt_exceptions, create_access_token(), create_token(), decode_token(), timedelta (+10 more)

### Community 20 - "Notification Providers"
Cohesion: 0.13
Nodes (16): ABC, aiosmtplib, ambiguous_python_import_217b385085d6, ambiguous_python_import_f2c53e5435b2, email_message, BaseNotificationProvider, NotificationChannel, NotificationPriority (+8 more)

### Community 21 - "User Repository & Lockout"
Cohesion: 0.10
Nodes (12): get_auth_service(), AsyncSession, AsyncSession, AsyncSession, datetime, لیست ایمیل کاربران فعالی که ادمین برایشان ارسال نوتیفیکیشن را فعال کرده است…, بروزرسانی مستقیم و همزمان (synchronous) وضعیت تلاش‌های ناموفق ورود/قفل حساب.…, UserRepository (+4 more)

### Community 22 - "Service Configs"
Cohesion: 0.11
Nodes (15): Config, BaseSettings, Settings, BaseSettings, Settings, os, pathlib, BaseSettings (+7 more)

### Community 23 - "Feeders Module"
Cohesion: 0.13
Nodes (11): Feeder, Base, FeederRepository, AsyncSession, FeederCreate, overrides_of(), datetime, ذخیره نتیجه آخرین Polling یک فیدر (توسط telemetry_service گزارش می‌شود). این… (+3 more)

### Community 24 - "Main API Telemetry Router"
Cohesion: 0.20
Nodes (20): export_feeder_report_excel(), export_feeder_report_pdf(), export_report(), get_active_feeders(), get_chart_data(), get_energy(), get_forecast(), get_history() (+12 more)

### Community 25 - "Postgres Write Handlers"
Cohesion: 0.17
Nodes (18): ambiguous_python_import_363361d64c1c, ambiguous_python_import_ec0fb716adf3, _extract_id(), handle_db_write_event(), Any, فیلتر کردن کلیدهای نامعتبر و تصحیح فیلدهای خاص مثل metadata و datetime, شناسه‌ی رکورد برای update/delete. main_api برای کاربران شناسه را در سطح بالای…, پردازش انواع عملیات نوشتنی روی دیتابیس بر اساس پیلود پیام (+10 more)

### Community 26 - "RabbitMQ Publisher"
Cohesion: 0.12
Nodes (12): Any, RabbitMQPublisher, کلاس مدیریت اتصال و انتشار رویدادها به RabbitMQ از طریق Topic Exchange, Declare صف با x-dead-letter-exchange. اگر صف از قبل (قبل از این تغییر) با…, بررسی فعال بودن اتصال برای Health Check, برقراری اتصال پایدار به RabbitMQ و راه‌اندازی Topic Exchange, قطع ایمن اتصال در زمان خاموش شدن برنامه, متد اصلی برای انتشار رویدادها به Topic Exchange. تمام سرویس‌ها باید از این متد… (+4 more)

### Community 27 - "Background Audit Logging"
Cohesion: 0.20
Nodes (9): BackgroundTasks, ارسال لاگ‌های عمومی و امنیتی (ورود، تغییرات سیستم، خطاها، نوتیفیکیشن‌ها و ...), ثبت audit log بدون بلاک کردن پاسخ درخواست. اگر BackgroundTasks در دسترس باشد…, schedule_audit_log(), send_audit_log(), BackgroundTasks, A helper method to publish events to RabbitMQ. Automatically adds routing_key,…, BackgroundTasks (+1 more)

### Community 28 - "Feeders Router"
Cohesion: 0.15
Nodes (15): delete_feeder(), download_feeder_excel_template(), get_feeder(), get_feeders(), get_message_broker(), delete, get, put (+7 more)

### Community 29 - "Telemetry Proxy Client"
Cohesion: 0.18
Nodes (11): internal_headers(), parse_time(), Any, datetime, نکته کارایی: برای گزارش‌های بزرگ (بازه‌های زمانی طولانی/window ریز) کوئری…, تبدیل زمان ورودی کاربر به datetime: «now()»، زمان نسبی مثل «-24h» / «-7d» یا…, پروکسی دریافت داده‌های تفکیک‌شده نمودار از میکروسرویس تلمتری, telemetry_service همه‌ی اندپوینت‌هایش را پشت کلید مشترک INTERNAL_API_KEY گذاشته… (+3 more)

### Community 30 - "Logging & Graylog Handlers"
Cohesion: 0.15
Nodes (12): ambiguous_python_import_18570834da53, ambiguous_python_import_f19bfe42a94c, graypy, influxdb_client, Logger, logging_handlers, CustomFormatter, get_logger() (+4 more)

### Community 31 - "Auth Endpoints"
Cohesion: 0.21
Nodes (16): change_password(), forgot_password(), login(), BackgroundTasks, limit, post, Request, تغییر رمز عبور توسط کاربر لاگین‌شده (+8 more)

### Community 32 - "System Settings Repo"
Cohesion: 0.22
Nodes (10): Base, SystemSetting, Any, AsyncSession, SettingRepository, AsyncSession, BackgroundTasks, دریافت تنظیمات سیستم. ابتدا از کش خوانده می‌شود. در صورت عدم وجود در دیتابیس،… (+2 more)

### Community 33 - "Telemetry Schemas"
Cohesion: 0.17
Nodes (15): ChartDataPoint, DeviceAlertSchema, BaseModel, مدل انتشار هشدارهای وضعیت تجهیزات., یک نقطه از داده‌های نمودار., پاسخ داده‌های نمودار تله‌متری., مدل ورودی برای ثبت داده در InfluxDB., مدل خروجی برای API، وب‌سوکت و کلاینت‌ها. (+7 more)

### Community 34 - "Two-Step Feeder Commands"
Cohesion: 0.21
Nodes (14): hashlib, انتشار مستقیم یک پیام نوتیفیکیشن (ایمیل/پیامک) به صف notification_events. ارسال…, send_notification_to_queue(), build_command_code_email_html(), ایمیل کد تأیید فرمان قطع/وصل, _code_digest(), confirm_command(), _prune() (+6 more)

### Community 35 - "Energy Analytics & Forecast"
Cohesion: 0.21
Nodes (12): ambiguous_python_import_78d81c03b82c, ambiguous_python_import_e7a60a81023c, _feeder_filter(), flux_location(), get_energy(), get_forecast(), datetime, محاسبات تحلیلی روی داده‌های InfluxDB: انرژی (انتگرال توان) و پیش‌بینی ساعتی… (+4 more)

### Community 36 - "Settings Router"
Cohesion: 0.32
Nodes (10): get_system_settings(), AsyncSession, get, put, update_system_settings(), Config, BaseModel, SettingResponse (+2 more)

### Community 37 - "Live Load Monitor"
Cohesion: 0.22
Nodes (7): _Entity, evaluate_load(), LiveMonitor, بعد از تغییر فیدر/لینک/تنظیمات، دفعه‌ی بعد اطلاعات دوباره خوانده شود., داده‌ی خام فیدر را با وضعیت بار غنی می‌کند و تغییر وضعیت‌ها را اعمال می‌کند., وضعیت و درصد بار بر اساس جریان و جریان مجاز., _StatusChange

### Community 38 - "Main API Telemetry Repo"
Cohesion: 0.24
Nodes (9): AsyncSession, ذخیره داده تله‌متری جدید در دیتابیس رابطه‌ای., TelemetryRepository, ActiveFeederConfig, Config, BaseModel, TelemetryBase, TelemetryCreate (+1 more)

### Community 39 - "Notification Service Config"
Cohesion: 0.18
Nodes (9): computed_field, BaseSettings, Settings, NotificationChannel, NotificationPayload, BaseModel, Enum, str (+1 more)

### Community 40 - "Feeder Create & Command Routes"
Cohesion: 0.24
Nodes (12): confirm_feeder_command(), create_feeder(), get_feeder_service(), import_feeders_from_excel(), AsyncSession, limit, post, Request (+4 more)

### Community 41 - "InfluxDB Telemetry Repo"
Cohesion: 0.21
Nodes (5): datetime, TelemetryCreate, TelemetryResponse, تبدیل تاریخ به فرمت استاندارد RFC3339 برای InfluxDB, TelemetryRepository

### Community 42 - "Telemetry Service Layer"
Cohesion: 0.21
Nodes (8): datetime, TelemetryCreate, TelemetryResponse, ۱. ذخیره در InfluxDB و ۲. انتشار روی Redis برای اطلاع لحظه‌ای Main API, دریافت آخرین دیتای پایش‌شده فیدر, دریافت دیتای تاریخی و گزارش فیدر, دریافت داده‌های نمودار جهت نمایش در فرانت‌اند, TelemetryService

### Community 43 - "Postgres Storage Worker"
Cohesion: 0.22
Nodes (10): ambiguous_python_import_a4e0744fbfde, ambiguous_python_import_e0d7deaa04d8, _declare_main_queue_with_dlq(), process_message(), IncomingMessage, پردازش هر پیام دریافتی از صف RabbitMQ, Declare صف اصلی با آرگومان x-dead-letter-exchange. اگر این صف از قبل (قبل از…, حلقه اصلی اجرای کانسومر و اتصال پایدار به RabbitMQ (+2 more)

### Community 44 - "Feeder Service"
Cohesion: 0.29
Nodes (3): FeederService, BackgroundTasks, A helper method to publish events to RabbitMQ. Automatically adds routing_key,…

### Community 45 - "Timeseries Storage Worker"
Cohesion: 0.29
Nodes (8): ambiguous_python_import_7a39148dc34b, handle_telemetry_metric(), دریافت پیام، استخراج داده‌ها و ارسال به InfluxDB, _declare_main_queue_with_dlq(), main(), process_message(), IncomingMessage, مشابه توضیح در postgres_storage_service/main.py: declare صف با DLQ، با fallback…

### Community 46 - "InfluxDB Writer"
Cohesion: 0.22
Nodes (5): ambiguous_python_import_9dd8dea1acab, ثبت ۵ پارامتر الکتریکی به صورت Point در InfluxDB, تبدیل ایمن مقادیر با پشتیبانی از مقادیر None یا رشته‌های خراب, _safe_float(), TimeSeriesDB

### Community 47 - "InfluxDB Connection Manager"
Cohesion: 0.20
Nodes (6): ambiguous_python_import_ef06596c8cee, influxdb_client_client_influxdb_client_async, InfluxDBClientAsync, get_influx_write_api(), InfluxDBManager, Dependency برای دریافت Write API جهت ثبت داده‌ها

### Community 48 - "Email HTML Templates"
Cohesion: 0.25
Nodes (8): html, build_feeder_offline_email_html(), build_load_alert_email_html(), _card_email_html(), قالب‌های HTML ایمیل. محتوای ساخته‌شده در اینجا به همراه نسخه متنی (plain text)…, قالب مشترک ایمیل‌های هشدار و کد تأیید (RTL، هم‌سبک با قالب قطعی فیدر), ایمیل هشدار بار فیدر/لینک (وضعیت هشدار یا بحرانی نسبت به جریان مجاز), قالب HTML راست‌به‌چین (RTL) ایمیل هشدار قطعی فیدر

### Community 49 - "WebSocket Auth"
Cohesion: 0.22
Nodes (9): authenticate_websocket(), get_current_user(), AsyncSession, احراز هویت وب‌سوکت با توکن query (?token=...). از یک سشن کوتاه‌مدت استفاده…, websocket, وب‌سوکت اختصاصی کاربر برای دریافت زنده نوتیفیکیشن‌ها و هشدارها مسیر اتصال:…, websocket_notifications(), websocket (+1 more)

### Community 50 - "Feeder Status Reporting"
Cohesion: 0.33
Nodes (5): post, report_feeder_status(), FeederStatusUpdate, AsyncSession, TelemetryService

### Community 51 - "Dashboard Summary"
Cohesion: 0.32
Nodes (8): get_live(), get_summary(), AsyncSession, get, _status_counts(), نوع فیدر؛ اگر روی فیدر تعریف نشده باشد از نوع پست آن گرفته می‌شود., role_of(), _energy_rows()

### Community 52 - "Notification WebSocket Manager"
Cohesion: 0.39
Nodes (3): NotificationConnectionManager, WebSocket, ارسال پیام به تمام تب‌های باز یک کاربر خاص؛ اتصال‌های قطع‌شده حذف می‌شوند

### Community 53 - "Telemetry WebSocket Manager"
Cohesion: 0.39
Nodes (3): ConnectionManager, WebSocket, ارسال داده به کلاینت‌های متصل (فقط کلاینت‌هایی که همین فیدر یا همه‌ی فیدرها را…

### Community 54 - "Telemetry WS Consumer"
Cohesion: 0.29
Nodes (3): AbstractIncomingMessage, رویدادهای تله‌متری را از RabbitMQ می‌خواند و به کلاینت‌های وب‌سوکت…, TelemetryWebSocketConsumer

### Community 55 - "Broker Dependencies"
Cohesion: 0.38
Nodes (5): get_rabbitmq_publisher(), تابع وابستگی (Dependency Injection) برای استفاده در FastAPI, ارسال لاگ‌های سیستمی (رویدادهای عمومی، خطاها و ...) به سرویس لاگ. توجه: این…, send_log_to_rabbitmq(), این ماژول قبلاً یک نسخه‌ی دوم و مستقل از RabbitMQPublisher را تعریف می‌کرد که…

### Community 56 - "User & Role Queries"
Cohesion: 0.29
Nodes (7): get_all_users(), get_pages(), get_roles(), get_user(), get, کلید صفحه‌ها برای فیلد allowed_pages کاربر (ادمین همیشه به همه دسترسی دارد)., Returns the list of roles defined in the system for use in the frontend (e.g.…

### Community 57 - "Alembic Env"
Cohesion: 0.33
Nodes (6): Connection, do_run_migrations(), In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_online()

### Community 58 - "Graylog Client"
Cohesion: 0.40
Nodes (3): GraylogClient, Any, جستجوی لاگ‌ها در بازه زمانی گذشته بر حسب ثانیه

### Community 60 - "Profile Read"
Cohesion: 0.67
Nodes (3): get_my_profile(), get, دریافت اطلاعات پروفایل کاربر لاگین‌شده

### Community 61 - "Profile Update"
Cohesion: 0.67
Nodes (3): put, به‌روزرسانی پروفایل کاربر فعلی (ارسال به صف), update_my_profile()

## Ambiguous Edges - Review These
- `reportlab + openpyxl (report export)` → `Excel Bulk Import`  [AMBIGUOUS]
  main_api/req.txt · relation: conceptually_related_to

## Knowledge Gaps
- **15 isolated node(s):** `setup_input.sh script`, `Config`, `Config`, `Config`, `Config` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 468 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `reportlab + openpyxl (report export)` and `Excel Bulk Import`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `RabbitMQPublisher` connect `RabbitMQ Publisher` to `System Settings Repo`, `Feeder Excel Import`, `Locations Module`, `Settings Router`, `Migrations & Domain Constants`, `Feeder Create & Command Routes`, `Links Module`, `Auth Schemas & Router`, `Feeder Service`, `Auth Service & Password Reset`, `User Management`, `User Repository & Lockout`, `Broker Dependencies`, `Feeders Router`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `send_audit_log()` connect `Background Audit Logging` to `Audit Log Models & Services`, `Feeder Excel Import`, `Two-Step Feeder Commands`, `System Settings Repo`, `Locations Module`, `Settings Router`, `Main API Telemetry Repo`, `Migrations & Domain Constants`, `Links Module`, `Alert Dispatch`, `Auth Schemas & Router`, `Feeder Service`, `Auth Service & Password Reset`, `User Management`, `Notification Service Logic`, `Feeder Status Reporting`, `Broker Dependencies`, `Telemetry Proxy Client`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `send_audit_log()` (e.g. with `schedule_audit_log()` and `.forgot_password()`) actually correct?**
  _`send_audit_log()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `RabbitMQPublisher` (e.g. with `get_auth_service()` and `AuthService`) actually correct?**
  _`RabbitMQPublisher` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `AuthService` (e.g. with `change_password()` and `forgot_password()`) actually correct?**
  _`AuthService` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `setup_input.sh script`, `Config`, `Config` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._