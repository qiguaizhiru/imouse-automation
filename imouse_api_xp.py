# iMouse XP API Wrapper (adapted from Pro version)
# Port: 9911, uses XP endpoint paths
# Reconstructed from imouse_api.pyc (Python 3.12)
import base64
import json
import threading
import time
import traceback
import requests
from requests.adapters import HTTPAdapter
from websocket import WebSocketApp


class HttpApi:
    """
    http接口封装
    所有接口的sync参数http调用都无效,http只支持同步调用
    """

    def __init__(self, host='127.0.0.1'):
        self._api_url = f"http://{host}:9911/api"
        self._data_creation = Data_Creation()
        self._msgid = 0
        self._session = requests.Session()
        self._adapter = HTTPAdapter()
        self._session.mount("http://", self._adapter)

    def _utf8_to_hex(self, input_str: str) -> str:
        """将 UTF-8 字符串转换为十六进制表示的字符串"""
        return ''.join(f'{b:02x}' for b in input_str.encode('utf-8'))

    def _hex_to_utf8(self, hex_str: str) -> str:
        """将十六进制字符串还原为 UTF-8 编码的字符串"""
        if len(hex_str) % 2 != 0:
            raise ValueError("Invalid hex string length. Must be a multiple of 2.")
        return bytes(int(hex_str[i:i+2], 16) for i in range(0, len(hex_str), 2)).decode('utf-8')

    def _get_msgid(self, sync=True):
        if sync:
            self._msgid += 1
            return self._msgid
        return 0

    def get_device_list(self, sync=True):
        """获取设备列表"""
        return self._post(self._data_creation.get_device_list(self._get_msgid(sync)))

    def get_group_list(self, sync=True):
        """获取分组列表"""
        return self._post(self._data_creation.get_group_list(self._get_msgid(sync)))

    def get_usb_list(self, sync=True):
        """获取已连接USB列表"""
        return self._post(self._data_creation.get_usb_list(self._get_msgid(sync)))

    def get_devicemodel_list(self, sync=True):
        """获取设备型号列表"""
        return self._post(self._data_creation.get_devicemodel_list(self._get_msgid(sync)))

    def change_dev_name(self, deviceid='', name='', sync=True):
        """修改设备名称"""
        return self._post(self._data_creation.set_dev(deviceid, self._get_msgid(sync), {"name": name}))

    def change_dev_group(self, deviceid='', group_id='', sync=True):
        """修改设备分组"""
        return self._post(self._data_creation.set_dev(deviceid, self._get_msgid(sync), {"gid": group_id}))

    def change_dev_usb_id(self, deviceid='', vid='', pid='', sync=True):
        """修改设备usb设备id"""
        return self._post(self._data_creation.set_dev(deviceid, self._get_msgid(sync), {"vid": vid, "pid": pid}))

    def change_dev_location(self, deviceid='', location_crc='', sync=True):
        """修改设备usb设备物理位置"""
        return self._post(self._data_creation.set_dev(deviceid, self._get_msgid(sync), {"location_crc": location_crc}))

    def del_dev(self, deviceid='', sync=True):
        """删除设备"""
        return self._post(self._data_creation.del_dev(deviceid, self._get_msgid(sync)))

    def set_group(self, gid=0, name='', sync=True):
        """设置分组, gid为0则新增分组"""
        return self._post(self._data_creation.set_group(gid, name, self._get_msgid(sync)))

    def del_group(self, gid=0, sync=True):
        """删除分组"""
        return self._post(self._data_creation.del_group(gid, self._get_msgid(sync)))

    def get_device_screenshot(self, deviceid='', gzip=False, sync=True, binary=False, isJpg=True, original=False):
        """获取设备屏幕"""
        return self._post(self._data_creation.get_device_screenshot(deviceid, gzip, binary, self._get_msgid(sync), isJpg, original))

    def click(self, deviceid='', x=0, y=0, button='left', time=0, sync=True):
        """鼠标单击"""
        return self._post(self._data_creation.click(deviceid, x, y, button, time, self._get_msgid(sync)))

    def swipe(self, deviceid='', direction='left', button='left', length=0, sx=0, sy=0, ex=0, ey=0, afor=0, sync=True):
        """鼠标滑动"""
        return self._post(self._data_creation.swipe(deviceid, direction, button, length, sx, sy, ex, ey, afor, self._get_msgid(sync)))

    def mouse_up(self, deviceid='', button='left', sync=True):
        """鼠标弹起"""
        return self._post(self._data_creation.mouse_up(deviceid, button, self._get_msgid(sync)))

    def mouse_down(self, deviceid='', button='left', sync=True):
        """鼠标按下"""
        return self._post(self._data_creation.mouse_down(deviceid, button, self._get_msgid(sync)))

    def mouse_move(self, deviceid='', x=0, y=0, sync=True):
        """鼠标移动"""
        return self._post(self._data_creation.mouse_move(deviceid, x, y, self._get_msgid(sync)))

    def mouse_wheel(self, deviceid='', direction='up', length=0, number=1, sync=True):
        """鼠标滚轮"""
        return self._post(self._data_creation.mouse_wheel(deviceid, direction, length, number, self._get_msgid(sync)))

    def mouse_reset_pos(self, deviceid='', sync=True):
        """鼠标复位"""
        return self._post(self._data_creation.mouse_reset_pos(deviceid, self._get_msgid(sync)))

    def send_key(self, deviceid='', key='', fn_key=None, sync=True):
        """键盘输入"""
        return self._post(self._data_creation.send_key(deviceid, key, fn_key, self._get_msgid(sync)))

    def restart(self, sync=True):
        """重启内核"""
        return self._post(self._data_creation.restart(self._get_msgid(sync)))

    def get_airplaysrvnum(self, sync=True):
        """获取投屏服务数"""
        return self._post(self._data_creation.get_airplaysrvnum(self._get_msgid(sync)))

    def set_airplaysrvnum(self, airplaysrvnum=0, sync=True):
        """设置投屏服务数"""
        return self._post(self._data_creation.set_airplaysrvnum(airplaysrvnum, self._get_msgid(sync)))

    def mouse_collection_open(self, deviceid='', sync=True):
        """打开鼠标坐标采集"""
        return self._post(self._data_creation.mouse_collection_open(deviceid, self._get_msgid(sync)))

    def mouse_collection_close(self, deviceid='', sync=True):
        """关闭鼠标坐标采集"""
        return self._post(self._data_creation.mouse_collection_close(deviceid, self._get_msgid(sync)))

    def save_dev_location(self, deviceid='', describe='', sync=True):
        """保存设备物理位置通用卡"""
        return self._post(self._data_creation.save_dev_location(deviceid, describe, self._get_msgid(sync)))

    def del_dev_location(self, model='', version='', crc='', sync=True):
        """从通用卡删除物理位置"""
        return self._post(self._data_creation.del_dev_location(model, version, crc, self._get_msgid(sync)))

    def send_text(self, deviceid='', text='', fn_key=None, sync=True):
        """发送批量字符"""
        return self._post(self._data_creation.send_text(deviceid, text, fn_key, self._get_msgid(sync)))

    def find_image(self, deviceid='', img=None, rect=None, original=False, similarity=0.8, sync=True):
        """查找图片"""
        if img and not isinstance(img, str):
            img = base64.b64encode(img).decode()
        return self._post(self._data_creation.find_image(deviceid, img, rect, original, similarity, self._get_msgid(sync)))

    def find_imageEx(self, deviceid='', img_list=None, rect=None, original=False, all=False, repeat=1, similarity=0.8, sync=True):
        """查找图片 支持同时查找多张图片"""
        encoded_list = []
        if img_list:
            for img in img_list:
                if img and not isinstance(img, str):
                    encoded_list.append(base64.b64encode(img).decode())
                else:
                    encoded_list.append(img)
        return self._post(self._data_creation.find_imageEx(deviceid, encoded_list, rect, original, similarity, all, repeat, self._get_msgid(sync)))

    def ocr(self, deviceid='', rect=None, original=False, sync=True):
        """ocr文字识别_普通模式"""
        return self._post(self._data_creation.ocr('ocr', deviceid, rect, original, self._get_msgid(sync)))

    def ocr_ex(self, deviceid='', rect=None, original=False, sync=True):
        """ocr文字识别_增强模式"""
        return self._post(self._data_creation.ocr('ocr_ex', deviceid, rect, original, self._get_msgid(sync)))

    def find_multi_color(self, deviceid='', first_color='', offset_color='', rect=None, similarity=0.8, dir=0, sync=True):
        """多点找色"""
        return self._post(self._data_creation.find_multi_color(deviceid, rect, first_color, offset_color, similarity, dir, self._get_msgid(sync)))

    def save_autoscreen_point(self, deviceid='', sync=True):
        """获取自动投屏物理位置"""
        return self._post(self._data_creation.save_autoscreen_point(deviceid, self._get_msgid(sync)))

    def restart_usb(self, deviceid='', sync=True):
        """重启USB设备"""
        return self._post(self._data_creation.restart_usb(deviceid, self._get_msgid(sync)))

    def set_usb_autoairplay(self, deviceid='', autoairplay=False, sync=True):
        """设置是否自动投屏"""
        return self._post(self._data_creation.set_usb_autoairplay(deviceid, autoairplay, self._get_msgid(sync)))

    def get_usb_autoairplay(self, deviceid='', sync=True):
        """获取是否自动投屏状态"""
        return self._post(self._data_creation.get_usb_autoairplay(deviceid, self._get_msgid(sync)))

    def set_airplay_mode(self, deviceid='', airplay_mode=0, sync=True):
        """设置投屏画面模式"""
        return self._post(self._data_creation.set_airplay_mode(deviceid, airplay_mode, self._get_msgid(sync)))

    def get_airplay_mode(self, deviceid='', sync=True):
        """获取投屏画面模式"""
        return self._post(self._data_creation.get_airplay_mode(deviceid, self._get_msgid(sync)))

    def save_restart_point(self, deviceid='', sync=True):
        """获取重启手机物理位置"""
        return self._post(self._data_creation.save_restart_point(deviceid, self._get_msgid(sync)))

    def restart_device(self, deviceid='', sync=True):
        """重启手机"""
        return self._post(self._data_creation.restart_device(deviceid, self._get_msgid(sync)))

    def restart_mdns(self, srvname='', sync=True):
        """重启发现服务"""
        return self._post(self._data_creation.set_mdns(srvname, self._get_msgid(sync)))

    def off_mdns(self, srvname='', sync=True):
        """关闭发现服务"""
        return self._post(self._data_creation.set_mdns(srvname, self._get_msgid(sync)))

    def open_mdns(self, srvname='', sync=True):
        """开启发现服务"""
        return self._post(self._data_creation.set_mdns(srvname, self._get_msgid(sync)))

    def auto_connect_screen_all(self, sync=True):
        """自动投屏所有在线或离线"""
        return self._post(self._data_creation.auto_connect_screen_all(self._get_msgid(sync)))

    def discon_airplay(self, deviceid='', sync=True):
        """断开投屏"""
        return self._post(self._data_creation.discon_airplay(deviceid, self._get_msgid(sync)))

    def shortcut_photo_list(self, deviceid='', num=5, date='', outtime=30000):
        """获取手机照片列表 - XP: /shortcut/album/get"""
        ret = self._post({"fun": "/shortcut/album/get", "data": {
            "id": deviceid, "album_name": "", "num": num, "outtime": outtime
        }, "msgid": self._get_msgid(True)})
        if ret and ret.get('status') == 200:
            return ret.get('data', {})
        return ret

    def shortcut_down_photo(self, deviceid='', files=None, outtime=30000):
        """下载照片"""
        return self._post(self._data_creation.shortcut(deviceid, 2, [], json.dumps({"name": files or []}), outtime, self._get_msgid(True)))

    def shortcut_del_photo(self, deviceid='', files=None, devlist=None, outtime=30000):
        """删除照片 - XP: /shortcut/album/clear (清空全部)"""
        return self._post({"fun": "/shortcut/album/clear", "data": {
            "id": deviceid, "album_name": "", "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_file_list(self, deviceid='', path='', outtime=30000):
        """获取文件列表"""
        ret = self._post(self._data_creation.shortcut(deviceid, 4, [], json.dumps({"path": path}), outtime, self._get_msgid(True)))
        if ret and 'retdata' in ret:
            return ret['retdata']
        return ret

    def shortcut_down_file(self, deviceid='', files=None, outtime=30000):
        """下载文件"""
        return self._post(self._data_creation.shortcut(deviceid, 5, [], json.dumps({"name": files or []}), outtime, self._get_msgid(True)))

    def shortcut_del_file(self, deviceid='', files=None, devlist=None, outtime=30000):
        """删除文件 - XP: /shortcut/file/del"""
        return self._post({"fun": "/shortcut/file/del", "data": {
            "id": deviceid, "path": "", "list": files or [], "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_up_photo(self, deviceid='', files=None, name='Recents', devlist=None, outtime=60000):
        """上传照片/视频 - XP: /shortcut/album/upload"""
        return self._post({"fun": "/shortcut/album/upload", "data": {
            "id": deviceid, "album_name": name, "zip": 0,
            "files": files or [], "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_up_file(self, deviceid='', files=None, path='', devlist=None, outtime=60000):
        """上传文件 - XP: /shortcut/file/upload"""
        return self._post({"fun": "/shortcut/file/upload", "data": {
            "id": deviceid, "path": path, "zip": 0,
            "files": files or [], "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_send_clipboard(self, deviceid='', text='', devlist=None, outtime=30000):
        """发送文字到手机剪切板 - XP: /shortcut/clipboard/set"""
        return self._post({"fun": "/shortcut/clipboard/set", "data": {
            "id": deviceid, "text": text, "sleep": 0, "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_get_clipboard(self, deviceid='', devlist=None, outtime=30000):
        """获取手机剪切板 - XP: /shortcut/clipboard/get"""
        ret = self._post({"fun": "/shortcut/clipboard/get", "data": {
            "id": deviceid, "outtime": outtime
        }, "msgid": self._get_msgid(True)})
        if ret and ret.get('status') == 200:
            rd = ret.get('data', {})
            if isinstance(rd, dict) and 'text' in rd:
                return rd
        return ret

    def shortcut_open_url(self, deviceid='', url='', devlist=None, outtime=30000):
        """打开url - XP: /shortcut/exec/url"""
        return self._post({"fun": "/shortcut/exec/url", "data": {
            "id": deviceid, "url": url, "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_set_lightness(self, deviceid='', level=1.0, devlist=None, outtime=30000):
        """设置屏幕亮度 - XP: /shortcut/switch/bril"""
        return self._post({"fun": "/shortcut/switch/bril", "data": {
            "id": deviceid, "state": level, "outtime": outtime
        }, "msgid": self._get_msgid(True)})

    def shortcut_get_ip(self, deviceid='', outtime=30000):
        """获取设备ip"""
        return self._post(self._data_creation.shortcut(deviceid, 15, [], '{}', outtime, self._get_msgid(True)))

    def _post(self, post_data):
        return self._session.post(self._api_url, json=post_data).json()


class WsApi(HttpApi):
    """WebSocket API 客户端"""

    def __init__(self, host='127.0.0.1', on_message=None, on_binary=None, QApplication=None, debug=False):
        super().__init__(host)
        self._host = host
        self._is_work = False
        self._QApplication = QApplication
        self._is_connect = False
        self._recv_msg_list = {}
        self._callback = on_message
        self._bmp_callback = on_binary
        self._debug = debug
        self._outtime = 30
        self._ws_command = None

    def start(self):
        if not self._is_work:
            self._is_work = True
            threading.Thread(target=self._init_ws_command, daemon=True).start()

    def stop(self):
        self._is_work = False
        if self._ws_command:
            self._ws_command.close()

    def is_onnect(self):
        return self._is_connect

    def _print_log(self, log):
        if self._debug:
            print(log)

    def _init_ws_command(self):
        self._ws_command = WebSocketApp(
            "ws://{}:9911/api".format(self._host),
            on_data=self.on_data,
            on_error=self._on_error,
            on_open=self._on_open,
            on_close=self._on_close
        )
        while self._is_work:
            try:
                self._ws_command.run_forever()
            except:
                pass
            time.sleep(3)
            if not self._is_work:
                break
            self._is_connect = False
            if self._callback:
                try:
                    self._callback({"fun": "connect_disconnect", "status": 0})
                except:
                    pass
        try:
            if self._ws_command:
                self._ws_command.close()
        except KeyboardInterrupt:
            pass

    def loop_device_screenshot(self, deviceid='', time=100, stop=False, isJpg=True, sync=False):
        """循环获取设备屏幕"""
        return self._post(self._data_creation.loop_device_screenshot(deviceid, time, stop, self._get_msgid(sync), isJpg))

    def auto_connect_screen(self, deviceid='', force=False, sync=True):
        """自动投屏"""
        return self._post(self._data_creation.auto_connect_screen(deviceid, force, self._get_msgid(sync)))

    def mouse_collection_cfg(self, deviceid='', sync=True):
        """鼠标坐标采集"""
        return self._post(self._data_creation.mouse_collection_cfg(deviceid, self._get_msgid(sync)))

    def _post(self, post_data):
        if not self._ws_command:
            return None
        self._ws_command.send(json.dumps(post_data))
        msgid = post_data.get('msgid', 0)
        if msgid == 0:
            return post_data
        # Sync mode: wait for response
        fun = post_data.get('fun', '')
        if fun == 'loop_device_screenshot':
            return post_data
        start = time.time()
        while time.time() - start < self._outtime:
            if self._QApplication:
                self._QApplication.processEvents()
            if msgid in self._recv_msg_list:
                return self._recv_msg_list.pop(msgid)
            time.sleep(0.01)
        return {"fun": "/pic/" + fun, "status": -1, "message": "接口调用超时"}

    def on_data(self, ws, message, data_type, continue_flag):
        import websocket
        if data_type == websocket.ABNF.OPCODE_BINARY:
            if self._bmp_callback:
                self._bmp_callback(message)
        elif data_type == websocket.ABNF.OPCODE_TEXT:
            self._msgEvent(ws, message)

    def _on_error(self, ws, error):
        self._ws_command = ws
        self._print_log("_ws_command连接错误{}".format(error))

    def _on_close(self, ws, *args):
        self._ws_command = ws
        self._is_connect = False
        self._print_log("_ws_command连接关闭...")

    def _on_open(self, ws):
        self._ws_command = ws
        self._is_connect = True
        self._print_log("_ws_command连接成功...")
        if self._callback:
            self._callback({"fun": "connect", "status": 0})

    def send(self, params):
        if self._ws_command:
            self._ws_command.send(params)

    def sync_send(self, params):
        self.send(params)

    def _msgEvent(self, ws, message):
        try:
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            data = json.loads(message)
            msgid = data.get('msgid', 0)
            if msgid:
                self._recv_msg_list[msgid] = data
            if self._callback:
                self._callback(data)
        except Exception:
            traceback.print_exc()


class Data_Creation:
    """构建 API 请求数据"""

    def set_dev(self, deviceid='', msgid=0, data=None):
        result = {"fun": "/device/set", "data": {"id": deviceid}, "msgid": msgid}
        if data:
            result["data"].update(data)
        return result

    def del_dev(self, deviceid='', msgid=0):
        return {"fun": "/device/del", "data": {"id": deviceid}, "msgid": msgid}

    def set_group(self, gid=0, name='', msgid=0):
        return {"fun": "/device/group/set", "data": {"gid": gid, "name": name}, "msgid": msgid}

    def del_group(self, gid=0, msgid=0):
        return {"fun": "/device/group/del", "data": {"gid": gid}, "msgid": msgid}

    def get_device_list(self, msgid=0):
        return {"fun": "/device/get", "data": {}, "msgid": msgid}

    def get_group_list(self, msgid=0):
        return {"fun": "/device/group/get", "data": {}, "msgid": msgid}

    def get_usb_list(self, msgid=0):
        return {"fun": "/config/usb/get", "data": {}, "msgid": msgid}

    def get_devicemodel_list(self, msgid=0):
        return {"fun": "/config/devicemodel/get", "data": {}, "msgid": msgid}

    def get_device_screenshot(self, deviceid='', gzip=False, binary=False, msgid=0, isJpg=True, original=False):
        return {"fun": "/pic/screenshot", "data": {
            "id": deviceid, "binary": binary, "jpg": isJpg,
            "rect": []
        }, "msgid": msgid}

    def loop_device_screenshot(self, deviceid='', time=100, stop=False, msgid=0, isJpg=True):
        return {"fun": "/pic/screenshot", "data": {
            "id": deviceid, "time": time, "stop": stop, "isjpg": isJpg
        }, "msgid": msgid}

    def click(self, deviceid='', x=0, y=0, button='left', time=0, msgid=0):
        return {"fun": "/mouse/click", "data": {
            "id": deviceid, "button": 1 if button=="left" else (2 if button=="right" else int(button) if str(button).isdigit() else 1), "x": x, "y": y, "time": time
        }, "msgid": msgid}

    def swipe(self, deviceid='', direction='left', button='left', length=0,
              sx=0, sy=0, ex=0, ey=0, afor=0, msgid=0):
        return {"fun": "/mouse/swipe", "data": {
            "id": deviceid, "direction": direction, "button": 1 if button=="left" else (2 if button=="right" else int(button) if str(button).isdigit() else 1),
            "len": length, "sx": sx, "sy": sy, "ex": ex, "ey": ey, "for": afor
        }, "msgid": msgid}

    def mouse_up(self, deviceid='', button='left', msgid=0):
        return {"fun": "/mouse/up", "data": {"id": deviceid, "button": 1 if button=="left" else (2 if button=="right" else int(button) if str(button).isdigit() else 1)}, "msgid": msgid}

    def mouse_down(self, deviceid='', button='left', msgid=0):
        return {"fun": "/mouse/down", "data": {"id": deviceid, "button": 1 if button=="left" else (2 if button=="right" else int(button) if str(button).isdigit() else 1)}, "msgid": msgid}

    def mouse_move(self, deviceid='', x=0, y=0, msgid=0):
        return {"fun": "/mouse/move", "data": {"id": deviceid, "x": x, "y": y}, "msgid": msgid}

    def mouse_wheel(self, deviceid='', direction='up', length=0, number=1, msgid=0):
        return {"fun": "/mouse/wheel", "data": {
            "id": deviceid, "direction": direction, "len": length, "number": number
        }, "msgid": msgid}

    def mouse_reset_pos(self, deviceid='', msgid=0):
        return {"fun": "/mouse/reset", "data": {"id": deviceid}, "msgid": msgid}

    def send_key(self, deviceid='', key='', fn_key=None, msgid=0):
        result = {"fun": "/key/sendkey", "data": {"id": deviceid, "key": key}, "msgid": msgid}
        if fn_key:
            result["data"]["fn_key"] = fn_key
        return result

    def restart(self, msgid=0):
        return {"fun": "/imserver/restart", "data": {}, "msgid": msgid}

    def get_airplaysrvnum(self, msgid=0):
        return {"fun": "get_airplaysrvnum", "data": {}, "msgid": msgid}

    def set_airplaysrvnum(self, airplaysrvnum=0, msgid=0):
        return {"fun": "set_airplaysrvnum", "data": {"airplaysrvnum": airplaysrvnum}, "msgid": msgid}

    def mouse_collection_open(self, deviceid='', msgid=0):
        return {"fun": "/device/collection/mouse", "data": {"id": deviceid}, "msgid": msgid}

    def mouse_collection_close(self, deviceid='', msgid=0):
        return {"fun": "/device/collection/mouse", "data": {"id": deviceid}, "msgid": msgid}

    def mouse_collection_cfg(self, deviceid='', msgid=0):
        return {"fun": "/device/collection/mouse", "data": {"id": deviceid}, "msgid": msgid}

    def save_dev_location(self, deviceid='', describe='', msgid=0):
        return {"fun": "save_dev_location", "data": {"id": deviceid, "describe": describe}, "msgid": msgid}

    def del_dev_location(self, model='', version='', crc='', msgid=0):
        return {"fun": "del_dev_location", "data": {"model": model, "version": version, "crc": crc}, "msgid": msgid}

    def send_text(self, deviceid='', key='', fn_key=None, msgid=0):
        return {"fun": "/key/sendkey", "data": {"id": deviceid, "key": key, "fn_key": fn_key}, "msgid": msgid}

    def find_image(self, deviceid='', img=None, rect=None, original=False, similarity=0.8, msgid=0):
        result = {"fun": "/pic/find-image", "data": {
            "id": deviceid, "img": img, "original": original, "similarity": similarity
        }, "msgid": msgid}
        if rect:
            result["data"]["rect"] = rect
        return result

    def find_imageEx(self, deviceid='', img_list=None, rect=None, original=False,
                     similarity=0.8, all=False, repeat=1, msgid=0):
        result = {"fun": "/pic/find-image", "data": {
            "id": deviceid, "img_list": img_list or [], "original": original,
            "similarity": similarity, "all": all, "repeat": repeat
        }, "msgid": msgid}
        if rect:
            result["data"]["rect"] = rect
        return result

    def ocr(self, fun='ocr', deviceid='', rect=None, original=False, msgid=0):
        result = {"fun": "/pic/" + fun, "data": {"id": deviceid, "original": original}, "msgid": msgid}
        if rect:
            result["data"]["rect"] = rect
        return result

    def find_multi_color(self, deviceid='', rect=None, first_color='', offset_color='',
                         similarity=0.8, dir=0, msgid=0):
        return {"fun": "/pic/find-multi-color", "data": {
            "id": deviceid, "rect": rect, "first_color": first_color,
            "offset_color": offset_color, "similarity": similarity, "dir": dir
        }, "msgid": msgid}

    def auto_connect_screen(self, deviceid='', force=False, msgid=0):
        return {"fun": "/device/airplay/connect", "data": {"id": deviceid, "force": force}, "msgid": msgid}

    def save_autoscreen_point(self, deviceid='', msgid=0):
        return {"fun": "save_autoscreen_point", "data": {"id": deviceid}, "msgid": msgid}

    def restart_usb(self, deviceid='', msgid=0):
        return {"fun": "/device/usb/restart", "data": {"id": deviceid}, "msgid": msgid}

    def set_usb_autoairplay(self, deviceid='', autoairplay=False, msgid=0):
        return {"fun": "set_usb_autoairplay", "data": {"id": deviceid, "autoairplay": autoairplay}, "msgid": msgid}

    def get_usb_autoairplay(self, deviceid='', msgid=0):
        return {"fun": "get_usb_autoairplay", "data": {"id": deviceid}, "msgid": msgid}

    def set_airplay_mode(self, deviceid='', airplay_mode=0, msgid=0):
        return {"fun": "set_airplay_mode", "data": {"id": deviceid, "airplay_mode": airplay_mode}, "msgid": msgid}

    def get_airplay_mode(self, deviceid='', msgid=0):
        return {"fun": "get_airplay_mode", "data": {"id": deviceid}, "msgid": msgid}

    def save_restart_point(self, deviceid='', msgid=0):
        return {"fun": "save_restart_point", "data": {"id": deviceid}, "msgid": msgid}

    def restart_device(self, deviceid='', msgid=0):
        return {"fun": "/device/restart", "data": {"id": deviceid}, "msgid": msgid}

    def set_mdns(self, srvname='', msgid=0):
        return {"fun": "set_mdns", "data": {"srvname": srvname}, "msgid": msgid}

    def auto_connect_screen_all(self, msgid=0):
        return {"fun": "/device/airplay/connect/all", "data": {}, "msgid": msgid}

    def discon_airplay(self, deviceid='', msgid=0):
        return {"fun": "/device/airplay/disconnect", "data": {"id": deviceid}, "msgid": msgid}

    def shortcut(self, deviceid='', id=0, devlist=None, parameter='', outtime=30000, msgid=0):
        return {"fun": "shortcut", "data": {
            "id": deviceid, "id": id, "devlist": devlist or [],
            "parameter": json.dumps(parameter) if isinstance(parameter, (dict, list)) else parameter,
            "outtime": outtime
        }, "msgid": msgid}
