import serial
from serial import Serial, SerialException
from serial.serialutil import PortNotOpenError
from serial.tools import list_ports
import time

# 有如下几种报错
# 找不到端口 SerialException FileNotFoundError
# 已经打开的端口重复打开 SerialException Port is already open (但重复关闭不会有问题)
# 端口被占用 SerialException PermissionError
# 使用未打开端口 serialutil.PortNotOpenError
# 突然断开连接 SerialException GetOverlappedResult（关机没问题，只有拔线有问题）
# 断开后重新插回 SerialException ClearCommError （好像只有重新连接一种解决方法）

# 启动时会有一段FF 80 0A/0B 0D 0E 0A 0A的数据，注意处理。

COMPORTS = {}


def updateComPorts():
    global COMPORTS
    COMPORTS = {}
    ports = list_ports.comports()
    for port_info in ports:
        COMPORTS[str(port_info.device)] = port_info


def deriveDT(msg):
    dT = msg[3]+(msg[4]+(msg[5]+msg[6]/10)/10)/10
    if msg[2] == 10:
        pass
    elif msg[2] == 11:
        dT = -dT
    elif msg[2] == 1:
        dT += 10
    elif msg[2] == 12:
        dT = -10-dT
    return dT


class EasySerial:
    """
    将serial的Serial打包成在本实验中更易使用的结构
    """

    def __init__(self, name, baud=1200):  # 除非换机器，否则此处1200不要改
        self._name = name
        self._baud = baud
        self._port = None
        self._changed = False

    def setName(self, name):
        self._name=name
        self._changed=True

    def open(self):
        self.close()
        if self._changed or self._port is None:
            try:
                self._port = Serial(self._name, self._baud)
                self._changed=False
            except SerialException as e:
                self._port = None
                s = str(e)
                if "PermissionError" in s:  # 最可能是多开造成的
                    raise PermissionError("端口被占用！请查找可能占用端口的程序！")
                elif "FileNotFoundError" in s:
                    raise FileNotFoundError("未知端口名！请检查线缆是否正确连接！")
                else:
                    raise e
        if self._port is not None and not self._port.is_open:
            self._port.open()

    def read(self):
        if self._port is None or not self._port.is_open:
            "端口未打开！请先打开端口！"
            return
        msg = b''
        try:
            self._port.flush()
            msg = self._port.read(7)
            i = msg.find(b"\xff")
            assert i >= 0
            msg = msg[i:]+self._port.read(i)
            while msg[-1] == 10:
                msg = self.read(7)
            t = time.time()
            temperature = deriveDT(msg)
            return t, temperature
        except AttributeError as e:
            if "NoneType" in s:
                raise ValueError("端口未打开！请先打开端口！")
            else:
                raise e
        except PortNotOpenError as e:
            raise ValueError("端口未打开！请先打开端口！")
        except SerialException as e:
            s = str(e)
            if "GetOverlappedResult" in s:
                raise BufferError("连接已断开！请检查物理线缆连接！")
            elif "ClearCommError" in s:
                raise IOError("状态错误！请断开重连！")
            else:
                raise e

    def close(self):
        if self._port is not None:
            self._port.close()

        
if __name__=="__main__":
    updateComPorts()
    print(COMPORTS)
    #ser=EasySerial("COM3")
    #ser.open("COM1",1200)
    #while True:
    #    print(ser.read(),end=" ")
