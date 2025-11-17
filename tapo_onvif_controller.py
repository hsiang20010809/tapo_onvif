#!/usr/bin/env python3
"""
Tapo C225 ONVIF PTZ Controller
透過 ONVIF Profile S 協定控制 Tapo C225 攝影機

ONVIF 的優勢：
1. 支援絕對座標（-1.0 到 +1.0 正規化座標）
2. 業界標準協定，可與 NVR/NAS 整合
3. 支援即時串流 (RTSP)

注意事項：
- Tapo 攝影機只支援 ONVIF Profile S
- 需要先在 Tapo App 建立攝影機帳戶
- ONVIF 埠號: 2020
- RTSP 埠號: 554
"""

import time
from typing import Dict, Any, Optional, Tuple
from onvif import ONVIFCamera
from zeep.helpers import serialize_object


class TapoONVIFController:
    """Tapo C225 ONVIF PTZ 控制器"""
    
    def __init__(self, host: str, port: int = 2020, user: str = "", password: str = "", wsdl_dir: str = None):
        """
        初始化 ONVIF 控制器
        
        Args:
            host: 攝影機 IP 位址
            port: ONVIF 服務埠號（Tapo 預設為 2020）
            user: 攝影機帳戶使用者名稱（在 Tapo App 設定）
            password: 攝影機帳戶密碼
            wsdl_dir: WSDL 檔案目錄（可選）
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.wsdl_dir = wsdl_dir
        
        self.camera: Optional[ONVIFCamera] = None
        self.media_service = None
        self.ptz_service = None
        self.media_profile = None
        self.ptz_config_options = None
        
        # 座標範圍
        self.pan_range = (-1.0, 1.0)
        self.tilt_range = (-1.0, 1.0)
        self.zoom_range = (0.0, 1.0)
        
    def connect(self) -> bool:
        """
        連接到攝影機
        
        Returns:
            bool: 連接成功返回 True
        """
        try:
            print(f"🔌 連接到 ONVIF 服務 {self.host}:{self.port}...")
            
            # 建立 ONVIF 連線
            if self.wsdl_dir:
                self.camera = ONVIFCamera(
                    self.host, self.port, self.user, self.password, self.wsdl_dir
                )
            else:
                self.camera = ONVIFCamera(
                    self.host, self.port, self.user, self.password
                )
            
            print("✓ ONVIF 連線成功")
            
            # 取得設備資訊
            device_info = self.camera.devicemgmt.GetDeviceInformation()
            print(f"  製造商: {device_info.Manufacturer}")
            print(f"  型號: {device_info.Model}")
            print(f"  韌體版本: {device_info.FirmwareVersion}")
            
            # 建立媒體服務
            self.media_service = self.camera.create_media_service()
            print("✓ 媒體服務已建立")
            
            # 取得媒體配置檔
            profiles = self.media_service.GetProfiles()
            if not profiles:
                raise Exception("找不到媒體配置檔")
            
            self.media_profile = profiles[0]
            print(f"  配置檔名稱: {self.media_profile.Name}")
            print(f"  配置檔 Token: {self.media_profile.token}")
            
            # 建立 PTZ 服務
            self.ptz_service = self.camera.create_ptz_service()
            print("✓ PTZ 服務已建立")
            
            # 取得 PTZ 配置選項
            self._get_ptz_config_options()
            
            return True
            
        except Exception as e:
            print(f"✗ 連接失敗: {e}")
            return False
    
    def _get_ptz_config_options(self):
        """取得 PTZ 配置選項和座標範圍"""
        try:
            request = self.ptz_service.create_type('GetConfigurationOptions')
            request.ConfigurationToken = self.media_profile.PTZConfiguration.token
            self.ptz_config_options = self.ptz_service.GetConfigurationOptions(request)
            
            # 解析座標範圍
            spaces = self.ptz_config_options.Spaces
            
            # 絕對位置空間
            if hasattr(spaces, 'AbsolutePanTiltPositionSpace') and spaces.AbsolutePanTiltPositionSpace:
                abs_space = spaces.AbsolutePanTiltPositionSpace[0]
                self.pan_range = (abs_space.XRange.Min, abs_space.XRange.Max)
                self.tilt_range = (abs_space.YRange.Min, abs_space.YRange.Max)
                print(f"  絕對座標範圍:")
                print(f"    Pan (水平): {self.pan_range[0]} ~ {self.pan_range[1]}")
                print(f"    Tilt (垂直): {self.tilt_range[0]} ~ {self.tilt_range[1]}")
            
            # 縮放空間
            if hasattr(spaces, 'AbsoluteZoomPositionSpace') and spaces.AbsoluteZoomPositionSpace:
                zoom_space = spaces.AbsoluteZoomPositionSpace[0]
                self.zoom_range = (zoom_space.XRange.Min, zoom_space.XRange.Max)
                print(f"    Zoom (縮放): {self.zoom_range[0]} ~ {self.zoom_range[1]}")
                
        except Exception as e:
            print(f"  ⚠ 無法獲取 PTZ 配置選項: {e}")
    
    # ========== 串流 URL ==========
    
    def get_rtsp_url(self, stream_index: int = 1) -> str:
        """
        取得 RTSP 串流 URL
        
        Args:
            stream_index: 串流索引（1 = 主串流, 2 = 次串流）
            
        Returns:
            str: RTSP URL
        """
        return f"rtsp://{self.user}:{self.password}@{self.host}:554/stream{stream_index}"
    
    def get_onvif_stream_url(self) -> str:
        """
        透過 ONVIF 取得串流 URL
        
        Returns:
            str: 串流 URI
        """
        try:
            stream_setup = self.media_service.create_type('GetStreamUri')
            stream_setup.ProfileToken = self.media_profile.token
            stream_setup.StreamSetup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            
            uri = self.media_service.GetStreamUri(stream_setup)
            return uri.Uri
        except Exception as e:
            print(f"✗ 無法獲取串流 URL: {e}")
            return ""
    
    # ========== PTZ 控制 - 絕對移動 ==========
    
    def absolute_move(self, pan: float = None, tilt: float = None, zoom: float = None, 
                      speed: float = 1.0) -> bool:
        """
        絕對位置移動（ONVIF 的優勢功能）
        
        座標系統：
        - Pan (水平): -1.0（左）到 +1.0（右）
        - Tilt (垂直): -1.0（下）到 +1.0（上）
        - Zoom: 0.0（廣角）到 1.0（望遠）
        
        注意：Tapo 攝影機可能不支援 Zoom
        
        Args:
            pan: 水平位置 (-1.0 ~ 1.0)
            tilt: 垂直位置 (-1.0 ~ 1.0)
            zoom: 縮放位置 (0.0 ~ 1.0)
            speed: 移動速度 (0.0 ~ 1.0)
            
        Returns:
            bool: 成功返回 True
        """
        try:
            request = self.ptz_service.create_type('AbsoluteMove')
            request.ProfileToken = self.media_profile.token
            
            # 設定位置
            request.Position = self.ptz_service.GetStatus(
                {'ProfileToken': self.media_profile.token}
            ).Position
            
            if pan is not None or tilt is not None:
                if not hasattr(request.Position, 'PanTilt'):
                    request.Position.PanTilt = {}
                if pan is not None:
                    request.Position.PanTilt.x = max(self.pan_range[0], 
                                                      min(self.pan_range[1], pan))
                if tilt is not None:
                    request.Position.PanTilt.y = max(self.tilt_range[0], 
                                                      min(self.tilt_range[1], tilt))
            
            if zoom is not None:
                if not hasattr(request.Position, 'Zoom'):
                    request.Position.Zoom = {}
                request.Position.Zoom.x = max(self.zoom_range[0], 
                                               min(self.zoom_range[1], zoom))
            
            # 設定速度
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            self.ptz_service.AbsoluteMove(request)
            print(f"✓ 絕對移動: Pan={pan}, Tilt={tilt}, Zoom={zoom}")
            return True
            
        except Exception as e:
            print(f"✗ 絕對移動失敗: {e}")
            return False
    
    def move_to_position(self, pan: float, tilt: float, speed: float = 1.0) -> bool:
        """
        移動到指定的正規化位置
        
        Args:
            pan: 水平位置 (-1.0 ~ 1.0)
            tilt: 垂直位置 (-1.0 ~ 1.0)
            speed: 移動速度 (0.0 ~ 1.0)
            
        Returns:
            bool: 成功返回 True
        """
        return self.absolute_move(pan=pan, tilt=tilt, speed=speed)
    
    # ========== PTZ 控制 - 相對移動 ==========
    
    def relative_move(self, pan_delta: float = 0.0, tilt_delta: float = 0.0, 
                      zoom_delta: float = 0.0, speed: float = 1.0) -> bool:
        """
        相對位置移動
        
        Args:
            pan_delta: 水平移動量
            tilt_delta: 垂直移動量
            zoom_delta: 縮放移動量
            speed: 移動速度 (0.0 ~ 1.0)
            
        Returns:
            bool: 成功返回 True
        """
        try:
            request = self.ptz_service.create_type('RelativeMove')
            request.ProfileToken = self.media_profile.token
            
            # 設定移動量
            request.Translation = {
                'PanTilt': {'x': pan_delta, 'y': tilt_delta},
                'Zoom': {'x': zoom_delta}
            }
            
            # 設定速度
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            self.ptz_service.RelativeMove(request)
            print(f"✓ 相對移動: Pan Δ={pan_delta}, Tilt Δ={tilt_delta}")
            return True
            
        except Exception as e:
            print(f"✗ 相對移動失敗: {e}")
            return False
    
    # ========== PTZ 控制 - 連續移動 ==========
    
    def continuous_move(self, pan_speed: float = 0.0, tilt_speed: float = 0.0, 
                        zoom_speed: float = 0.0, duration: float = 1.0):
        """
        連續移動（指定速度和方向）
        
        Args:
            pan_speed: 水平速度 (-1.0 ~ 1.0，負值向左，正值向右）
            tilt_speed: 垂直速度 (-1.0 ~ 1.0，負值向下，正值向上）
            zoom_speed: 縮放速度 (-1.0 ~ 1.0）
            duration: 持續時間（秒）
        """
        try:
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = self.media_profile.token
            
            request.Velocity = {
                'PanTilt': {'x': pan_speed, 'y': tilt_speed},
                'Zoom': {'x': zoom_speed}
            }
            
            self.ptz_service.ContinuousMove(request)
            print(f"🔄 連續移動開始: Pan={pan_speed}, Tilt={tilt_speed}")
            
            time.sleep(duration)
            self.stop()
            
        except Exception as e:
            print(f"✗ 連續移動失敗: {e}")
    
    def stop(self):
        """停止所有移動"""
        try:
            self.ptz_service.Stop({
                'ProfileToken': self.media_profile.token,
                'PanTilt': True,
                'Zoom': True
            })
            print("⏹ 移動已停止")
        except Exception as e:
            print(f"✗ 停止失敗: {e}")
    
    # ========== 方向控制 ==========
    
    def pan_left(self, speed: float = 0.5, duration: float = 1.0):
        """向左平移"""
        self.continuous_move(pan_speed=-speed, duration=duration)
    
    def pan_right(self, speed: float = 0.5, duration: float = 1.0):
        """向右平移"""
        self.continuous_move(pan_speed=speed, duration=duration)
    
    def tilt_up(self, speed: float = 0.5, duration: float = 1.0):
        """向上傾斜"""
        self.continuous_move(tilt_speed=speed, duration=duration)
    
    def tilt_down(self, speed: float = 0.5, duration: float = 1.0):
        """向下傾斜"""
        self.continuous_move(tilt_speed=-speed, duration=duration)
    
    # ========== 狀態查詢 ==========
    
    def get_status(self) -> Dict[str, Any]:
        """
        獲取當前 PTZ 狀態（包含當前座標！）
        
        Returns:
            dict: PTZ 狀態資訊
        """
        try:
            status = self.ptz_service.GetStatus({'ProfileToken': self.media_profile.token})
            status_dict = serialize_object(status)
            
            print("📍 當前 PTZ 狀態:")
            if hasattr(status, 'Position'):
                pos = status.Position
                if hasattr(pos, 'PanTilt'):
                    print(f"   Pan (水平): {pos.PanTilt.x:.4f}")
                    print(f"   Tilt (垂直): {pos.PanTilt.y:.4f}")
                if hasattr(pos, 'Zoom'):
                    print(f"   Zoom (縮放): {pos.Zoom.x:.4f}")
            
            if hasattr(status, 'MoveStatus'):
                ms = status.MoveStatus
                print(f"   移動狀態: PanTilt={getattr(ms, 'PanTilt', 'N/A')}, Zoom={getattr(ms, 'Zoom', 'N/A')}")
            
            return status_dict
            
        except Exception as e:
            print(f"✗ 無法獲取狀態: {e}")
            return {}
    
    def get_current_position(self) -> Tuple[float, float, float]:
        """
        獲取當前座標（這是 ONVIF 相比 pytapo 的主要優勢！）
        
        Returns:
            tuple: (pan, tilt, zoom) 座標
        """
        try:
            status = self.ptz_service.GetStatus({'ProfileToken': self.media_profile.token})
            
            pan = 0.0
            tilt = 0.0
            zoom = 0.0
            
            if hasattr(status, 'Position'):
                pos = status.Position
                if hasattr(pos, 'PanTilt'):
                    pan = pos.PanTilt.x
                    tilt = pos.PanTilt.y
                if hasattr(pos, 'Zoom'):
                    zoom = pos.Zoom.x
            
            return (pan, tilt, zoom)
            
        except Exception as e:
            print(f"✗ 無法獲取座標: {e}")
            return (0.0, 0.0, 0.0)
    
    # ========== 預設位置 ==========
    
    def get_presets(self) -> Dict[str, str]:
        """
        獲取所有預設位置
        
        Returns:
            dict: {token: name} 預設位置字典
        """
        try:
            presets = self.ptz_service.GetPresets({'ProfileToken': self.media_profile.token})
            preset_dict = {}
            
            print(f"📋 預設位置 ({len(presets)} 個):")
            for preset in presets:
                preset_dict[preset.token] = preset.Name
                
                # 顯示預設位置的座標（如果有）
                if hasattr(preset, 'PTZPosition'):
                    pos = preset.PTZPosition
                    pan = pos.PanTilt.x if hasattr(pos, 'PanTilt') else 'N/A'
                    tilt = pos.PanTilt.y if hasattr(pos, 'PanTilt') else 'N/A'
                    print(f"   Token {preset.token}: {preset.Name} (Pan={pan}, Tilt={tilt})")
                else:
                    print(f"   Token {preset.token}: {preset.Name}")
            
            return preset_dict
            
        except Exception as e:
            print(f"✗ 無法獲取預設位置: {e}")
            return {}
    
    def goto_preset(self, preset_token: str, speed: float = 1.0):
        """
        移動到預設位置
        
        Args:
            preset_token: 預設位置 Token
            speed: 移動速度 (0.0 ~ 1.0)
        """
        try:
            request = self.ptz_service.create_type('GotoPreset')
            request.ProfileToken = self.media_profile.token
            request.PresetToken = preset_token
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            self.ptz_service.GotoPreset(request)
            print(f"✓ 正在移動到預設位置: {preset_token}")
            
        except Exception as e:
            print(f"✗ 移動到預設位置失敗: {e}")
    
    def set_preset(self, preset_name: str, preset_token: str = None) -> str:
        """
        設定當前位置為預設
        
        Args:
            preset_name: 預設位置名稱
            preset_token: 預設 Token（可選，不提供則自動生成）
            
        Returns:
            str: 預設位置 Token
        """
        try:
            request = self.ptz_service.create_type('SetPreset')
            request.ProfileToken = self.media_profile.token
            request.PresetName = preset_name
            
            if preset_token:
                request.PresetToken = preset_token
            
            response = self.ptz_service.SetPreset(request)
            token = response.PresetToken
            print(f"✓ 已設定預設位置: {preset_name} (Token: {token})")
            return token
            
        except Exception as e:
            print(f"✗ 設定預設位置失敗: {e}")
            return ""
    
    def remove_preset(self, preset_token: str):
        """
        移除預設位置
        
        Args:
            preset_token: 預設位置 Token
        """
        try:
            self.ptz_service.RemovePreset({
                'ProfileToken': self.media_profile.token,
                'PresetToken': preset_token
            })
            print(f"✓ 已移除預設位置: {preset_token}")
            
        except Exception as e:
            print(f"✗ 移除預設位置失敗: {e}")
    
    # ========== Home 位置 ==========
    
    def goto_home(self, speed: float = 1.0):
        """移動到 Home 位置"""
        try:
            request = self.ptz_service.create_type('GotoHomePosition')
            request.ProfileToken = self.media_profile.token
            request.Speed = {
                'PanTilt': {'x': speed, 'y': speed},
                'Zoom': {'x': speed}
            }
            
            self.ptz_service.GotoHomePosition(request)
            print("🏠 正在移動到 Home 位置")
            
        except Exception as e:
            print(f"✗ 移動到 Home 位置失敗: {e}")
    
    def set_home(self):
        """設定當前位置為 Home"""
        try:
            self.ptz_service.SetHomePosition({'ProfileToken': self.media_profile.token})
            print("🏠 已設定當前位置為 Home")
            
        except Exception as e:
            print(f"✗ 設定 Home 位置失敗: {e}")
    
    # ========== 設備資訊 ==========
    
    def get_device_info(self) -> Dict[str, Any]:
        """獲取設備資訊"""
        try:
            info = self.camera.devicemgmt.GetDeviceInformation()
            return serialize_object(info)
        except Exception as e:
            print(f"✗ 無法獲取設備資訊: {e}")
            return {}
    
    def get_capabilities(self) -> Dict[str, Any]:
        """獲取設備能力"""
        try:
            caps = self.camera.devicemgmt.GetCapabilities()
            return serialize_object(caps)
        except Exception as e:
            print(f"✗ 無法獲取設備能力: {e}")
            return {}
    
    def get_ptz_nodes(self) -> list:
        """獲取 PTZ 節點資訊"""
        try:
            nodes = self.ptz_service.GetNodes()
            return serialize_object(nodes)
        except Exception as e:
            print(f"✗ 無法獲取 PTZ 節點: {e}")
            return []


def demo():
    """ONVIF 控制示範"""
    print("=" * 60)
    print("Tapo C225 ONVIF PTZ 控制系統 - 示範")
    print("=" * 60)
    
    # 配置（請根據實際環境修改）
    HOST = "192.168.1.100"
    PORT = 2020  # Tapo ONVIF 預設埠號
    USER = "your_camera_account"  # 在 Tapo App 設定的帳戶
    PASSWORD = "your_camera_password"
    
    # 建立控制器
    controller = TapoONVIFController(HOST, PORT, USER, PASSWORD)
    
    # 連接
    if not controller.connect():
        return
    
    print("\n--- 基本功能示範 ---")
    
    # 1. 獲取 RTSP URL
    print("\n1. RTSP 串流 URL:")
    print(f"   主串流: {controller.get_rtsp_url(1)}")
    print(f"   次串流: {controller.get_rtsp_url(2)}")
    
    # 2. 獲取當前狀態和座標（ONVIF 優勢！）
    print("\n2. 當前 PTZ 狀態:")
    controller.get_status()
    
    # 3. 獲取當前座標
    print("\n3. 當前座標:")
    pan, tilt, zoom = controller.get_current_position()
    print(f"   Pan={pan:.4f}, Tilt={tilt:.4f}, Zoom={zoom:.4f}")
    
    # 4. 絕對位置移動
    print("\n4. 絕對位置移動 (移動到中心位置):")
    controller.move_to_position(pan=0.0, tilt=0.0)
    time.sleep(3)
    
    # 5. 驗證移動後的座標
    print("\n5. 移動後座標:")
    controller.get_current_position()
    
    # 6. 預設位置管理
    print("\n6. 預設位置:")
    presets = controller.get_presets()
    
    # 7. 設定新的預設位置
    print("\n7. 設定新預設位置:")
    controller.move_to_position(pan=0.5, tilt=0.3)
    time.sleep(2)
    token = controller.set_preset("ONVIF_測試位置")
    
    # 8. 移動到 Home
    print("\n8. 移動到 Home 位置:")
    controller.goto_home()
    time.sleep(3)
    
    # 9. 回到剛設定的預設位置
    if token:
        print("\n9. 回到預設位置:")
        controller.goto_preset(token)
        time.sleep(3)
    
    print("\n" + "=" * 60)
    print("示範完成")
    print("=" * 60)
    print("\nONVIF 的主要優勢：")
    print("1. ✓ 支援絕對座標（可以知道精確位置）")
    print("2. ✓ 標準化協定（可整合 NVR/NAS）")
    print("3. ✓ 支援 RTSP 串流")
    print("4. ✓ PTZ 控制功能完整")


if __name__ == "__main__":
    demo()
