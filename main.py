import os
import time
from threading import Thread

from myserial import EasySerial,COMPORTS

class Measure:
    def __init__(self,port_name,internal=0):
        self.port_name=port_name
        self.internal=internal
        self.read_thread:Thread=None
        self.read_active=False
        self.tmp_file_path="latest.tmp"
        self.reset()

    def _read_into_result(self):
        try:
            end_time,dT=self._port.read()
            dt=end_time-self.start_time
            self.result.append((dt,dT,0))
            self.tmp_file.write(f"{dt:.3f},\t\t{dT:.3f},\t\t0\n")
        except BufferError as e:
            "连接已断开！请检查物理线缆连接！"
            self.read_active=False
        except IOError as e:
            "状态错误！请断开重连！"
            self._port.close()
            self._port.open()
    
    def _read_into_result_looping(self):
        while self.read_active:
            self._read_into_result()
            time.sleep(self.internal)

    def reset(self):
        self.result=[] # 测量时间 测量值 注释
        self._port=None
        if self.read_thread is not None:
            self.read_active=False
            while not self.read_thread.is_alive():
                pass
        self.read_active=False
        self.read_thread=None
        self.start_time=0
        self.tmp_file=None
    
    def start(self):
        assert self.tmp_file is None
        assert self.read_thread is None
        self.read_active=True
        self.tmp_file=open(self.tmp_file_path,"w",encoding="utf-8")
        self.start_time=time.time()
        self._port=EasySerial(self.port_name)
        try:
            self._port.open()
        except FileNotFoundError as e:
            "未知端口名！请检查线缆是否正确连接！"
            raise e
        except PermissionError as e:
            "端口被占用！请查找可能占用端口的程序！"
            raise e
        self.read_thread=Thread(target=self._read_into_result_looping)
        self.read_thread.daemon=True
        self.read_thread.start()

    def stop(self):
        assert self.read_thread is not None
        self.read_active=False
        while not self.read_thread.is_alive():
            pass
        self.tmp_file.close()
        self._port.close()

    def saveCSV(self,path):
        with open(path,"w",encoding="utf-8") as f:
            f.write("时间/s,\t温差/K,\t标记\n")
            for dt,dT,comment in self.result:
                f.write(f"{dt:.3f},\t\t{dT:.3f},\t\t{comment}\n")

    
if __name__=="__main__":
    task=Measure("COM22",1)
    task.start()
    time.sleep(5)
    task.stop()
    task.saveCSV("./test.csv")