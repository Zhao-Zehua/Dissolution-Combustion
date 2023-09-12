# Author: 赵泽华
# 内置库
import csv
import os
import re
import sys
import time
# from tkinter import ttk
from tkinter import *
import tkinter.filedialog as filedialog
from tkinter.messagebox import showinfo, showwarning
from tkinter.scrolledtext import ScrolledText
# 第三方库
from func_timeout import FunctionTimedOut
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from PIL import Image as pilImage
from PIL import ImageTk
import ttkbootstrap as ttk
# 自建库
from expserial import EasySerial, getComPorts
import maths as maths
from water_capacity_smooth import water_capacity_smooth
from water_density_smooth import water_density_smooth

def getWaterDensity(temp):
    temperature = "{:.2f}".format(float(temp))
    try:
        return water_density_smooth[temperature]
    except:
        pass

def getWaterCapacity(temp):
    temperature = "{:.2f}".format(float(temp))
    try:
        return water_capacity_smooth[temperature]
    except:
        pass

# 从绝对路径获取文件名和扩展名
def file_name_extension(absolute_path):
    file_name = absolute_path.split("/")[-1]
    extension = file_name.split(".")[-1]
    file_name = file_name.split(".")[0]
    return file_name, extension

# 把字典按给定列名展开
def dct2cols(cols,dct):
    res=[]
    for col in cols:
        res.append(dct[col])
    return res

# 快捷键对应event.state的数值
SHORTCUT_CODE={
    "Shift":0x1,
    "Control":0x4,
    "Command":0x8,
    "Alt":0x20000
}

DATA_CONFIG = {
    "app": None,
    "window": None,
    "screen": None,
    "csv_len": -1,
    "csv":None,
    "mode":None,
    "combustion_mode":None,
    "time_interval":500,
    "plot_max_points":500,
    "port_timeout":0.25,
    "py_path":"."
}

'''
样式
    relief = "raised" or "sunken"
    主框架borderwidth = 5，如self.framex, self.framex_left, self.framex_right_y
    有relief的次框架borderwidth = 1，如self.framex_right_1_left, self.framex_right_1_right
    无relief的次框架borderwidth = 2，如self.framex_left_y包含button或treeview或entry的框架
    对应entry的label padding = 2
'''

SCREEN_CONFIG={
    "borderwidth": 5,
    "relief": "raised"
}

MAIN_FRAME_CONFIG = {
    "borderwidth": 5,
    "relief": "sunken"
}

RAISED_SUBFRAME_CONFIG = {
    "borderwidth": 1,
    "relief": "raised"
}

FLAT_SUBFRAME_CONFIG = {
    "borderwidth": 2
}

ENTRY_LABEL_CONFIG = {
    "padding": 2
}

PLOT_CONFIG={
    "MainScatter":{
        "s":5, 
        "color":"dimgray"
    },
    "MainLine":{
        "linewidth":1, 
        "color":'#1F77B4'
    },
    "Scatter1":{
        "s":15, 
        "color":'darkorange',
    },
    "Line1":{
        "ls":"--", 
        "linewidth":1, 
        "color":'darkorange'
    },
    "Scatter2":{
        "s":15, 
        "color":'limegreen'
    },
    "Line2":{
        "ls":"--", 
        "linewidth":1, 
        "color":'limegreen'
    },
    "Scatter3":{
        "s":15, 
        "color":'violet'
    },
    "Line3":{
        "ls":"--", 
        "linewidth":1, 
        "color":'violet'
    },
    "Heat":{
        "s":15, 
        "color":'red'
    },
    "Reynolds":{
        "ls":"--", 
        "color":'red', 
        "linewidth":1
    },
    "Area":{
        "color":'dimgray', 
        "alpha":0.2
    }
}

DEFAULT_DATA_VALUE={
    "room_temperature(K)":"298.15",
    "water_volume(mL)":"500.0",
    "water_density(g/mL)":"0.9970470",
    "water_capacity(J/gK)":"4.1813",
    "solute_mass(g)":"5.0000",
    "solute_molarmass(g/mol)":"74.551",
    "current(A)":"1.00",
    "benzoic_enthalpy(kJ/mol)":"-3228.2",
    "cotton_heat(J/g)":"-16736",
    "Nickel_heat(J/g)":"-3243",
    "combustible_mass(g)":"1.0000",
    "cotton_mass(g)":"0.0100",
    "Nickel_before_mass(g)":"0.0080",
    "Nickel_after_mass(g)":"0.0030",
    "R1(Omega)":"10.00",
    "R2(Omega)":"10.00",
    "t1":"0.000",
    "t2":"0.000",
}

"""
小组件
"""


class TableWidget(ttk.Frame):
    """
    表格实现
    """
    def __init__(self, master, cols, widths, **kwargs):
        super().__init__(master, **kwargs)
        self.table = ttk.Treeview(self, show="headings", columns=cols)
        for col, width in zip(cols, widths):
            self.table.column(col, width=width, anchor="center")
            self.table.heading(col, text=col)
        self.table.place(relx=0, rely=0, relwidth=0.95, relheight=1)
        scollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.table.yview)
        scollbar.place(relx=0.95, rely=0, relwidth=0.05, relheight=1)
    def append(self,args):
        self.table.insert("", "end", values = args)
        self.table.yview_moveto(1)
    def clear(self):
        self.table.delete(*self.table.get_children())


class TextWidget(ttk.Frame):
    """
    信息文本框
    """
    def __init__(self,master,**kwargs):
        super().__init__(master,**kwargs)
        self.textbox=ScrolledText(self)
        self.textbox.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.textbox.config(state="disabled")
    def append(self,s):
        self.textbox.config(state="normal")
        self.textbox.insert("end",s)
        self.textbox.config(state="disabled")
    def clear(self):
        self.textbox.config(state="normal")
        self.textbox.delete(1.0,"end")
        self.textbox.config(state="disabled")
    def see(self,pos):
        self.textbox.see(pos)


class PlotWidget(ttk.Frame):
    def __init__(self,master,xlabel,ylabel,**kwargs):
        super().__init__(master,**kwargs)
        self.xlabel=xlabel
        self.ylabel=ylabel
        self.P = Figure(dpi = DATA_CONFIG["window"].winfo_fpixels('1i'))# * scale_factor)
        self.P.subplots_adjust(left = 0.1, right = 0.9, top = 0.9, bottom = 0.15)
        self.f = self.P.add_subplot(111)
        self.f.set_xlabel(self.xlabel)
        self.f.set_ylabel(self.ylabel)
        # 设置刻度向内
        self.f.tick_params(direction = "in")
        # 设置四周框线
        self.f.spines["top"].set_visible(True)
        self.f.spines["right"].set_visible(True)
        self.f.spines["bottom"].set_visible(True)
        self.f.spines["left"].set_visible(True)
        # 设置框线宽度
        self.f.spines["top"].set_linewidth(0.5)
        self.f.spines["right"].set_linewidth(0.5)
        self.f.spines["bottom"].set_linewidth(0.5)
        self.f.spines["left"].set_linewidth(0.5)
        # 设置英文字体为Arial
        self.f.xaxis.label.set_fontname("Arial")
        self.f.yaxis.label.set_fontname("Arial")
        # 初始化tkinter中的matplotlib画布
        self.canvas = FigureCanvasTkAgg(self.P, DATA_CONFIG["window"])
        self.canvas.draw()
        self.canvas.draw_idle()
        PIL_image = pilImage.frombytes('RGB', self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        self.bind("<Configure>", self.resize_image)
        self.canvas_plot=ttk.Label(self,image = tk_image)
        self.canvas_plot.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
    def clear(self):
        # 清空图像
        self.f.clear()
        self.f.set_xlabel(self.xlabel)
        self.f.set_ylabel(self.ylabel)
    def plot(self,x,y,**kwargs):
        self.f.plot(x,y,**kwargs)
    def scatter(self,x,y,**kwargs):
        self.f.scatter(x,y,**kwargs)
    def legend(self):
        self.f.legend()
    def show(self):
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        self.canvas_plot.configure(image = tk_image)
        self.canvas_plot.image = tk_image
    def fill_between(self,x,y1,y2,**kwargs):
        self.f.fill_between(x,y1,y2,**kwargs)
    def resize_image(self, event):
        # 根据frame大小重绘图片
        frame_width, frame_height = event.width, event.height
        new_width, new_height = frame_width / self.P.dpi, frame_height / self.P.dpi
        self.P.set_size_inches(new_width, new_height, forward = True)
        self.canvas.draw()
        PIL_image = pilImage.frombytes('RGB', self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        self.canvas_plot.config(image = tk_image)
        self.canvas_plot.image = tk_image
    def save_fig(self,name):
        self.P.set_size_inches(DATA_CONFIG["width_height_inches"])
        self.P.savefig(fname = name, dpi = DATA_CONFIG["dpi"])

class StringEntriesWidget(ttk.Frame):
    """
    参数集合
    """
    class CachedStringEntryWidget(ttk.Frame):
        def __init__(self, master, name, default="", text=None, **kwargs):
            def bind_return():
                #if "temperature" in name:print("bind",self.name,self.entry)
                self.entry.bind("<Return>", lambda event:self.check_memory())

            def unbind_return():
                #if "temperature" in name:print("unbind",self.name,self.entry)
                self.entry.unbind("<Return>")
                self.check_memory()

            super().__init__(master, **kwargs)
            self.name = name
            self.text = name if text is None else text
            self.label = ttk.Label(self, text=self.text, **ENTRY_LABEL_CONFIG)
            self.label.place(relx=0, rely=0, relwidth=0.5, relheight=1)
            default="0" if default is None else default
            self.cached = StringVar()
            self.cached.set(default)
            self.var = StringVar()
            self.var.set(default)
            self.entry = ttk.Entry(self, textvariable=self.var)
            self.entry.bind("<FocusIn>", lambda *args: bind_return())
            self.entry.bind("<FocusOut>", lambda *args: unbind_return())
            self.entry.place(relx=0.5,rely=0,relwidth=0.5,relheight=1)

        def set_state(self, state):
            self.entry.config(state=state)

        def set_var(self, value):
            self.var.set(value=value)
            self.cached.set(value=value)
            #self.check_memory()
        # 检查输入参数是否合法

        def check_memory(self):
            #print("return",self.name)
            # 判断是否为数字
            def is_number(s):
                try:
                    float(s)
                    return True
                except ValueError:
                    return False
            # 检查输入是否为数字，若不是则恢复上一次的输入

            def _check_memory(memory: StringVar, realtime: StringVar):
                # 只保留数字、小数点和四则运算符号，支持加减乘除和幂运算
                realtime.set(re.sub(r"[^\d+*/().-]+", "", realtime.get()))
                # 若输入与原先不同
                if realtime.get() != memory.get():
                    # 若输入不是数字，则判断是否为合法算式
                    if not is_number(realtime.get()):
                        try:
                            realtime.set(str(eval(realtime.get())))
                            if float(realtime.get()) == float(memory.get()):
                                realtime.set(memory.get())
                            else:
                                memory.set(realtime.get())
                                self.master.change()
                        except:  # 此时输入的不是数字或者合法算式
                            realtime.set(memory.get())
                    # 若输入是数字，则更新记忆
                    else:
                        memory.set(realtime.get())
                        if self.name not in ("dissolution_heat(kJ)","constant(J/K)","combustion_heat(J/g)"):
                            DATA_CONFIG["screen"].change_entry()
            # 检查输入框
            memory = self.cached
            realtime = self.var
            _check_memory(memory, realtime)

    def __init__(self, master,
                 names: "list[str]",
                 defaults: "dict"={},
                 dependences=[],
                 texts: dict={},
                 cols: int = 2,
                 **kwargs
                 ):
        super().__init__(master, **kwargs)
        self.entries = [self.CachedStringEntryWidget(
            self, name,default=defaults.get(name,None),text=texts.get(name,None)) for name in names]
        self.entries_table = {entry.name: entry for entry in self.entries}

        def trace_factory(affected, func, args):
            def trace_template(*_):
                res = func(*[self.entries_table[arg].cached.get()
                           for arg in args])
                self.entries_table[affected].var.set(res)
                self.entries_table[affected].cached.set(res)
            return trace_template
        for traced, affected, func, args in dependences:
            self.entries_table[traced].cached.trace_add(
                "write", trace_factory(affected, func, args))
        rows = len(self.entries)//cols
        if len(self.entries) % cols != 0:
            rows += 1
        for i, entry in enumerate(self.entries):
            entry.place(relx=(i % cols)/cols, rely=(i//cols) /
                        rows, relwidth=1/cols, relheight=1/rows)
    
    def clear(self):
        for entry in self.entries:
            entry.set_var("")

    def dump(self):
        return {entry.name: entry.cached.get() for entry in self.entries}
    
    def set_states(self,state,names):
        for name in names:
            self.entries_table[name].set_state(state)

    def set_all_states(self,state):
        for entry in self.entries:
            entry.set_state(state)
    
    def set_value(self,key,value):
        if key in self.entries_table:
            self.entries_table[key].set_var(value)


class SpinEntriesWidget(ttk.Frame):
    """
    起终点集合
    """

    PAIRS=0

    class SpinEntry(ttk.Frame):
        def __init__(self, master, name, default="0", **kwargs):
            def bind_return():
                self.bind("<Return>", self.check_memory())

            def unbind_return():
                self.unbind("<Return>")
                self.check_memory()
            super().__init__(master, **kwargs)
            self.name = name
            self.label = ttk.Label(self, text=name)
            self.label.place(relx=0, rely=0, relwidth=0.5, relheight=1)
            self.cached = StringVar()
            self.cached.set(default)
            self.var = StringVar()
            self.var.set(default)
            self.entry = ttk.Spinbox(
                self, textvariable=self.var, from_=0, to=0, increment=1, command=self.check_memory)
            self.entry.bind("<FocusIn>", lambda *args: bind_return())
            self.entry.bind("<FocusOut>", lambda *args: unbind_return())
            self.entry.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

        def check_memory(self):
            if not self.var.get().isdigit():
                self.var.set(self.cached.get())
            elif hasattr(DATA_CONFIG["screen"], "spinEntries") and not DATA_CONFIG["screen"].spinEntries.check_memory():
                self.var.set(self.cached.get())
            else:
                self.cached.set(self.var.get())
                DATA_CONFIG["screen"].change_entry()
                DATA_CONFIG["screen"].calc_regression()
                DATA_CONFIG['screen'].plot_regression()
                DATA_CONFIG['screen'].plot_frame.show()
        
        def set_state(self,state):
            self.entry.config(state=state)

        def set_var(self,val):
            self.var.set(val)
            self.cached.set(val)

        def set_from_to(self,from_,to):
            self.entry.config(from_=from_,to=to)

    def __init__(self, master, pairs, **kwargs):
        super().__init__(master, **kwargs)
        self.entries = []
        self.entries_table={}
        cols = 2
        rows = pairs
        for i in range(rows):
            row_frame=ttk.Frame(self)
            row_frame.place(relx=0, rely=i*0.25, relwidth=1, relheight=0.25)
            self.entries.append(self.SpinEntry(row_frame, f"Start {i+1}"))
            self.entries[-1].place(relx=0,rely=0,relwidth=0.5,relheight=1)
            self.entries.append(self.SpinEntry(row_frame, f"End {i+1}"))
            self.entries[-1].place(relx=0.5,rely=0,relwidth=0.5,relheight=1)
        for entry in self.entries:
            self.entries_table[entry.name]=entry
        buttons = ttk.Frame(self)
        buttons.place(relx=0, rely=pairs*0.25, relwidth=1, relheight=0.25)
        button_left = ttk.Frame(buttons, **FLAT_SUBFRAME_CONFIG)
        button_left.place(relx=0, rely=0, relwidth=0.5, relheight=1)
        button_right = ttk.Frame(buttons, **FLAT_SUBFRAME_CONFIG)
        button_right.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)
        self.button_remake = ttk.Button(
            button_left, text="重置(Ctrl-Z)", command=self.remake_file)
        self.button_integrate = ttk.Button(
            button_right, text="计算(Ctrl-D)", command=self.calc)
        self.button_remake.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.button_integrate.place(relx=0, rely=0, relwidth=1, relheight=1)

    def gbl_buttons(self):
        DATA_CONFIG["screen"].button_remake=self.button_remake
        DATA_CONFIG["screen"].button_integrate=self.button_integrate

    def check_memory(self):
        if int(self.entries[0].var.get()) < 0:return False
        if "csv_len" in DATA_CONFIG:
            if DATA_CONFIG["csv_len"]!=-1:
                if DATA_CONFIG["csv_len"] <= int(self.entries[-1].var.get()):
                    return False
        for i in range(1, len(self.entries)):
            if int(self.entries[i-1].var.get()) >= int(self.entries[i].var.get()):
                return False
        return True

    def dump(self):
        return {entry.name: int(entry.cached.get()) for entry in self.entries}
    
    def set_var(self,key,value):
        self.entries_table[key].set_var(value)

    def set_states(self,state):
        for entry in self.entries:
            entry.set_state(state)
    
    def set_from_to(self,name,from_,to):
        self.entries_table[name].set_from_to(from_,to)

    def remake_file(self):
        # 更新输入框的值
        self.start_end_points_list = maths.find_start_end_point(DATA_CONFIG["csv"], DATA_CONFIG["mode"].get(), DATA_CONFIG['time_lower_limit'], DATA_CONFIG['time_upper_limit'], DATA_CONFIG['std_limit'])
        if self.start_end_points_list is None:return 
        self.start_end_points_dict = {}
        DATA_CONFIG["screen"].start_end_points_dict=self.start_end_points_dict
        for i,point in enumerate(self.start_end_points_list):
            self.start_end_points_dict[f"{'End' if i&1 else 'Start'} {(i>>1)+1}"]=point
        for i in range(self.PAIRS+1):
            if f"End {i}" not in self.start_end_points_dict:
                if i==0:
                    self.start_end_points_dict[f"End {i}"]=-1
                elif i==self.PAIRS:
                    self.start_end_points_dict[f"End {i}"]=DATA_CONFIG["csv_len"]-1
                else:
                    self.start_end_points_dict[f"End {i}"]=int(DATA_CONFIG["csv_len"]*(i*2-1)/(self.PAIRS*2-1))
            if f"Start {i+1}" not in self.start_end_points_dict:
                if i==self.PAIRS:
                    self.start_end_points_dict[f"Start {i+1}"]=DATA_CONFIG["csv_len"]
                else:
                    self.start_end_points_dict[f"Start {i+1}"]=int(DATA_CONFIG["csv_len"]*(i*2)/(self.PAIRS*2-1))
        for i in range(1,self.PAIRS+1):
            self.set_var(f"Start {i}",str(self.start_end_points_dict[f"Start {i}"]))
            self.set_var(f"End {i}",str(self.start_end_points_dict[f"End {i}"]))
        self.set_states("normal")
        for i in range(1,self.PAIRS+1):
            self.set_from_to(f"Start {i}",self.start_end_points_dict[f"End {i-1}"]+1,self.start_end_points_dict[f"End {i}"]-1)
            self.set_from_to(f"End {i}",self.start_end_points_dict[f"Start {i}"]+1,self.start_end_points_dict[f"Start {i+1}"]-1)
        # 线性回归
        DATA_CONFIG["screen"].change_entry()
        DATA_CONFIG["screen"].calc_regression()
        DATA_CONFIG["screen"].plot_regression()
        DATA_CONFIG["screen"].plot_frame.show()
        # 解锁除file、remake之外的所有button
        self.button_remake.config(state = "normal")
        self.button_integrate.config(state = "normal")

    def calc(self):
        """
        积分与其他值计算
        """
        #DATA_CONFIG["screen"].calc_regression()
        DATA_CONFIG["screen"].calc_integration()
        DATA_CONFIG["screen"].plot_regression()
        DATA_CONFIG["screen"].plot_integration()
        DATA_CONFIG["screen"].plot_frame.show()
        DATA_CONFIG["screen"].calc_result()

class DissolutionSpinEntriesWidget(SpinEntriesWidget):
    PAIRS=3
    def __init__(self, master, **kwargs):
        super().__init__(master, self.PAIRS, **kwargs)

class CombustionSpinEntriesWidget(SpinEntriesWidget):
    PAIRS=2
    def __init__(self, master, **kwargs):
        super().__init__(master, self.PAIRS, **kwargs)
        mode_frame=ttk.Frame(self)
        mode_frame.place(relx=0,rely=0.75,relwidth=1,relheight=0.25)
        DATA_CONFIG["combustion_mode"]=StringVar()
        if sys.platform.startswith('win'):
            self.radiobutton_constant=ttk.Radiobutton(mode_frame, text = "常数(Alt-E)", value = "constant", variable = DATA_CONFIG["combustion_mode"], command = self.select_mode)
            self.radiobutton_constant.place(relx = 0.25, rely = 0.5, anchor = "center")
            self.radiobutton_combustible = ttk.Radiobutton(mode_frame, text = "样品(Alt-S)", value = "combustible", variable = DATA_CONFIG["combustion_mode"], command = self.select_mode)
            self.radiobutton_combustible.place(relx = 0.75, rely = 0.5, anchor = "center")
        elif sys.platform.startswith('darwin'):
            self.radiobutton_constant=ttk.Radiobutton(mode_frame, text = "常数(Cmd-E)", value = "constant", variable = DATA_CONFIG["combustion_mode"], command = self.select_mode)
            self.radiobutton_constant.place(relx = 0.25, rely = 0.5, anchor = "center")
            self.radiobutton_combustible = ttk.Radiobutton(mode_frame, text = "样品(Cmd-S)", value = "combustible", variable = DATA_CONFIG["combustion_mode"], command = self.select_mode)
            self.radiobutton_combustible.place(relx = 0.75, rely = 0.5, anchor = "center")
        DATA_CONFIG["combustion_mode"].set("constant")
    
    def select_mode(self):
        DATA_CONFIG["screen"].set_entry_state()

    def gbl_buttons(self):
        super().gbl_buttons()
        DATA_CONFIG["screen"].radiobutton_constant=self.radiobutton_constant
        DATA_CONFIG["screen"].radiobutton_combustible=self.radiobutton_combustible
        

# 四个主界面

class Screen(ttk.Frame):
    COLS=[]
    SHORTCUTS=[]

    def __init__(self):
        super().__init__(DATA_CONFIG["window"],**SCREEN_CONFIG)
        DATA_CONFIG["screen"]=self
        DATA_CONFIG["csv_len"]=-1
        DATA_CONFIG["csv"]=None
        self.buttons()
        self.place(relx=0,rely=0,relwidth=1,relheight=1)
        main_paned=ttk.PanedWindow(self,orient="horizontal")
        main_paned.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.left_frame=ttk.Frame(main_paned, **MAIN_FRAME_CONFIG)
        main_paned.add(self.left_frame,weight=30)
        right_frame=ttk.Frame(main_paned)
        main_paned.add(right_frame,weight=70)
        self.right_paned=ttk.PanedWindow(right_frame,orient="vertical")
        self.right_paned.place(relx=0,rely=0,relwidth=1,relheight=1)
    def addTextBox(self,height):
        self.text_frame=TextWidget(self.right_paned,**MAIN_FRAME_CONFIG)
        self.right_paned.add(self.text_frame,weight=height)
        if hasattr(self,"INFORM_TEXT"):
            self.text_frame.append(self.INFORM_TEXT)
    def addPlotBox(self,height,xlabel,ylabel):
        self.plot_frame=PlotWidget(self.right_paned,xlabel,ylabel,**MAIN_FRAME_CONFIG)
        self.right_paned.add(self.plot_frame,weight=height)
    def addModeButton(self,order):
        frame=ttk.Frame(self.left_frame,**FLAT_SUBFRAME_CONFIG)
        frame.place(relx=0,rely=0,relwidth=1,relheight=0.05)
        DATA_CONFIG["mode"]=StringVar()
        self.button_mode=ttk.OptionMenu(frame,DATA_CONFIG["mode"],*order,command=self.change_mode)
        self.button_mode.place(relx=0,rely=0,relwidth=1,relheight=1)
    def addTableBox(self,cols,widths,startY):
        self.table_frame=TableWidget(self.left_frame,cols,widths,**FLAT_SUBFRAME_CONFIG)
        self.table_frame.place(relx=0,rely=startY,relwidth=1,relheight=0.95-startY)
    def addInfoLabel(self):
        tmp=ttk.Frame(self.left_frame)
        tmp.place(relx=0,rely=0.95,relwidth=1,relheight=0.05)
        self.info_label= ttk.Label(tmp, text = "作者：赵泽华 安孝彦", anchor = "center")
        self.info_label.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
    
    # 所有button
    def buttons(self):
        self.button_get_comport = None
        self.radiobutton_dissolution = None
        self.radiobutton_combustion = None
        self.button_data_start = None
        self.button_heat_start = None
        self.button_heat_stop = None
        self.button_data_stop = None
        self.button_save = None
        self.button_open = None
        self.button_remake = None
        self.button_integrate = None
        self.radiobutton_constant = None
        self.radiobutton_combustible = None

    def button_shortcut(self,event):
        modifier=""
        if event.state & SHORTCUT_CODE["Shift"]:
            modifier += "Shift-"
        if event.state & SHORTCUT_CODE["Control"]:
            modifier += "Control-"
        if sys.platform.startswith('win'):
            if event.state & SHORTCUT_CODE["Alt"]:
                modifier += "Alt-"
        elif sys.platform.startswith('darwin'):
            if event.state & SHORTCUT_CODE["Command"]:
                modifier += "Command-"
        keyboard = f"<{modifier}{event.keysym.lower()}>"
        shortcuts = {\
            "<Shift-Control-r>": self.button_get_comport, \
            "<Alt-d>": self.radiobutton_dissolution, \
            "<Alt-c>": self.radiobutton_combustion, \
            "<Command-d>": self.radiobutton_dissolution, \
            "<Command-c>": self.radiobutton_combustion, \
            "<Control-q>": self.button_data_start, \
            "<Control-w>": self.button_heat_start, \
            "<Control-e>": self.button_heat_stop, \
            "<Control-r>": self.button_data_stop, \
            "<Control-s>": self.button_save, \
            "<Control-f>": self.button_open, \
            "<Control-z>": self.button_remake, \
            "<Control-d>": self.button_integrate, \
            "<Alt-e>": self.radiobutton_constant, \
            "<Alt-s>": self.radiobutton_combustible, \
            "<Command-e>": self.radiobutton_constant, \
            "<Command-s>": self.radiobutton_combustible \
            }
        if keyboard in shortcuts:
            button = shortcuts[keyboard]
            if str(button["state"]) == "normal":
                button.invoke()

    def change_mode(self,*args):
        DATA_CONFIG['app'].change_mode()

    def open_file(self):
        '''
        数据文件的格式如下：
            前若干行为变量行，每行包括变量名和数值2列；此后1行为标题行；随后若干行为时间-温差数值。
            1. 溶解热模式
                变量依次为temperature(K), water_volume(mL), solute_molarmass(g/mol), solute_mass(g), R1(Ω), R2(Ω), t1(s), t2(s), current(A)
            2. 燃烧热模式
                变量依次为temperature(K), water_volume(mL), cotton_mass(g), combustible_mass(g), Nickel_before_mass(g), Nickel_after_mass(g)
        '''
        absolute_path = filedialog.askopenfilename(filetypes = [("CSV", ".csv"), ("TXT", ".txt"), ("ALL", "*.*")])
        if absolute_path == "":
            return
        self.absolute_path = absolute_path
        self.file_name, self.extension = file_name_extension(self.absolute_path)
        csv_skiprows = 1
        # 给entry上锁，同时清空相关信息
        self.spinEntries.set_states("disabled")
        self.strEntries.set_all_states("disabled")
        self.text_frame.clear()
        self.table_frame.clear()
        self.plot_frame.clear()
        # 重置并读取参数
        csv_all = np.loadtxt(self.absolute_path, delimiter = ",", dtype = str)
        row_count=9 if DATA_CONFIG["mode"].get()=="溶解热" else 6
        try:
            # 尝试从输入文件读取参数
            parameters = csv_all[0 : row_count, 1].astype(float)
            parameters_dict={k:v.astype(float) for k,v in csv_all[0:row_count]}
            csv_skiprows += len(parameters)
        except:
            pass
        # 锁定除file之外的所有button
        self.button_save.config(state = "disabled")
        self.button_remake.config(state = "disabled")
        self.button_integrate.config(state = "disabled")
        # 读取文件，加载变量
        try:
            DATA_CONFIG["csv"] = csv_all[csv_skiprows:].astype(float)
        except:
            self.text_frame.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 读取{self.absolute_path}失败，请检查文件格式\n")
            showwarning(title = "警告", message = f"读取{self.absolute_path}失败，请检查文件格式")
            return
        # 将csv中的数据按时间排序
        self.csv_time = DATA_CONFIG["csv"][:, 0]
        self.csv_time = np.argsort(self.csv_time)
        DATA_CONFIG["csv"] = DATA_CONFIG["csv"][self.csv_time]
        DATA_CONFIG["csv_len"] = len(DATA_CONFIG["csv"])
        # 将csv中的数据加载到表格中
        for i in range(DATA_CONFIG["csv_len"]):
            self.table_frame.append((i, f"{DATA_CONFIG['csv'][i][0]:.3f}", f"{DATA_CONFIG['csv'][i][1]:.3f}"))
        # 更新文件名
        self.info_label.config(text = self.file_name)
        # 计算平滑曲线
        self.smooth = maths.B_Spline(DATA_CONFIG["csv"][:, 0], DATA_CONFIG["csv"][:, 1], DATA_CONFIG["dx"])
        self.x_smooth = np.arange(DATA_CONFIG["csv"][:, 0].min(), DATA_CONFIG["csv"][:, 0].max(), DATA_CONFIG["dx"])
        self.y_smooth = self.smooth(self.x_smooth)
        # 更新输入框范围
        self.remake_file()
        # 参数赋值，并检查导入的参数是否合法
        try:
            for k in parameters_dict:
                self.strEntries.set_value(k,str(parameters_dict[k]))
        except:
            pass
        if DATA_CONFIG["mode"].get()=="溶解热":
            self.strEntries.set_value("dissolution_heat(kJ)","")
        elif DATA_CONFIG["mode"].get()=="燃烧热":
            if DATA_CONFIG["combustion_mode"].get() == "constant":
                self.strEntries.set_value("constant(J/K)","")
            elif DATA_CONFIG["combustion_mode"].get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                self.strEntries.set_value("combustion_heat(J/g)","")
    
    def save_file(self):
        result_file_name="dissolution.csv" if DATA_CONFIG["mode"].get()=="溶解热" else "combustion.csv"
        result_path = self.absolute_path.replace(self.file_name + '.' + self.extension, result_file_name)
        # 如果与当前打开的csv文件同目录的文件夹下没有dissolution.csv文件
        if not os.path.exists(result_path):
            with open(result_path, mode = "w", encoding = "UTF-8", newline = "") as f:
                writer = csv.writer(f)
                writer.writerow(self.COLS)
        try:
            with open(result_path, mode = "a", encoding = "UTF-8", newline = "") as f:
                writer = csv.writer(f)
                writer.writerow(dct2cols(self.COLS,self.parameters))
        except PermissionError:
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 保存失败！请关闭{result_file_name}文件后再次尝试保存\n")
            self.text_frame.see("end")
            showwarning(title = "警告", message = f"保存失败！请关闭{result_file_name}文件后再次尝试保存")
            return
        self.plot_frame.save_fig(self.absolute_path.replace(self.extension, "png"))
        self.button_save.config(state = "disabled")
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {result_file_name}文件保存成功\n")
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {self.file_name}.png保存成功\n")
        self.text_frame.see("end")
        showinfo(title = "提示", message = f"保存成功！\n{self.file_name}.png保存至{self.absolute_path.replace(self.file_name + '.' + self.extension, '')}\n计算数据保存至同目录下的{result_file_name}文件")

    def remake_file(self):
        self.spinEntries.remake_file()
        self.strEntries.set_all_states("normal")
        if DATA_CONFIG["mode"].get()=="溶解热":
            self.strEntries.set_states("readonly",["dissolution_heat(kJ)"])
        elif DATA_CONFIG["mode"].get()=="燃烧热":
            self.radiobutton_constant.config(state = "normal")
            self.radiobutton_combustible.config(state = "normal")
            if DATA_CONFIG["combustion_mode"].get() == "constant":
                self.strEntries.set_states("readonly",["constant(J/K)"])
                self.strEntries.set_states("disabled",["combustion_heat(J/g)"])
            elif DATA_CONFIG["combustion_mode"].get() == "combustible":
                self.strEntries.set_states("readonly",["combustion_heat(J/g)"])
    
    def change_entry(self):
        if DATA_CONFIG["mode"].get()=="溶解热":
            self.strEntries.set_value("dissolution_heat(kJ)","")
        elif DATA_CONFIG["mode"].get()=="燃烧热":
            if DATA_CONFIG["combustion_mode"].get() == "constant":
                self.strEntries.set_value("constant(J/K)","")
            elif DATA_CONFIG["combustion_mode"].get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                self.strEntries.set_value("combustion_heat(J/g)","")

    def calc_regression(self):
        # 判断csv是否已读入
        #if str(type(self.csv)) == "<class 'NoneType'>":
        #    return
        # 线性回归
        self.start_end_points_dict=self.spinEntries.dump()
        self.k1, self.b1, self.stddev_k1, self.stddev_b1, self.r_square1 = maths.linear_regression(DATA_CONFIG["csv"], self.start_end_points_dict["Start 1"], self.start_end_points_dict["End 1"])
        self.k2, self.b2, self.stddev_k2, self.stddev_b2, self.r_square2 = maths.linear_regression(DATA_CONFIG["csv"], self.start_end_points_dict["Start 2"], self.start_end_points_dict["End 2"])
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.k3, self.b3, self.stddev_k3, self.stddev_b3, self.r_square3 = maths.linear_regression(DATA_CONFIG["csv"], self.start_end_points_dict["Start 3"], self.start_end_points_dict["End 3"])
        # 更新text_result
        self.text_frame.clear()
        self.text_frame.append(f"Linear Fit 1: Delta_T/K = ({self.k1:.6} ± {self.stddev_k1:.3}) t/s + ({self.b1:.6} ± {self.stddev_b1:.3}), r-square = {self.r_square1:.9f}\n")
        self.text_frame.append(f"Linear Fit 2: Delta_T/K = ({self.k2:.6} ± {self.stddev_k2:.3}) t/s + ({self.b2:.6} ± {self.stddev_b2:.3}), r-square = {self.r_square2:.9f}\n")
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.text_frame.append(f"Linear Fit 3: Delta_T/K = ({self.k3:.6} ± {self.stddev_k3:.3}) t/s + ({self.b3:.6} ± {self.stddev_b3:.3}), r-square = {self.r_square3:.9f}\n")

    def plot_regression(self):
        # 回归直线绘图
        # 清空图像
        self.plot_frame.clear()
        # 绘制起止点和散点图
        self.plot_frame.scatter(DATA_CONFIG["csv"][:, 0], DATA_CONFIG["csv"][:, 1], label = "$\Delta T$ - $t$ data", **PLOT_CONFIG["MainScatter"])
        self.plot_frame.scatter(DATA_CONFIG["csv"][self.start_end_points_dict["Start 1"], 0], DATA_CONFIG["csv"][self.start_end_points_dict["Start 1"], 1], label = "linear fit 1 endpoints", **PLOT_CONFIG["Scatter1"])
        self.plot_frame.scatter(DATA_CONFIG["csv"][self.start_end_points_dict["End 1"], 0], DATA_CONFIG["csv"][self.start_end_points_dict["End 1"], 1], **PLOT_CONFIG["Scatter1"])
        self.plot_frame.scatter(DATA_CONFIG["csv"][self.start_end_points_dict["Start 2"], 0], DATA_CONFIG["csv"][self.start_end_points_dict["Start 2"], 1], label = "linear fit 2 endpoints", **PLOT_CONFIG["Scatter2"])
        self.plot_frame.scatter(DATA_CONFIG["csv"][self.start_end_points_dict["End 2"], 0], DATA_CONFIG["csv"][self.start_end_points_dict["End 2"], 1], **PLOT_CONFIG["Scatter2"])
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.plot_frame.scatter(DATA_CONFIG["csv"][self.start_end_points_dict["Start 3"], 0], DATA_CONFIG["csv"][self.start_end_points_dict["Start 3"], 1], label = "linear fit 3 endpoints", **PLOT_CONFIG["Scatter3"])
            self.plot_frame.scatter(DATA_CONFIG["csv"][self.start_end_points_dict["End 3"], 0], DATA_CONFIG["csv"][self.start_end_points_dict["End 3"], 1], **PLOT_CONFIG["Scatter3"])
            try:
                t1_temperature = self.smooth(float(self.t1.get()))
                t2_temperature = self.smooth(float(self.t2.get()))
                self.f.scatter(float(self.t1.get()), float(t1_temperature), label = "heating endpoints", **PLOT_CONFIG["Heat"])
                self.f.scatter(float(self.t2.get()), float(t2_temperature), **PLOT_CONFIG["Heat"])
            except:
                pass
        # 绘制平滑曲线
        self.plot_frame.plot(self.x_smooth, self.y_smooth, label = "$\Delta T$ - $t$ curve", **PLOT_CONFIG["MainLine"])
        # 绘制线性回归
        self.y1 = self.k1 * self.x_smooth + self.b1
        self.y2 = self.k2 * self.x_smooth + self.b2
        self.plot_frame.plot(self.x_smooth, self.y1, label = "linear fit 1", **PLOT_CONFIG["Line1"])
        self.plot_frame.plot(self.x_smooth, self.y2, label = "linear fit 2", **PLOT_CONFIG["Line2"])
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.y3 = self.k3 * self.x_smooth + self.b3
            self.plot_frame.plot(self.x_smooth, self.y3, label = "linear fit 3", **PLOT_CONFIG["Line3"])
        # 绘制图例
        self.plot_frame.legend()
    
    def calc_integration(self):
        # 计算校正点
        self.x1, S1_left, S1_right = maths.Reynolds(DATA_CONFIG['csv'], self.start_end_points_dict["Start 1"], self.start_end_points_dict["End 1"], self.start_end_points_dict["Start 2"], self.start_end_points_dict["End 2"], DATA_CONFIG['dx'])
        self.T1_left = self.k1 * self.x1 + self.b1
        self.T1_right = self.k2 * self.x1 + self.b2
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.x2, S2_left, S2_right = maths.Reynolds(DATA_CONFIG['csv'], self.start_end_points_dict["Start 2"], self.start_end_points_dict["End 2"], self.start_end_points_dict["Start 3"], self.start_end_points_dict["End 3"], DATA_CONFIG['dx'])
            self.T2_left = self.k2 * self.x2 + self.b2
            self.T2_right = self.k3 * self.x2 + self.b3
        # 更新text_frame
        self.text_frame.clear()
        self.text_frame.append(f"Linear Fit 1: Delta_T/K = ({self.k1:.6} ± {self.stddev_k1:.3}) t/s + ({self.b1:.6} ± {self.stddev_b1:.3}), r-square = {self.r_square1:.9f}\n")
        self.text_frame.append(f"Linear Fit 2: Delta_T/K = ({self.k2:.6} ± {self.stddev_k2:.3}) t/s + ({self.b2:.6} ± {self.stddev_b2:.3}), r-square = {self.r_square2:.9f}\n")
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.text_frame.append(f"Linear Fit 3: Delta_T/K = ({self.k3:.6} ± {self.stddev_k3:.3}) t/s + ({self.b3:.6} ± {self.stddev_b3:.3}), r-square = {self.r_square3:.9f}\n")
        if DATA_CONFIG["mode"].get() == "燃烧热":
            self.text_frame.append(f"x0 = {self.x1:.2f}\n")
            self.text_frame.append(f"S_left = {S1_left:.2f}  S_right = {S1_right:.2f}\n")
            self.text_frame.append(f"T_left = {self.T1_left:.3f} K  T_right = {self.T1_right:.3f} K\n")
        elif DATA_CONFIG["mode"].get() == "溶解热":
            self.text_frame.append(f"x1 = {self.x1:.2f}, x2 = {self.x2:.2f}\n")
            self.text_frame.append(f"S1_left = {S1_left:.2f}  S1_right = {S1_right:.2f}  S2_left = {S2_left:.2f}  S2_right = {S2_right:.2f}\n")
            self.text_frame.append(f"T1_left = {self.T1_left:.3f} K  T1_right = {self.T1_right:.3f} K  T2_left = {self.T2_left:.3f} K  T2_right = {self.T2_right:.3f} K\n")
        # 设置save为可用
        self.button_save.config(state = "normal")
    
    def plot_integration(self):
        # 绘制积分区域
        # 绘制分界线
        T1_small, T1_big = [self.T1_right, self.T1_left] if self.T1_left > self.T1_right else [self.T1_left, self.T1_right]
        Delta_T1 = T1_big - T1_small
        T1_y = np.arange(T1_small - Delta_T1 * 0.1, T1_big + Delta_T1 * 0.1, DATA_CONFIG['dx'])
        T1_x = np.full(len(T1_y), self.x1)
        if DATA_CONFIG["mode"].get() == "燃烧热":
            self.plot_frame.plot(T1_x, T1_y, label = "Reynolds auxiliary line", **PLOT_CONFIG["Reynolds"])
        elif DATA_CONFIG["mode"].get() == "溶解热":
            T2_small, T2_big = [self.T2_right, self.T2_left] if self.T2_left > self.T2_right else [self.T2_left, self.T2_right]
            Delta_T2 = T2_big - T2_small
            T2_y = np.arange(T2_small - Delta_T2 * 0.1, T2_big + Delta_T2 * 0.1, DATA_CONFIG['dx'])
            T2_x = np.full(len(T2_y), self.x2)
            self.plot_frame.plot(T1_x, T1_y, **PLOT_CONFIG["Reynolds"])
            self.plot_frame.plot(T2_x, T2_y, label = "Reynolds auxiliary line", **PLOT_CONFIG["Reynolds"])
        # 绘制积分面积
        T1_x_area_left = np.arange(DATA_CONFIG["csv"][self.start_end_points_dict["End 1"], 0], self.x1, DATA_CONFIG['dx'])
        T1_x_area_right = np.arange(self.x1, DATA_CONFIG["csv"][self.start_end_points_dict["Start 2"], 0], DATA_CONFIG['dx'])
        T1_y_area_left_linear = self.k1 * T1_x_area_left + self.b1
        T1_y_area_right_linear = self.k2 * T1_x_area_right + self.b2
        T1_y_area_left_smooth = self.smooth(T1_x_area_left)
        T1_y_area_right_smooth = self.smooth(T1_x_area_right)
        self.plot_frame.fill_between(T1_x_area_left, T1_y_area_left_linear, T1_y_area_left_smooth, **PLOT_CONFIG["Area"])
        self.plot_frame.fill_between(T1_x_area_right, T1_y_area_right_linear, T1_y_area_right_smooth, **PLOT_CONFIG["Area"])
        if DATA_CONFIG["mode"].get() == "溶解热":
            T2_x_area_left = np.arange(DATA_CONFIG["csv"][self.start_end_points_dict["End 2"], 0], self.x2, DATA_CONFIG['dx'])
            T2_x_area_right = np.arange(self.x2, DATA_CONFIG["csv"][self.start_end_points_dict["Start 3"], 0], DATA_CONFIG['dx'])
            T2_y_area_left_linear = self.k2 * T2_x_area_left + self.b2
            T2_y_area_right_linear = self.k3 * T2_x_area_right + self.b3
            T2_y_area_left_smooth = self.smooth(T2_x_area_left)
            T2_y_area_right_smooth = self.smooth(T2_x_area_right)
            self.plot_frame.fill_between(T2_x_area_left, T2_y_area_left_linear, T2_y_area_left_smooth, **PLOT_CONFIG["Area"])
            self.plot_frame.fill_between(T2_x_area_right, T2_y_area_right_linear, T2_y_area_right_smooth, **PLOT_CONFIG["Area"])
    
    def dump_data(self):
        self.parameters={}
        self.parameters.update(self.spinEntries.dump())
        self.parameters.update(self.strEntries.dump())
        if DATA_CONFIG["mode"].get() == "溶解热":
            self.parameters["filename"]=self.file_name
            self.parameters["T1_left"]=self.T1_left
            self.parameters["T1_right"]=self.T1_right
            self.parameters["T2_left"]=self.T2_left
            self.parameters["T2_right"]=self.T2_right
        elif DATA_CONFIG["mode"].get()=="燃烧热":
            self.parameters["filename"]=f"{self.file_name}.{self.extension}"
            self.parameters["T_left(K)"]=self.T1_left
            self.parameters["T_right(K)"]=self.T1_right

    def calc_result(self):
        if DATA_CONFIG["mode"].get() == "溶解热":
            # 加载参数
            self.dump_data()
            maths.calculate_dissolution(self.parameters)
            # 更新计算结果
            self.strEntries.set_value("dissolution_heat(kJ)",self.parameters["dissolution_heat(kJ)"])
        elif DATA_CONFIG["mode"].get() == "燃烧热":
            # 加载参数
            self.dump_data()
            maths.calculate_combustion(self.parameters,DATA_CONFIG["combustion_mode"].get())
            # 更新计算结果
            if DATA_CONFIG["combustion_mode"].get() == "constant":
                self.strEntries.set_value("constant(J/K)",self.parameters["constant(J/K)"])
            elif DATA_CONFIG["combustion_mode"].get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                self.strEntries.set_value("combustion_heat(J/g)",self.parameters["combustion_heat(J/g)"])
    
    def initShortCut(self):
        for shortcut in self.SHORTCUTS:
            DATA_CONFIG["window"].bind(shortcut,self.button_shortcut)

    def destroy(self):
        for shortcut in self.SHORTCUTS:
            DATA_CONFIG["window"].unbind(shortcut)
        super().destroy()

class Screen1_Data(Screen):
    """
    数据采集界面
    """
    INFORM_TEXT=""\
    "数据记录模式使用说明\n"\
    "0. 点击左上角按钮切换模式\n"\
    "1. 选择正确的记录模式。\n"\
    "2. 点击刷新串口，程序将自动识别有数据输入的串口，并开始读取数据。如有多个有数据输入的串口，请自行选择正确的一个。\n"\
    "3. 点击开始记录，开始记录数据。\n"\
    "4. 如选择溶解热记录模式，在开始加热和结束加热时点击相应按钮。\n"\
    "5. 点击停止记录，停止记录数据。\n"\
    "6. 在文本框中输入实验参数后，保存数据。\n"\
    "7. 如数据丢失，可从与main.py同目录的tempfile.tmp中找到最近一次的记录数据。注意：溶解热的此数据需要处理后再使用。\n"\
    "8. 为保证csv文档的易读性，建议使用纯英文字符命名csv文件。\n\n"
    entry_state={
        "dissolution":[
            "room_temperature(K)",
            "solute_molarmass(g/mol)",
            "solute_mass(g)",
            "R1(Omega)",
            "R2(Omega)",
            "current(A)",
            "water_volume(mL)"
        ],
        "combustion":[
            "room_temperature(K)",
            "water_volume(mL)",
            "cotton_mass(g)",
            "combustible_mass(g)",
            "Nickel_before_mass(g)",
            "Nickel_after_mass(g)"
        ]
    }

    measure_mode=None

    all_comports=[]
    comport_name=None
    comport=None
    start_time=0
    end_time=0
    temp_Delta_t = []
    temp_Delta_T = []
    temp_file_name="tempfile.tmp"
    temp_file=None
    during_measuring=False
    csv_path=""
    csv_data=[]
    t1="0.000"
    t2="0.000"

    SHORTCUTS=[
        "<Shift-Control-r>",
        "<Shift-Control-R>",
        "<Alt-d>",
        "<Alt-D>",
        "<Alt-c>",
        "<Alt-C>",
        "<Command-d>",
        "<Command-D>",
        "<Command-c>",
        "<Command-C>",
        "<Control-q>",
        "<Control-Q>",
        "<Control-r>",
        "<Control-R>",
        "<Control-w>",
        "<Control-W>",
        "<Control-e>",
        "<Control-E>",
        "<Control-s>",
        "<Control-S>"
    ]
    
    comport_reading = False

    def __init__(self):
        super().__init__()
        self.addModeButton(["数据记录","溶解热","燃烧热","溶解热拟合"])
        self.arrangeLeft()
        self.addTableBox(["time(s)","Delta_T(K)"],[50,50],0.35)
        self.addInfoLabel()
        self.addEntries()
        self.addTextBox(15)
        self.addPlotBox(65,"$t$ (s)","$\Delta T$ (K)")
        self.init_states()
        self.initShortCut()
        self.read_comport()
    def arrangeLeft(self):
        tmp=ttk.Frame(self.left_frame,**FLAT_SUBFRAME_CONFIG)
        tmp.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.comport_name=StringVar()
        self.comports_menu=ttk.OptionMenu(tmp, self.comport_name,"请刷新串口",*self.all_comports, command = self.change_port)
        self.comports_menu.place(relx=0,rely=0,relwidth=1,relheight=1)
        tmp=ttk.Frame(self.left_frame,**FLAT_SUBFRAME_CONFIG)
        tmp.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_get_comport=ttk.Button(tmp, text="刷新串口(Ctrl-Shift-R)", command = self.get_port)
        self.button_get_comport.place(relx=0,rely=0,relwidth=1,relheight=1)
        tmp=ttk.Frame(self.left_frame)
        tmp.place(relx = 0, rely = 0.15, relwidth = 1, relheight = 0.05)
        self.measure_mode=StringVar()
        if sys.platform.startswith('win'):
            self.radiobutton_dissolution=ttk.Radiobutton(tmp, text = "溶解热(Alt-D)", value = "dissolution", variable = self.measure_mode, command = self.change_measure_mode)
            self.radiobutton_dissolution.place(relx = 0.25, rely = 0.5, anchor = "center")
            self.radiobutton_combustion=ttk.Radiobutton(tmp, text = "燃烧热(Alt-C)", value = "combustion", variable = self.measure_mode, command = self.change_measure_mode)
            self.radiobutton_combustion.place(relx = 0.75, rely = 0.5, anchor = "center")
        elif sys.platform.startswith('darwin'):
            self.radiobutton_dissolution=ttk.Radiobutton(tmp, text = "溶解热(Cmd-D)", value = "dissolution", variable = self.measure_mode, command = self.change_measure_mode)
            self.radiobutton_dissolution.place(relx = 0.25, rely = 0.5, anchor = "center")
            self.radiobutton_combustion=ttk.Radiobutton(tmp, text = "燃烧热(Cmd-C)", value = "combustion", variable = self.measure_mode, command = self.change_measure_mode)
            self.radiobutton_combustion.place(relx = 0.75, rely = 0.5, anchor = "center")
        self.measure_mode.set("dissolution")
        tmp=ttk.Frame(self.left_frame,**FLAT_SUBFRAME_CONFIG)
        tmp.place(relx=0,rely=0.2,relwidth=1,relheight=0.05)
        self.button_data_start=ttk.Button(tmp,text="开始记录(Ctrl-Q)",command=self.data_start)
        self.button_data_start.place(relx=0,rely=0,relwidth=0.5,relheight=1)
        self.button_data_stop=ttk.Button(tmp,text="停止记录(Ctrl-R)",command=self.data_end)
        self.button_data_stop.place(relx=0.5,rely=0,relwidth=0.5,relheight=1)
        tmp=ttk.Frame(self.left_frame,**FLAT_SUBFRAME_CONFIG)
        tmp.place(relx=0,rely=0.25,relwidth=1,relheight=0.05)
        self.button_heat_start=ttk.Button(tmp,text="开始加热(Ctrl-W)",command=self.heat_start)
        self.button_heat_start.place(relx=0,rely=0,relwidth=0.5,relheight=1)
        self.button_heat_stop=ttk.Button(tmp,text="停止加热(Ctrl-E)",command=self.heat_end)
        self.button_heat_stop.place(relx=0.5,rely=0,relwidth=0.5,relheight=1)
        tmp=ttk.Frame(self.left_frame,**FLAT_SUBFRAME_CONFIG)
        tmp.place(relx=0,rely=0.3,relwidth=1,relheight=0.05)
        self.button_save=ttk.Button(tmp,text="保存数据(Ctrl-S)",command=self.data_save)
        self.button_save.place(relx=0,rely=0,relwidth=1,relheight=1)

    def addEntries(self):
        self.entries_frame=StringEntriesWidget(
            self.right_paned,
            [
                "room_temperature(K)","water_volume(mL)",
                "solute_molarmass(g/mol)","cotton_mass(g)",
                "solute_mass(g)","combustible_mass(g)",
                "R1(Omega)","Nickel_before_mass(g)",
                "R2(Omega)","Nickel_after_mass(g)",
                "current(A)"
            ],
            defaults=DEFAULT_DATA_VALUE,
            texts={
                "room_temperature(K)":"室温(K)",
                "solute_molarmass(g/mol)":"溶质式量(g/mol)",
                "solute_mass(g)":"溶质质量(g)",
                "R1(Omega)":"加热前电阻(Ω)",
                "R2(Omega)":"加热后电阻(Ω)",
                "current(A)":"电流(A)",
                "water_volume(mL)":"水体积(mL)",
                "cotton_mass(g)":"棉线(g)",
                "combustible_mass(g)":"苯甲酸+棉线(g)",
                "Nickel_before_mass(g)":"镍丝(g)",
                "Nickel_after_mass(g)":"燃烧后镍丝(g)",
            },
            **MAIN_FRAME_CONFIG
        )
        self.right_paned.add(self.entries_frame,weight=20)
        self.set_entry_state()
        self.t1=DEFAULT_DATA_VALUE["t1"]
        self.t2=DEFAULT_DATA_VALUE["t2"]
    
    def init_states(self):
        self.button_data_start.config(state = "disabled")
        self.button_data_stop.config(state = "disabled")
        self.button_heat_start.config(state = "disabled")
        self.button_heat_stop.config(state = "disabled")
        self.button_save.config(state="disabled")
        self.set_entry_state()
    
    def set_entry_state(self):
        self.entries_frame.set_all_states("disabled")
        self.entries_frame.set_states("normal",self.entry_state[self.measure_mode.get()])

    def change_mode(self,*args):
        if self.comport is not None:
            self.comport.close()
        super().change_mode()

    def get_port(self):
        if str(self.button_get_comport["state"]) != "normal":
            return
        # 禁用组件
        self.button_get_comport.config(state="disabled")
        self.button_data_start.config(state = "disabled")
        self.button_data_stop.config(state = "disabled")
        self.button_heat_start.config(state = "disabled")
        self.button_heat_stop.config(state = "disabled")
        self.button_save.config(state="disabled")
        # 提示信息
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 正在检测串口信息，请耐心等待！\n")
        if self.comport:
            self.comport.close()
        # 获取串口信息
        self.all_comports = getComPorts(select = True, timeout =DATA_CONFIG["port_timeout"])
        # 重置开始时间、数据记录、绘图
        self.start_time = time.time()
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.plot_frame.clear()
        self.table_frame.clear()
        # 提示信息
        if self.all_comports:
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口检测完成，" + f"可用串口为{' '.join(self.all_comports)}\n")
        else:
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口检测完成，无可用串口\n")
        self.text_frame.see("end")
        # 如果有可用串口
        if self.all_comports:
            # 如果当前选择的串口不在可用串口中
            if self.comport_name.get() not in self.all_comports:
                # 选择第一个可用串口并打开
                self.comport_name.set(self.all_comports[0])
                #self.change_comport(self.comport_name.get())
                # 如果还没有开始读数(读数在打开程序后只需要启动一次)
                #if not self.comport_reading:
                #    self.read_comport()
            # 如果当前选择的串口在可用串口中
            #else:
                #self.button_data_start.config(state = "normal")
            self.change_port(self.comport_name.get())
        # 如果没有可用串口
        else:
            self.comport_name.set("请刷新串口")
            self.comport.close() if self.comport else None
            self.comport = None
        # 更新按钮状态
        self.comports_menu.set_menu(self.comport_name.get(), *self.all_comports)
        self.button_get_comport.config(state = "normal")
    
    def change_port(self,event):
        self.comport.close() if self.comport else None
        self.comport = None
        self.comport_name.set(event)
        self.comports_menu.set_menu(self.comport_name.get(), *self.all_comports)
        self.comport = EasySerial(event)
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口已切换为{event}\n")
        self.text_frame.see("end")
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.plot_frame.clear()
        self.table_frame.clear()
        try:
            # 打开与py文件同目录的临时文件，用逗号分隔的形式存储数据，方便后续处理
            # exe文件不能用os.path.abspath获取当前目录
            self.temp_file = open(os.path.join(DATA_CONFIG["py_path"],self.temp_file_name), "w", encoding = "UTF-8")
            self.temp_file.write("time(s),Delta_T(K)\n")
            self.temp_file.flush()
            self.start_time = time.time()
            self.comport.open()
            self.button_data_start.config(state = "normal")
        except:
            self.comport.close()
            self.button_data_start.config(state = "disabled")
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口打开失败，请尝试其他串口，或检查USB线缆连接状态。\n")
            self.text_frame.see("end")

    def change_measure_mode(self):
        self.set_entry_state()
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 当前选择{'燃烧热' if self.measure_mode.get() == 'combustion' else '溶解热'}模式\n")
        self.text_frame.see("end")

    def read_comport(self):
        try:
            # 读取串口数据
            Delta_T = self.comport.read()
            self.end_time = time.time()
            Delta_t = self.end_time - self.start_time
            # 将数据写入临时文件和csv文件
            try:
                self.temp_file.write(f"{Delta_t:.3f},{Delta_T:.3f}\n")
                self.temp_file.flush()
                if self.during_measuring == 1:
                    self.csv_data.append([f"{Delta_t:.3f}", f"{Delta_T:.3f}"])
                self.table_frame.append((f"{Delta_t:.3f}", f"{Delta_T:.3f}"))
                self.temp_Delta_t.append(Delta_t)
                if len(self.temp_Delta_t) >= DATA_CONFIG["plot_max_points"]:
                    self.temp_Delta_t = self.temp_Delta_t[-DATA_CONFIG["plot_max_points"]:]
                self.temp_Delta_T.append(Delta_T)
                if len(self.temp_Delta_T) >= DATA_CONFIG["plot_max_points"]:
                    self.temp_Delta_T = self.temp_Delta_T[-DATA_CONFIG["plot_max_points"]:]
            except TypeError:
                self.csv_data.append([f"{Delta_t:.3f}", f"{Delta_T:.3f}"])
                self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口读取数据失败，请检查串口连接状态。\n")
                self.text_frame.see("end")
            self.plot_frame.clear()
            self.plot_frame.plot(self.temp_Delta_t, self.temp_Delta_T, color = '#1F77B4')
            self.plot_frame.show()

        except BufferError:
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口读取数据失败，请检查串口连接状态。\n")
            self.text_frame.see("end")
        except IOError:
            self.comport.close()
            self.comport.open()
        except AttributeError as e:
            if self.comport is not None:
                raise e
        except FunctionTimedOut:
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口读取数据失败，请检查串口连接状态。\n")
            self.text_frame.see("end")
        # self.during_measuring = True
        self.after(DATA_CONFIG["time_interval"], self.read_comport)

    def data_start(self):
        DATA_CONFIG["window"].protocol("WM_DELETE_WINDOW", lambda: None)
        self.temp_file.close()
        self.temp_file = open(os.path.join(DATA_CONFIG["py_path"],self.temp_file_name), "w", encoding = "UTF-8")
        self.temp_file.write("time(s),Delta_T(K)\n")
        self.temp_file.flush()
        self.start_time = time.time()
        if self.measure_mode.get() == "combustion":
            self.csv_data = [["room_temperature(K)"], ["water_volume(mL)"], ["cotton_mass(g)"], ["combustible_mass(g)"], ["Nickel_before_mass(g)"], ["Nickel_after_mass(g)"], ["time(s)", "Delta_T(K)"]]
        elif self.measure_mode.get() == "dissolution":
            self.csv_data = [["room_temperature(K)"], ["water_volume(mL)"], ["solute_molarmass(g/mol)"], ["solute_mass(g)"], ["R1(Omega)"], ["R2(Omega)"], ["t1(s)"], ["t2(s)"], ["current(A)"], ["time(s)", "Delta_T(K)"]]
        self.during_measuring=True
        self.button_mode.configure(state = "disabled")
        self.button_data_start.config(state = "disabled")
        self.comports_menu.configure(state = "disabled")
        self.button_get_comport.config(state = "disabled")
        self.radiobutton_combustion.config(state = "disabled")
        self.radiobutton_dissolution.config(state = "disabled")
        if self.measure_mode.get() == "dissolution":
            self.button_heat_start.config(state = "normal")
        elif self.measure_mode.get() == "combustion":
            self.button_data_stop.config(state = "normal")
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.plot_frame.clear()
        self.table_frame.clear()
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 开始记录\n")
        self.text_frame.see("end")

    def data_end(self):
        self.temp_file.write("stop recording\n")
        self.temp_file.flush()
        self.csv_state = False
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 停止记录\n")
        self.text_frame.see("end")
        self.button_data_stop.config(state="disabled")
        self.button_save.config(state = "normal")

    def heat_start(self):
        self.t1=f"{(time.time() - self.start_time):.3f}"
        self.temp_file.write(f"start heating at {self.t1} s\n")
        self.temp_file.flush()
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 开始加热\n")
        self.text_frame.see("end")
        self.button_heat_start.config(state = "disabled")
        self.button_heat_stop.config(state = "normal")

    def heat_end(self):
        self.t2=f"{(time.time() - self.start_time):.3f}"
        self.temp_file.write(f"stop heating at {self.t2} s\n")
        self.temp_file.flush()
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 停止加热\n")
        self.text_frame.see("end")
        self.button_heat_stop.config(state = "disabled")
        self.button_data_stop.config(state = "normal")

    def data_save(self):
        self.csv_path = filedialog.asksaveasfilename(title = "保存数据", initialfile = f"{time.strftime('%Y%m%d%H%M%S', time.localtime())}{self.measure_mode.get()}data.csv", filetypes = [("CSV", ".csv")])
        if self.csv_path == "":
            # self.save_data()    # 递归调用，直到选择保存路径，但其间不能修改，所以注释掉
            return
        entries_data=self.entries_frame.dump()
        entries_data["t1(s)"]=self.t1
        entries_data["t2(s)"]=self.t2
        for key_val in self.csv_data:
            if len(key_val)==1:
                key_val.append(entries_data[key_val[0]])
        with open(self.csv_path, "w", encoding = "UTF-8", newline = "") as f:
            csv.writer(f).writerows(self.csv_data)
        showinfo(title = "提示", message = f"数据成功保存至{self.csv_path}")
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 数据保存成功\n")
        self.text_frame.see("end")
        self.temp_file.close()
        self.temp_file = open(os.path.join(DATA_CONFIG["py_path"],self.temp_file_name), "w", encoding = "UTF-8")
        self.temp_file.write("time(s),Delta_T(K)\n")
        self.temp_file.flush()
        self.start_time = time.time()
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.plot_frame.clear()
        self.table_frame.clear()
        self.button_save.config(state = "disabled")
        self.button_mode.configure(state = "normal")
        self.button_data_start.config(state = "normal")
        self.comports_menu.configure(state = "normal")
        self.button_get_comport.config(state = "normal")
        self.radiobutton_combustion.config(state = "normal")
        self.radiobutton_dissolution.config(state = "normal")
        DATA_CONFIG["window"].protocol("WM_DELETE_WINDOW", DATA_CONFIG["window"].destroy)

class Screen2_Dissolution(Screen):
    """
    溶解热计算界面
    """
    INFORM_TEXT=""\
    "溶解热模式使用说明\n"\
    "0. 点击左上角按钮切换模式\n"\
    "1. 点击文件(.csv)导入文件，建议文件名不包含中文字符。\n"\
    "2. csv文件格式：共2列；前9行为参数名和参数数值；第10行为温度曲线的标题，第11行起为温度曲线数据，第1列为升序的time(s)，第2列为Delta_T(K)；同一行数据间以半角逗号分隔。\n"\
    "3. 调整Start 1 < End 1 < Start 2 < End 2 < Start 3 < End 3至合适位置。\n"\
    "4. 点击计算进行积分和溶解热计算。\n"\
    "5. 点击保存(.png)保存结果，并输出一个dissolution.csv文档，其中储存了本次计算的参数和结果。dissolution.csv可以直接用于积分溶解热的拟合计算。\n"\
    "6. 输入框可以自动识别并提取其中的合法数字。\n"\
    "7. 常数，如温度、水的体积等会自动记忆。\n"\
    "8. 内置了CRC Handbook of Chemistry and Physics 95th Edition中水的密度和热容常数，根据输入温度自动取值。\n"\
    "9. 如导入文件后没有响应，检查文件的编码格式是否为UTF-8，检查文件内有无特殊字符。\n\n"
    
    PAIRS=3
    COLS=["filename", "Start 1", "End 1", "Start 2", "End 2", "Start 3", "End 3", "T1_left", "T1_right", "T2_left", "T2_right", \
                            "room_temperature(K)", "water_volume(mL)", "water_density(g/mL)", "water_capacity(J/gK)", \
                            "solute_mass(g)", "solute_molarmass(g/mol)", "R1(Omega)", "R2(Omega)", "t1(s)", "t2(s)", "current(A)", "dissolution_heat(kJ)"]
    
    SHORTCUTS=[
        "<Control-f>",
        "<Control-F>",
        "<Control-s>",
        "<Control-S>",
        "<Control-z>",
        "<Control-Z>",
        "<Control-d>",
        "<Control-D>"
    ]

    def __init__(self):
        super().__init__()
        self.addModeButton(["溶解热","数据记录","燃烧热","溶解热拟合"])
        self.arrangeLeft()
        self.addTableBox(["index","time(s)","Delta_T(K)"],[25,50,50],0.15)
        self.addInfoLabel()
        self.addEntries()
        self.addTextBox(15)
        self.addPlotBox(65,"$t$ (s)","$\Delta T$ (K)")
        self.initShortCut()
        self.plot_frame.show()
    def arrangeLeft(self):
        tmp = ttk.Frame(self.left_frame, **FLAT_SUBFRAME_CONFIG)
        tmp.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_open = ttk.Button(tmp, text = "文件(Ctrl-F)", command = self.open_file)
        self.button_open.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        tmp = ttk.Frame(self.left_frame, borderwidth = 2)
        tmp.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_save = ttk.Button(tmp, text = "保存(Ctrl-S)", command = self.save_file, state = "disabled")
        self.button_save.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
    def addEntries(self):
        entries_frame=ttk.Frame(self.right_paned,**MAIN_FRAME_CONFIG)
        self.right_paned.add(entries_frame,weight=20)
        entries_frame_paned=ttk.PanedWindow(entries_frame,orient="horizontal")
        entries_frame_paned.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.spinEntries=DissolutionSpinEntriesWidget(entries_frame_paned,**FLAT_SUBFRAME_CONFIG)
        entries_frame_paned.add(self.spinEntries, weight = 30)
        self.strEntries=StringEntriesWidget(
            entries_frame_paned,
            [
                "room_temperature(K)","water_volume(mL)",
                "water_density(g/mL)","water_capacity(J/gK)",
                "solute_mass(g)","solute_molarmass(g/mol)",
                "R1(Omega)","R2(Omega)",
                "t1(s)","t2(s)",
                "current(A)","dissolution_heat(kJ)"
            ],
            DEFAULT_DATA_VALUE,
            [
                ("room_temperature(K)","water_density(g/mL)",lambda temp:getWaterDensity(temp),["room_temperature(K)"]),
                ("room_temperature(K)","water_capacity(J/gK)",lambda temp:getWaterCapacity(temp),["room_temperature(K)"]),
            ],
            {
                "room_temperature(K)":"温度(K)","water_volume(mL)":"水体积(mL)",
                "water_density(g/mL)":"水密度(g/mL)","water_capacity(J/gK)":"水热容(J/gK)",
                "solute_mass(g)":"溶质质量(g)","solute_molarmass(g/mol)":"溶质式量",
                "R1(Omega)":"加热前电阻(Ω)","R2(Omega)":"加热后电阻(Ω)",
                "t1(s)":"加热开始时间(s)","t2(s)":"加热结束时间(s)",
                "current(A)":"电流(A)","dissolution_heat(kJ)":"溶解热(kJ)" 
            }
        )
        entries_frame_paned.add(self.strEntries,weight=70)
        self.spinEntries.set_states("disabled")
        self.strEntries.set_all_states("disabled")
        self.spinEntries.gbl_buttons()
        self.button_remake.config(state="disabled")
        self.button_integrate.config(state="disabled")


class Screen3_Combustion(Screen):
    """
    燃烧热计算界面
    """
    INFORM_TEXT=""\
    "燃烧热模式使用说明\n"\
    "0. 点击左上角按钮切换模式\n"\
    "1. 点击文件(.csv)导入文件，建议文件名不包含中文字符。\n"\
    "2. csv文件格式：共2列；前6行为参数名和参数数值；第7行为温度曲线的标题，第8行起为温度曲线数据，第1列为升序的time(s)，第2列为Delta_T(K)；同一行数据间以半角逗号分隔。\n"\
    "3. 调整Start 1 < End 1 < Start 2 < End 2至合适位置。\n"\
    "4. 选择正确的计算模式。常数、样品模式分别用来计算量热计常数和样品燃烧热。\n"\
    "5. 点击计算进行积分和燃烧热计算。\n"\
    "6. 点击保存(.png)保存图片，并输出一个combustion.csv文档，其中储存了本次计算的参数和结果。\n"\
    "7. 输入框可以自动识别并提取其中的合法数字。\n"\
    "8. 常数，如温度、水的体积等会自动记忆。\n"\
    "9. 内置了CRC Handbook of Chemistry and Physics 95th Edition中水的密度和热容常数，根据输入温度自动取值。\n"\
    "10. 如导入文件后没有响应，检查文件的编码格式是否为UTF-8，检查文件内有无特殊字符。\n\n"
    
    COLS=["filename", "Start 1", "End 1", "Start 2", "End 2", "T_left(K)", "T_right(K)", \
                                "room_temperature(K)", "water_volume(mL)", "water_density(g/mL)", "water_capacity(J/gK)", \
                                "combustible_mass(g)", "cotton_mass(g)", "Nickel_before_mass(g)", "Nickel_after_mass(g)", \
                                "benzoic_enthalpy(kJ/mol)", "cotton_heat(J/g)", "Nickel_heat(J/g)", "constant(J/K)", "combustion_heat(J/g)"]
    
    SHORTCUTS=[
        "<Control-f>",
        "<Control-F>",
        "<Control-s>",
        "<Control-S>",
        "<Control-z>",
        "<Control-Z>",
        "<Control-d>",
        "<Control-D>",
        "<Alt-E>",
        "<Alt-e>",
        "<Alt-S>",
        "<Alt-s>",
        "<Command-E>",
        "<Command-e>",
        "<Command-S>",
        "<Command-s>"
    ]

    def __init__(self):
        super().__init__()
        self.addModeButton(["燃烧热","数据记录","溶解热","溶解热拟合"])
        self.arrangeLeft()
        self.addTableBox(["index","time(s)","Delta_T(K)"],[25,50,50],0.15)
        self.addInfoLabel()
        self.addEntries()
        self.addTextBox(15)
        self.addPlotBox(65,"$t$ (s)","$\Delta T$ (K)")
        self.initShortCut()
    def arrangeLeft(self):
        tmp = ttk.Frame(self.left_frame, **FLAT_SUBFRAME_CONFIG)
        tmp.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_open = ttk.Button(tmp, text = "文件(Ctrl-F)", command = self.open_file)
        self.button_open.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        tmp = ttk.Frame(self.left_frame, borderwidth = 2)
        tmp.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_save = ttk.Button(tmp, text = "保存(Ctrl-S)", command = self.save_file, state = "disabled")
        self.button_save.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
    def addEntries(self):
        entries_frame=ttk.Frame(self.right_paned,**MAIN_FRAME_CONFIG)
        self.right_paned.add(entries_frame,weight=20)
        entries_frame_paned=ttk.PanedWindow(entries_frame,orient="horizontal")
        entries_frame_paned.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.spinEntries=CombustionSpinEntriesWidget(entries_frame_paned,**FLAT_SUBFRAME_CONFIG)
        entries_frame_paned.add(self.spinEntries, weight = 30)
        self.strEntries=StringEntriesWidget(
            entries_frame_paned,
            [
                "room_temperature(K)","water_volume(mL)",
                "water_density(g/mL)","water_capacity(J/gK)",
                "cotton_mass(g)","combustible_mass(g)",
                "Nickel_before_mass(g)","Nickel_after_mass(g)",
                "benzoic_enthalpy(kJ/mol)","cotton_heat(J/g)",
                "Nickel_heat(J/g)","constant(J/K)",
                "combustion_heat(J/g)"
            ],
            DEFAULT_DATA_VALUE,
            [("room_temperature(K)","water_density(g/mL)",lambda temp:getWaterDensity(temp),["room_temperature(K)"]),
                ("room_temperature(K)","water_capacity(J/gK)",lambda temp:getWaterCapacity(temp),["room_temperature(K)"])],
            {
                "room_temperature(K)":"温度(K)","water_volume(mL)":"水体积(mL)",
                "water_density(g/mL)":"水密度(g/mL)","water_capacity(J/gK)":"水热容(J/gK)",
                "cotton_mass(g)":"棉线(g)","combustible_mass(g)":"苯甲酸+棉线(g)",
                "Nickel_before_mass(g)":"镍丝(g)","Nickel_after_mass(g)":"燃烧后镍丝(g)",
                "benzoic_enthalpy(kJ/mol)":"苯甲酸燃烧焓(kJ/mol)","cotton_heat(J/g)":"棉线燃烧热(J/g)",
                "Nickel_heat(J/g)":"镍丝燃烧热(J/g)","constant(J/K)":"量热计常数(J/K)",
                "combustion_heat(J/g)":"恒容燃烧热(J/g)"
            }
        )
        entries_frame_paned.add(self.strEntries,weight=70)
        self.spinEntries.set_states("disabled")
        self.strEntries.set_all_states("disabled")
        self.spinEntries.gbl_buttons()
        self.button_remake.config(state="disabled")
        self.button_integrate.config(state="disabled")
        self.radiobutton_combustible.config(state="disabled")
        self.radiobutton_constant.config(state="disabled")
    def set_entry_state(self):
        if DATA_CONFIG["combustion_mode"].get() == "constant":
            # 清空燃烧热计算结果，禁止编辑量热计常数和燃烧热
            self.strEntries.set_value("combustion_heat(J/g)","")
            self.strEntries.set_states("readonly",["constant(J/K)"])
            self.strEntries.set_states("disabled",["combustion_heat(J/g)"])
            # 更新label
            self.strEntries.entries_table["combustible_mass(g)"].label.config(text = "苯甲酸+棉线(g)")
            # 更新提示
            self.text_frame.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 当前选择量热计常数模式\n")
            self.text_frame.see("end")
        # 两种测量模式
        # 若修改为三种，需要修改self.Frame3_Combustion, self.combustion_mode, maths.calculate_combustion        
        elif DATA_CONFIG["combustion_mode"].get() == "combustible":
            # 清空燃烧热计算结果，禁止编辑燃烧热，允许编辑量热计常数
            self.strEntries.set_value("combustion_heat(J/g)","")
            self.strEntries.set_states("readonly",["combustion_heat(J/g)"])
            # 更新label
            self.strEntries.entries_table["combustible_mass(g)"].label.config(text = "样品+棉线(g)")
            # 更新提示
            self.text_frame.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 当前选择样品燃烧热模式\n")
            self.text_frame.see("end")

class Screen4_Fit(Screen):
    INFORM_TEXT=""\
    "溶解热拟合模式使用说明\n"\
    "0. 点击左上角按钮切换模式\n"\
    "1. 点击文件(.csv)导入文件，默认文件名为dissolution.csv。\n"\
    "2. 导入的csv文件由本程序的溶解热模式自动生成。文件第一行为标题行，此后每一行必须按照实际实验顺序排列，且只能出现一次。输入文件不合法将无法计算，如格式有误请自行编辑。\n"\
    "3. 拟合方程为Qs = Qs0 × a × n / (1 + a × n)。\n"\
    "4. 点击保存(.png)保存图片，并输出一个数据文档，其中储存了本次计算结果。\n\n"

    SHORTCUTS=[
        "<Control-f>",
        "<Control-F>",
        "<Control-s>",
        "<Control-S>"
    ]

    def __init__(self):
        super().__init__()
        self.addModeButton(["溶解热拟合","数据记录","溶解热","燃烧热"])
        self.addTableBox(["index","n0","Qs(kJ/mol)"],[25,50,50],0.15)
        self.addInfoLabel()
        self.addTextBox(35)
        self.addPlotBox(65,"$n_0$","$Q_s$ (kJ/mol)")
        self.arrangeLeft()
        self.initShortCut()
    
    def arrangeLeft(self):
        tmp = ttk.Frame(self.left_frame, **FLAT_SUBFRAME_CONFIG)
        tmp.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_open = ttk.Button(tmp, text = "文件(Ctrl-F)", command = self.open_file)
        self.button_open.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        tmp = ttk.Frame(self.left_frame, borderwidth = 2)
        tmp.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_save = ttk.Button(tmp, text = "保存(Ctrl-S)", command = self.save_file, state = "disabled")
        self.button_save.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

    def open_file(self):
        absolute_path = filedialog.askopenfilename(filetypes = [("CSV", ".csv"), ("TXT", ".txt"), ("ALL", "*.*")])
        if absolute_path == "":
            return
        self.absolute_path = absolute_path
        self.button_save.config(state = "disabled")
        # 更新text_result
        self.text_frame.clear()
        self.text_frame.append(self.INFORM_TEXT)
        self.file_name, self.extension = file_name_extension(self.absolute_path)
        with open(self.absolute_path,"r",encoding="utf-8") as file_obj:
            reader=csv.reader(file_obj)
            titles=[]
            parameters={}
            for row in reader:
                if not parameters:
                    titles=row.copy()
                    for title in row:
                        parameters[title]=[]
                else:
                    for title,val in zip(titles,row):
                        parameters[title].append(val)
        dissolution_csv = [list(map(float,row)) for row in zip(*[parameters[title] for title in ["water_volume(mL)", "water_density(g/mL)", "solute_mass(g)", "solute_molarmass(g/mol)", "dissolution_heat(kJ)"]])]
        len_csv = len(dissolution_csv)
        dissolution_parameters = []
        for i in range(len_csv):
            dissolution_parameters.append([dissolution_csv[i][0], dissolution_csv[i][1], dissolution_csv[i][2], dissolution_csv[i][3], dissolution_csv[i][4]])
        self.Qs, self.n, self.Qs0, self.a, self.stddev_Qs0, self.stddev_a, self.r_square = maths.dissolution_heat_regression(dissolution_parameters)
        self.dissolution_test_data = maths.dissolution_heat_test(self.Qs0, self.a)
        # 更新table_frame
        self.table_frame.clear()
        for i in range(len_csv):
            self.table_frame.append((i, f"{self.n[i]:.4g}", f"{self.Qs[i]:.2f}"))
        # 更新绘图
        self.plot_frame.clear()
        self.plot_frame.scatter(self.n, self.Qs, s = 50, marker = '+', color = 'dimgray', label = "$Q_s$-$n_0$ data points")
        # 非线性拟合方程
        n_plot = np.arange(0, max(self.n) * 1.2, DATA_CONFIG["dx"])
        Qs_plot = (self.Qs0 * self.a * n_plot) / (1 + self.a * n_plot)
        '''
        # 线性拟合方程
        n_arange = max(n) - min(n)
        n_plot = np.arange(min(n) - n_arange * 0.1, max(n) + n_arange * 0.1, n_arange / 1000)
        Qs_plot = n_plot / (Qs0 * a) + 1 / Qs0
        '''
        self.plot_frame.plot(n_plot, Qs_plot, color = '#1F77B4', label = "fitted curve")
        self.plot_frame.legend()
        self.plot_frame.show()
        # 更新text_result
        self.text_frame.append(f"拟合结果\n")
        self.text_frame.append(f"Qs0 = {self.Qs0:.6} ± {self.stddev_Qs0:.3} (kJ/mol)    a = {self.a:.6} ± {self.stddev_a:.3}\n")
        self.text_frame.append(f"Qs (kJ/mol) = {self.Qs0:.6} × {self.a:.6} × n0 / (1 + {self.a:.6} × n0), r_square = {self.r_square:.9f}\n\n")
        dissolution_test_data_width = np.max(np.char.str_len(self.dissolution_test_data), axis = 0) + 2
        dissolution_test_data_formatted = np.char.center(self.dissolution_test_data, dissolution_test_data_width)
        self.text_frame.append( f"测试数据\n")
        for row in dissolution_test_data_formatted:
            self.text_frame.append("|" + "|".join(row) + "|\n")
        self.text_frame.append("\n")
        self.text_frame.see("end")
        # 更新文件名
        self.info_label.config(text = self.file_name)
        # 更新button_save
        self.button_save.config(state = "normal")

    def save_file(self):
        try:
            with open(self.absolute_path.replace("." + self.extension, "_fitted_data.csv"), "w", encoding = "UTF-8", newline = "") as f:
                writer = csv.writer(f)
                writer.writerow(["n0", "Qs(kJ/mol)"])
                n0_Qs = np.stack((self.n, self.Qs), axis = 1)
                writer.writerows(n0_Qs)
                writer.writerow([])
                writer.writerow(["Qs0(kJ/mol)", "a"])
                writer.writerow([self.Qs0, self.a])
                writer.writerow([])
                writer.writerows(self.dissolution_test_data)
        except PermissionError:
            self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 保存失败！请关闭{self.file_name}_fitted_data.csv文件后再次尝试保存\n")
            self.text_frame.see("end")
            showwarning(title = "警告", message = f"保存失败！请关闭{self.file_name}_fitted_data.csv文件后再次尝试保存")
            return
        self.plot_frame.save_fig(self.absolute_path.replace(self.extension, "png"))
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {self.file_name}_fitted_data.csv文件保存成功\n")
        self.text_frame.append(f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {self.file_name}.png保存成功\n")
        self.text_frame.see("end")
        showinfo(title = "提示", message = f"保存成功！\n{self.file_name}.png保存至{self.absolute_path.replace(self.file_name + '.' + self.extension, '')}\n计算数据保存至同目录下的dissolution_fitted_data.csv文件")  

class App:
    """
    应用主体
    """

    def __init__(self,
                 dx: float = 0.1,
                 time_interval: int = 500,
                 plot_max_points: int = 500,
                 port_timeout: float = 0.25,
                 std_limit: float = 0.005,
                 time_lower_limit: int = 30,
                 time_upper_limit: int = 40,
                 width_height_inches: tuple = (10, 7),
                 dpi: int = 600,
                 py_path: str = os.path.dirname(os.path.abspath(__file__))
                 ):
        DATA_CONFIG["app"] = self
        DATA_CONFIG["dx"] = dx
        DATA_CONFIG["time_interval"]=time_interval
        DATA_CONFIG["plot_max_points"]=plot_max_points
        DATA_CONFIG["port_timeout"]=port_timeout
        DATA_CONFIG["py_path"]=py_path
        DATA_CONFIG["std_limit"]=std_limit
        DATA_CONFIG["time_lower_limit"]=time_lower_limit
        DATA_CONFIG["time_upper_limit"]=time_upper_limit
        DATA_CONFIG["width_height_inches"]=width_height_inches
        DATA_CONFIG["dpi"]=dpi
        DATA_CONFIG["window"]=ttk.Window(themename="sandstone",title="溶解热-燃烧热数据采集与处理软件 v2.2.0")
        try:
            if sys.platform.startswith('darwin'):
                # Mac系统
                #DATA_CONFIG["window"].iconbitmap(os.path.dirname(os.path.abspath(__file__)) + "/chem.icns")
                DATA_CONFIG["window"].iconphoto(True, PhotoImage(file = os.path.dirname(os.path.abspath(__file__)) + "/chem.png"))
            else:
                # Windows系统等
                DATA_CONFIG["window"].iconbitmap(os.path.dirname(os.path.abspath(__file__)) + "/chem.ico")
        except:
            pass
        # 初始化窗口大小
        min_height = 960
        min_width = int(min_height * 4 / 3)
        DATA_CONFIG["window"].minsize(min_width, min_height)
        DATA_CONFIG["window"].geometry(f"{min_width}x{min_height}")
        # 获取屏幕高度
        screen_height = DATA_CONFIG["window"].winfo_screenheight()
        screen_width = DATA_CONFIG["window"].winfo_screenwidth()
        # 完整显示的宽高为1280x960，默认高度为屏幕高度的75%，宽高比为4:3
        default_height = int(screen_height * 0.75)
        default_width = int(screen_height * 0.75 * 4 / 3)
        # 如果屏幕分辨率过低，那么调整最小窗口大小
        if screen_height < min_height or screen_width < min_width:
            DATA_CONFIG["window"].minsize(screen_width, screen_height)
            default_height = screen_height
            default_width = screen_width
            DATA_CONFIG["window"].geometry(f"{default_width}x{default_height}")
        # 如果屏幕分辨率满足要求，但默认宽高不能完全显示，那么不需要调整窗口大小
        # 如果屏幕分辨率满足要求，且默认宽高可以完全显示，那么调整窗口大小
        elif screen_height * 0.75 > min_height and screen_height * 0.75 * 4 / 3 > min_width:
            # 设置窗口大小默认高度为屏幕高度的75%，宽高比为4:3
            default_height = int(screen_height * 0.75)
            default_width = int(screen_height * 0.75 * 4 / 3)
            DATA_CONFIG["window"].geometry(f"{default_width}x{default_height}")
        # 使窗口在左上角显示
        DATA_CONFIG["window"].geometry("+0+0")
        #self.get_shortcut_states()
        DATA_CONFIG["screen"]=Screen1_Data()
        DATA_CONFIG["window"].mainloop()
    
    # 切换窗口
    def change_mode(self,*args):
        DATA_CONFIG["screen"].destroy()
        event=DATA_CONFIG["mode"].get()
        if event == "数据记录":
            DATA_CONFIG["screen"]=Screen1_Data()
        elif event == "溶解热":
            DATA_CONFIG["screen"]=Screen2_Dissolution()
        elif event == "燃烧热":
            DATA_CONFIG["screen"]=Screen3_Combustion()
        elif event == "溶解热拟合":
            DATA_CONFIG["screen"]=Screen4_Fit()
    
    # 响应数据修改
    def data_changed(self):
        pass