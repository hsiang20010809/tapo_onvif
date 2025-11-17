# Tapo C225 ONVIF 協定與座標系統詳細說明

## 官方參考文檔

- **[How to view Tapo camera on PC/NAS/NVR through RTSP/Onvif Protocol](https://www.tapo.com/en/faq/34/)** - 官方 RTSP/ONVIF 設定指南
- **[General questions about viewing Tapo Cameras via RTSP/ONVIF protocols](https://www.tapo.com/us/faq/724/)** - RTSP/ONVIF 常見問題
- **[General questions about Pan & Tilt feature of TP-Link Camera](https://www.tapo.com/en/faq/761/)** - PTZ 功能說明
- **[How to do Pan & Tilt Correction on Tapo cameras](https://www.tapo.com/uk/faq/590/)** - PTZ 校準指南
- **[How to set up Patrol Mode on Tapo cameras](https://www.tapo.com/en/faq/419/)** - 巡邏模式設定

---

## 目錄
1. [ONVIF 支援概述](#onvif-支援概述)
2. [ONVIF vs pytapo 座標系統比較](#onvif-vs-pytapo-座標系統比較)
3. [ONVIF 座標系統詳解](#onvif-座標系統詳解)
4. [連接設定](#連接設定)
5. [程式控制範例](#程式控制範例)
6. [ODM (ONVIF Device Manager) 使用](#odm-onvif-device-manager-使用)
7. [企業整合建議](#企業整合建議)

---

## ONVIF 支援概述

### Tapo C225 支援的協定

| 協定 | 支援狀態 | 埠號 | 說明 |
|------|----------|------|------|
| ONVIF Profile S | ✓ 支援 | 2020 | 基本功能、PTZ 控制、串流 |
| RTSP | ✓ 支援 | 554 | 即時視訊串流 |
| ONVIF Profile T | ✗ 不支援 | - | 進階功能（H.265等） |
| 雙向音訊 | ✗ 不支援 | - | Profile S 不包含此功能 |

### ONVIF Profile S 功能

Profile S 包含的功能：
- ✅ 視訊/音訊串流
- ✅ 網路配置
- ✅ 事件處理
- ✅ **PTZ (Pan-Tilt-Zoom) 控制**
- ✅ 預設位置管理

---

## ONVIF vs pytapo 座標系統比較

### 核心差異

| 特性 | ONVIF | pytapo |
|------|-------|--------|
| **座標類型** | 絕對座標 | 相對座標 |
| **座標範圍** | -1.0 ~ +1.0（正規化） | -170 ~ +170（裝置特定） |
| **可查詢當前位置** | ✅ 是 | ❌ 否 |
| **重啟後位置** | 可恢復到指定座標 | 回到機械預設位置 |
| **業界標準** | ✅ 是（ONVIF 標準） | ❌ 否（私有 API） |
| **NVR/NAS 整合** | ✅ 原生支援 | ❌ 需額外開發 |

### 重要發現：ONVIF 提供絕對座標！

**這是解決你需求的關鍵：**

pytapo 的座標系統：
```
當前位置 = (0, 0)  ← 永遠是相對於「現在」
moveMotor(10, 5)
新位置 = (0, 0)    ← 又重置了
```

ONVIF 的座標系統：
```
當前位置 = GetStatus() → Pan=0.3, Tilt=-0.2  ← 絕對座標
AbsoluteMove(pan=0.5, tilt=0.0)
GetStatus() → Pan=0.5, Tilt=0.0              ← 可驗證
```

---

## ONVIF 座標系統詳解

### 正規化座標空間

ONVIF 使用正規化座標（-1.0 到 +1.0），這是業界標準：

```
Pan (水平旋轉):
    -1.0 ←─────┼─────→ +1.0
    最左      中心      最右

Tilt (垂直傾斜):
    +1.0 (上)
      ↑
      │
    0.0 (中)
      │
      ↓
    -1.0 (下)

Zoom (縮放):
    0.0 (廣角) → 1.0 (望遠)
```

### 座標對應實體位置

假設攝影機安裝在天花板：

```
俯視圖（Pan 方向）:

              Pan = 0.0
                  ↑
    Pan = -1.0 ←  ●  → Pan = +1.0
                  ↓
              背面
              
側視圖（Tilt 方向）:

    Tilt = +1.0 (看向前方/水平)
         ↑
         ●  攝影機
         ↓
    Tilt = -1.0 (看向地板/垂直向下)
```

### 移動類型

ONVIF 支援三種移動方式：

1. **AbsoluteMove** - 移動到絕對座標
   ```python
   # 移動到正中央
   controller.absolute_move(pan=0.0, tilt=0.0)
   
   # 移動到右上角
   controller.absolute_move(pan=0.8, tilt=0.6)
   ```

2. **RelativeMove** - 相對當前位置移動
   ```python
   # 從當前位置向右移動 0.2
   controller.relative_move(pan_delta=0.2)
   ```

3. **ContinuousMove** - 以指定速度持續移動
   ```python
   # 向左持續移動 2 秒
   controller.continuous_move(pan_speed=-0.5, duration=2.0)
   ```

---

## 連接設定

> 📖 **官方指南：** [How to view Tapo camera on PC/NAS/NVR through RTSP/Onvif Protocol](https://www.tapo.com/en/faq/34/)

### 前置準備

1. **在 Tapo App 建立攝影機帳戶**
   - 進入攝影機 Live View → 右上角齒輪圖示 → 進階設定 → 攝影機帳戶
   - 建立專用的帳號密碼
   - **帳號密碼長度：6-32 字元**
   - **這個帳號用於 ONVIF/RTSP，必須與你的 TP-Link 雲端帳號不同**
   - 首次設定時會看到「關於攝影機帳戶」提示，需點擊「了解並同意使用」

2. **確認攝影機 IP**
   - 在 Tapo App 中：設備設定 → 設備資訊
   - 或在路由器的 DHCP 列表中查找

3. **網路設定**
   - 確保攝影機和控制端在同一網段
   - 開放 Port 2020 (ONVIF) 和 554 (RTSP)
   - **重要：只在受信任的本地網路使用，確保 Wi-Fi 有加密**

### 連線參數

```python
HOST = "192.168.1.100"     # 攝影機 IP
PORT = 2020                 # ONVIF 服務埠號（固定）
USER = "camera_account"     # 攝影機帳戶（在 Tapo App 設定的）
PASSWORD = "camera_password"
```

### RTSP URL 格式

根據官方文件，RTSP URL 格式如下：

```
主串流（高畫質）:
rtsp://IP_Address/stream1
或
rtsp://IP_Address:554/stream1

次串流（低畫質）:
rtsp://IP_Address/stream2
或
rtsp://IP_Address:554/stream2
```

**注意：** 
- 部分軟體（如 VLC）會在連線時要求輸入帳號密碼
- 某些軟體可能支援在 URL 中嵌入認證：`rtsp://username:password@IP_Address:554/stream1`
- 串流解析度由 Tapo App 中的「影像品質」設定決定，建議設為「最佳品質」

---

## 程式控制範例

### 安裝依賴

```bash
pip install onvif-zeep
# 或
pip install python-onvif-zeep
```

### 基本使用

```python
from tapo_onvif_controller import TapoONVIFController

# 連接
ctrl = TapoONVIFController(
    host="192.168.1.100",
    port=2020,
    user="camera_account",
    password="camera_password"
)
ctrl.connect()

# 獲取當前座標（ONVIF 的優勢！）
pan, tilt, zoom = ctrl.get_current_position()
print(f"當前位置: Pan={pan}, Tilt={tilt}")

# 絕對座標移動
ctrl.move_to_position(pan=0.5, tilt=0.3)

# 儲存預設位置
token = ctrl.set_preset("入口監控")

# 移動到預設位置
ctrl.goto_preset(token)
```

### 建立位置對照表

由於 ONVIF 提供絕對座標，你可以建立精確的位置對照表：

```python
# 定義監控位置
POSITIONS = {
    "入口": {"pan": 0.0, "tilt": 0.0},
    "走廊左側": {"pan": -0.6, "tilt": 0.2},
    "走廊右側": {"pan": 0.6, "tilt": 0.2},
    "大廳中央": {"pan": 0.0, "tilt": -0.3},
    "緊急出口": {"pan": -0.9, "tilt": 0.1},
}

def move_to_location(controller, location_name):
    """移動到預定義位置"""
    if location_name in POSITIONS:
        pos = POSITIONS[location_name]
        controller.move_to_position(pos["pan"], pos["tilt"])
        print(f"已移動到: {location_name}")

# 使用
move_to_location(ctrl, "走廊左側")
```

### 校準和映射物理角度

如果需要將 ONVIF 座標對應到實際角度：

```python
def normalized_to_degrees(pan_norm, tilt_norm):
    """
    將正規化座標轉換為角度
    假設：Pan 範圍 -180° ~ +180°，Tilt 範圍 -90° ~ +90°
    """
    pan_degrees = pan_norm * 180.0   # -1.0 → -180°, +1.0 → +180°
    tilt_degrees = tilt_norm * 90.0  # -1.0 → -90°, +1.0 → +90°
    return pan_degrees, tilt_degrees

def degrees_to_normalized(pan_deg, tilt_deg):
    """將角度轉換為正規化座標"""
    pan_norm = pan_deg / 180.0
    tilt_norm = tilt_deg / 90.0
    return pan_norm, tilt_norm

# 使用範例
pan_deg, tilt_deg = normalized_to_degrees(0.5, 0.3)
print(f"Pan: {pan_deg}°, Tilt: {tilt_deg}°")
# 輸出: Pan: 90°, Tilt: 27°
```

---

## ODM (ONVIF Device Manager) 使用

ONVIF Device Manager 是一個免費的 Windows 應用程式，用於測試和管理 ONVIF 設備。

### 官方推薦的第三方軟體

根據 TP-Link 官方文件，以下軟體經過測試：
- **Agent DVR** - 支援 ONVIF 自動發現，PTZ 控制
- **VLC Player** - RTSP 串流播放
- **iSpy** - 完整監控功能

### 下載與安裝

從 SourceForge 下載：
https://sourceforge.net/projects/onvifdm/

### 連接 Tapo C225

1. 開啟 ONVIF Device Manager
2. 點擊 "Add" 按鈕
3. 輸入：
   - Device Address: `http://192.168.1.100:2020/onvif/device_service`
   - Username: 你的攝影機帳戶
   - Password: 密碼
4. 點擊 "Connect"

### 使用 ODM 查看座標

在 ODM 中：
1. 選擇你的攝影機
2. 進入 "Live Video" 標籤
3. 使用 PTZ 控制面板
4. 觀察座標變化

### ODM 的座標顯示

ODM 會顯示：
- Pan/Tilt 座標（-1.0 ~ +1.0）
- 當前狀態
- 預設位置列表
- PTZ 能力資訊

這對於：
- 測試攝影機連線
- 確認座標範圍
- 手動設定預設位置
- 驗證程式控制結果

非常有用。

---

## 企業整合建議

### 架構選擇

根據你的需求，可以選擇：

1. **ONVIF + pytapo 混合使用**（推薦）
   - ONVIF：用於獲取絕對座標、NVR 整合
   - pytapo：用於特定功能（如隱私模式、AI 偵測設定）

2. **純 ONVIF**
   - 優點：標準化、可整合 NVR/NAS
   - 缺點：某些 Tapo 特定功能可能無法使用

3. **純 pytapo**
   - 優點：功能完整
   - 缺點：無絕對座標

### 推薦架構

```
┌─────────────┐
│  應用層     │  ← 業務邏輯
├─────────────┤
│  抽象層     │  ← 統一 API
├─────────────┤
│  ONVIF      │  │  pytapo    │
│  - 座標查詢 │  │  - 隱私模式 │
│  - 絕對移動 │  │  - AI 偵測  │
│  - RTSP     │  │  - 特定設定 │
└─────────────┘  └────────────┘
```

### 統一控制器範例

```python
class UnifiedTapoController:
    """統一 Tapo 控制器（整合 ONVIF 和 pytapo）"""
    
    def __init__(self, host, tapo_user, tapo_password, onvif_user, onvif_password):
        self.pytapo_ctrl = TapoC225Controller(host, tapo_user, tapo_password)
        self.onvif_ctrl = TapoONVIFController(host, 2020, onvif_user, onvif_password)
    
    def connect(self):
        self.pytapo_ctrl.connect()
        self.onvif_ctrl.connect()
    
    def get_absolute_position(self):
        """使用 ONVIF 獲取絕對座標"""
        return self.onvif_ctrl.get_current_position()
    
    def move_to_absolute(self, pan, tilt):
        """使用 ONVIF 絕對移動"""
        return self.onvif_ctrl.move_to_position(pan, tilt)
    
    def set_privacy_mode(self, enabled):
        """使用 pytapo 控制隱私模式"""
        if enabled:
            self.pytapo_ctrl.enable_privacy_mode()
        else:
            self.pytapo_ctrl.disable_privacy_mode()
    
    def set_auto_track(self, enabled):
        """使用 pytapo 控制自動追蹤"""
        self.pytapo_ctrl.set_auto_track(enabled)
```

### NVR 整合

如果要整合到 NVR（如 Synology Surveillance Station, QNAP QVR）：

1. 在 NVR 中新增 ONVIF 攝影機
2. 輸入 ONVIF 連線資訊
3. 自動發現 PTZ 功能
4. 可在 NVR 介面控制 PTZ

---

## 總結

### 解決你的需求

**原始需求：** 找到座標系統，程式控制 PTZ

**解決方案：**

1. **座標系統**
   - pytapo：相對座標，範圍約 -170 ~ +170（裝置特定）
   - ONVIF：**絕對座標**，範圍 -1.0 ~ +1.0（**推薦！**）

2. **重啟後自動回正**
   - 原因：攝影機執行馬達校準
   - 解決：使用預設位置記錄特定位置

3. **程式控制**
   - pytapo：簡單易用，功能完整
   - ONVIF：**支援絕對座標查詢和控制**

### 建議

1. **使用 ONVIF 獲取絕對座標** - 這是你需要的「座標系統」
2. **結合 pytapo 使用特定功能** - 如隱私模式、AI 偵測
3. **建立位置資料庫** - 記錄重要位置的座標
4. **定期校準驗證** - 確保座標準確性

### 重要提醒

- ONVIF 帳戶 ≠ TP-Link 雲端帳戶
- 需要在 Tapo App 中另外設定攝影機帳戶（6-32 字元）
- ONVIF 安全性較低，建議在安全的內網環境使用
- **不建議透過 Port Forwarding 暴露在公網，如需遠端存取請使用 VPN**
- 定期檢查韌體更新，可能影響 ONVIF 支援

### 儲存限制注意事項

根據官方文件，部分 Tapo 攝影機型號有串流數量限制：
- **Tapo Care 雲端儲存無法同時與 NVR 或 microSD 卡並用**
- 如果三者同時使用，NVR 錄影會被停用
- 若要恢復 NVR 錄影，需移除攝影機中的 microSD 卡

---

## 附錄：官方技術資源

### TP-Link / Tapo 官方文檔

| 主題 | 連結 |
|------|------|
| RTSP/ONVIF 設定指南 | https://www.tapo.com/en/faq/34/ |
| RTSP/ONVIF 常見問題 | https://www.tapo.com/us/faq/724/ |
| PTZ 功能說明 | https://www.tapo.com/en/faq/761/ |
| PTZ 校準指南 | https://www.tapo.com/uk/faq/590/ |
| 巡邏模式設定 | https://www.tapo.com/en/faq/419/ |
| 如何找到攝影機 IP | https://www.tp-link.com/support/faq/2616/ |
| Pan & Tilt 功能使用 | https://www.tp-link.com/us/support/faq/2623/ |
| Tapo C225 產品頁面 | https://www.tapo.com/us/product/smart-camera/tapo-c225/ |
| Tapo C225 下載中心 | https://www.tp-link.com/us/support/download/tapo-c225/ |

### ONVIF 標準文檔

| 文檔 | 連結 |
|------|------|
| ONVIF PTZ Service Specification | https://www.onvif.org/specs/srv/ptz/ONVIF-PTZ-Service-Spec-v1712.pdf |
| ONVIF Profile S | https://www.onvif.org/profiles/profile-s/ |

### 第三方函式庫

| 函式庫 | 連結 | 用途 |
|--------|------|------|
| pytapo | https://github.com/JurajNyiri/pytapo | Tapo 攝影機私有 API |
| python-onvif-zeep | https://pypi.org/project/onvif-zeep/ | ONVIF Python 客戶端 |
| Home Assistant Tapo Control | https://github.com/JurajNyiri/HomeAssistant-Tapo-Control | Home Assistant 整合 |

### 故障排除

如果 RTSP/ONVIF 連線失敗，可參考：
- **官方故障排除指南：** https://community.tp-link.com/en/smart-home/forum/topic/652710
