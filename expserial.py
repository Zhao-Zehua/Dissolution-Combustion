# Author: 安孝彦
# 第三方库
from func_timeout import func_set_timeout
from serial import Serial, SerialException
from serial.serialutil import PortNotOpenError
from serial.tools import list_ports

# 有如下几种报错
# 找不到端口 SerialException FileNotFoundError
# 已经打开的端口重复打开 SerialException Port is already open (但重复关闭不会有问题)
# 端口被占用 SerialException PermissionError
# 使用未打开端口 serialutil.PortNotOpenError
# 突然断开连接 SerialException GetOverlappedResult（关机没问题，只有拔线有问题）
# 断开后重新插回 SerialException ClearCommError （好像只有重新连接一种解决方法）

# 启动时会有一段FF 80 0A/0B 0D 0E 0A 0A的数据，注意处理。

COMPORTS = []   # 存储端口信息
port_status = False # 初始化端口状态

# 获取可用端口信息
def getComPorts(select = False, timeout: float = 0.25):
    global COMPORTS, port_status
    # 使用装饰器设置超时时间
    @func_set_timeout(timeout)   # 设置超时时间为0.25s
    def detectComPort(port_name):
        global port_status
        try:
            with Serial(port_name, 1200, timeout = 1) as ser:   # 打开信息为port_name的端口，波特率1200，超时1s
                port_read = ser.read(7)
                if len(port_read) < 7:  # 如果读取的数据长度小于7，说明没有数据传入
                    return    # 跳过本次循环
                else:
                    port_status = True
                    return
        except Exception:   # 如果出现异常
            return    # 跳过本次循环
    # 检测端口是否可用
    COMPORTS = []   # 清空端口信息
    all_ports = list_ports.comports()   # 获取所有端口信息
    for port_info in all_ports:
        port_status = False # 默认当前检测的端口不可用
        port_name = str(port_info.device)   # 遍历获取端口信息
        if select:
            try:
                detectComPort(port_name)    # 检测端口是否可用
            except:
                pass
        if port_status:
            COMPORTS.append(port_name)
    return sorted(COMPORTS, key = lambda x: x[3: ]) # 返回端口信息

# 计算温差
def derive_Delta_T(msg):
    dT = msg[3] + (msg[4] + (msg[5] + msg[6] / 10) / 10) / 10
    if msg[2] == 10:
        pass
    elif msg[2] == 11:
        dT = -dT
    elif msg[2] == 1:
        dT += 10
    elif msg[2] == 12:
        dT = -10 - dT
    return dT


class EasySerial:
    """
    将serial的Serial打包成在本实验中更易使用的结构
    """

    def __init__(self, name, baud = 1200):  # 除非更换设备，否则此处波特率1200不要改
        self._name = name   # 端口名
        self._baud = baud   # 波特率
        self._port = None   # 未打开端口
        self._changed = False   # 端口名改变标志位，初始为False，改变后为True

    # 设置要打开的端口
    def setName(self, name):
        self._name = name
        self._changed = True

    # 打开端口
    def open(self):
        self.close()    # 先关闭可能打开的端口
        if self._changed or self._port is None: # 如果端口名改变或端口未打开
            try:
                self._port = Serial(self._name, self._baud) # 打开端口
                self._changed = False   # 端口名改变标志位清零
            except SerialException as e:
                self._port = None   # 未打开端口
                s = str(e)
                if "PermissionError" in s:  # 最可能是多开造成的
                    raise PermissionError("端口被占用！请查找可能占用端口的程序！")
                elif "FileNotFoundError" in s:
                    raise FileNotFoundError("未知端口名！请检查线缆是否正确连接！")
                else:
                    raise e
        if self._port is not None and not self._port.is_open:   # 如果端口应打开但打开失败
            # 解决了串口断线重连的问题
            try:
                self._port.open()   # 重新尝试打开端口
            except SerialException as e:
                pass

    # 读取温度
    def read(self):
        if self._port is None:
            "端口未打开！请先打开端口！"
            return
        elif not self._port.is_open:
            try:
                self._port.open()
            except SerialException as e:
                return
        msg = b""
        try:
            self._port.read_all()   #!! 清空缓存
            while self._port.in_waiting < 7:    # 等待7个字节
                pass
            msg = self._port.read(7)    # 读取7个字节
            while len(msg) < 7 or msg.find(b"\xff") < 0:    # 如果读取的数据长度小于7或没有找到FF
                msg = self._port.read(7)    # 读取7个字节
            i = msg.find(b"\xff")   # 找到第一个FF的位置，作为起始位置
            msg = msg[i : ] + self._port.read(i)    # 一个完整的数据由FF开头，并有7个字节，根据FF的位置补全数据
            while msg[-1] == 10:    # 如果最后一个字节为0A，即启动时出现的非温差数据
                msg = self._port.read(7)  # 再读取7个字节
            temperature = derive_Delta_T(msg)   # 计算温差
            return temperature  # 返回温差
        except AssertionError as e:
            print(msg)
            raise e
        except AttributeError as e:
            if "NoneType" in s:
                raise ValueError("端口未打开！请先打开端口！")
            else:
                raise e
        except PortNotOpenError:
            raise ValueError("端口未打开！请先打开端口！")
        except SerialException as e:
            s = str(e)
            if "GetOverlappedResult" in s:
                raise BufferError("连接已断开！请检查物理线缆连接！")
            elif "ClearCommError" in s:
                raise IOError("状态错误！请断开重连！")
            else:
                raise e

    # 关闭端口
    def close(self):
        if self._port is not None:
            self._port.close()  # 调用serial的close方法关闭端口
