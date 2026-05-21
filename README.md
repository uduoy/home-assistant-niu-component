# Niu E-scooter Home Assistant Integration / 小牛电动车 Home Assistant 集成

[![HACS Validation](https://github.com/uduoy/home-assistant-niu-component/actions/workflows/hacs.yml/badge.svg)](https://github.com/uduoy/home-assistant-niu-component/actions/workflows/hacs.yml)
![GitHub release](https://img.shields.io/github/v/release/uduoy/home-assistant-niu-component)

支持中国小牛电动车连接。修改了代码中的连接服务器，`app-api-fk.niu.com` 改为 `app-api.niu.com`，`account-fk.niu.com` 改为 `account.niu.com`。

This is a custom component for Home Assistant to integrate your Niu Scooter, optimized for **Chinese users** with the domestic NIU API endpoints.

---

## Features / 功能特性

### 传感器 Sensors

| 传感器 Sensor | 描述 Description |
|---|---|
| Battery Charge / 电池电量 | Current battery level (%) |
| Times Charged / 充电次数 | Total charge cycles |
| Battery Temperature / 电池温度 | Battery temperature (°C) |
| Battery Grade / 电池健康度 | Battery health rating (%) |
| Current Speed / 当前速度 | Real-time speed (km/h) |
| Time Left / 剩余时间 | Estimated remaining time (h) |
| Estimated Mileage / 预估续航 | Estimated range (km) |
| Centre Control Battery / 中控电池 | Centre controller battery (%) |
| Total Mileage / 总里程 | Lifetime odometer (km) |
| Days In Use / 使用天数 | Days since activation |
| Trip Distance / 行程距离 | Current trip distance (m) |
| Trip Riding Time / 骑行时间 | Current trip duration (s) |
| GPS Coordinates / GPS 坐标 | Latitude / Longitude (auto-converted) |

### 二进制传感器 Binary Sensors

| Binary Sensor | 描述 Description |
|---|---|
| Battery Connected / 电池连接 | Battery connection status |
| Scooter Connected / 车辆连接 | Scooter connection status |
| Is Charging / 充电状态 | Charging status (On/Off) |
| Is Locked / 锁定状态 | Lock status (Locked/Unlocked) |

### 设备追踪 Device Tracker

- Vehicle location on HA map / 车辆位置在 HA 地图上显示
- GPS coordinates auto-converted from GCJ-02 to WGS-84 (China map compliance)
- GPS 坐标自动从 GCJ-02（火星坐标）转换为 WGS-84（标准 GPS）

### 轨迹相机 Track Camera

- Last ride track thumbnail displayed as camera entity
- 上次骑行轨迹缩略图以相机实体显示

---

## Why This Fork / 本项目优势

Since the original project was abandoned, this fork has accumulated significant improvements that make it the **most feature-rich and modernized** version available.

原项目已停止维护，本项目在原基础上进行了大量改进，是**功能最丰富、架构最现代**的版本。

### Compared to upstream (marcelwestrahome) / 对比原项目

| Feature / 特性 | Original / 原项目 | This Fork / 本项目 |
|---|---|---|
| Network I/O / 网络请求 | Synchronous `requests` / 同步 | **Async `aiohttp`** / 异步 |
| Data Management / 数据管理 | Per-platform polling / 各自轮询 | **`DataUpdateCoordinator`** / 统一管理 |
| Error Handling / 错误处理 | Direct dict access (crash-prone) | **Defensive `.get()` + `ConfigEntryNotReady`** |
| Device Tracker / 设备追踪 | ❌ Removed upstream | **✅ Preserved** / 保留 |
| Chinese API / 国内 API | Requires manual URL change | **✅ Pre-configured** / 预配置 |
| Coordinate System / 坐标系 | GCJ-02 only (map offset) | **✅ Auto GCJ-02 → WGS-84** |
| Binary Sensors / 二进制传感器 | ❌ Not available | **✅ Added** |
| Locale / 语言支持 | Hardcoded en-US | **✅ Auto-follows HA language** |
| Config Flow / 配置流 | Basic | **✅ Sensor multi-select** / 传感器多选 |
| Entity Naming / 实体命名 | Inconsistent | **✅ Deterministic + translation keys** |

### Merged Improvements / 合并的改进

#### From hasscc (Chinese Community)
- **GCJ-02 to WGS-84 coordinate conversion** — NIU API returns Mars coordinates (GCJ-02) as required by Chinese law. Without conversion, vehicle location is offset by hundreds of meters on HA map. This fork automatically converts to standard GPS (WGS-84).
- **GCJ-02 到 WGS-84 坐标转换** — NIU API 返回的是中国火星坐标系（GCJ-02），不经转换在 HA 地图上偏移数百米。本项目自动转换为标准 GPS。
- `ConfigEntryNotReady` — Automatically retries on temporary API failures instead of crashing.

#### From LookedPath
- **Binary sensor platform** — Status fields (`IsCharging`, `IsLocked`, `ScooterConnected`) are now proper binary sensors with on/off semantics and device classes, instead of plain sensors showing `0`/`1`.
- **二进制传感器** — 充电状态、锁定状态、连接状态等改用二进制传感器，在 HA 中显示"开/关"而非 0/1。
- State translations with human-readable labels (e.g. "Charging/Not Charging", "Locked/Unlocked").
- 状态文本翻译（如"充电中/未充电"、"已锁定/未锁定"）。

#### From jwtue (via upstream)
- Second battery API infrastructure (inactive until API recovers).
- 第二块电池 API 支持（API 恢复后可用）。

#### From upstream (multi-language support)
- **Auto locale detection** — The integration automatically reads your Home Assistant language setting and passes it to NIU API. No manual configuration needed.
- **自动语言适配** — 集成自动读取 HA 系统语言设置并传递给 NIU API，无需手动配置。

---

## What's NOT working / 已知不可用数据

Due to NIU server-side API changes, the following endpoints return HTTP 500:

因 NIU 服务端 API 变更，以下接口返回 HTTP 500：

- **Motor / Index data**: Current speed, GPS position, lock status, trip distance — all unavailable
- **马达/行驶数据**：当前速度、GPS 位置、锁定状态、行程距离 — 均不可用
- **Track list**: Ride history, track thumbnails — unavailable
- **轨迹列表**：骑行历史、轨迹缩略图 — 不可用

These are server-side issues, not bugs in the component. When NIU restores these APIs, the component will work without changes.

此为 NIU 服务端问题，非组件 bug。NIU 恢复后无需修改代码即可使用。

---

## Setup / 安装配置

### Via HACS (Recommended / 推荐)

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → Three dots menu → Custom repositories
   - Repository: `https://github.com/uduoy/home-assistant-niu-component`
   - Category: Integration
2. Click "Install"
3. Restart Home Assistant

### Manual Install / 手动安装

Copy the `custom_components/niu` directory to your HA `config/custom_components/` directory.

### Configuration / 配置

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration**
2. Search for "Niu Scooters"
3. Enter your NIU account credentials:
   - **Username**: Phone number / 手机号
   - **Password**: NIU App password / NIU App 密码
   - **Scooter ID**: Default `0`
   - **Sensors**: Select which sensors to display
4. Click Submit

---

## Credits / 致谢

- **[marcelwestrahome](https://github.com/marcelwestrahome)** — Original project / 原项目
- **[pikka97](https://github.com/pikka97)** — Async rewrite contributions
- **[hasscc](https://github.com/hasscc)** — GCJ-02 coordinate conversion, architecture improvements
- **[LookedPath](https://github.com/LookedPath)** — Binary sensor platform, switch platform
- **[jwtue](https://github.com/jwtue)** — Second battery support

---

## Version History / 版本历史

### v2.3.0
- **Fix**: overallTally API request format (form-data → JSON body) — restores total mileage sensor
- **Fix**: `getDataPos` typo (`postion` → `position`)
- **Fix**: Login broken after upstream merge (async method name mismatch)
- **Fix**: `hass.data[DOMAIN]` KeyError on setup
- **Fix**: `from_hass()` not used in `__init__` — language now follows HA settings
- **New**: GCJ-02 → WGS-84 coordinate conversion (from hasscc)
- **New**: Binary sensor platform for status fields (from LookedPath)
- **Improved**: `ConfigEntryNotReady` for automatic retry on API failure
- **Improved**: Auto-detect HA language for NIU API requests
