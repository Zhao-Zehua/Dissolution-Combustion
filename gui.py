# Author: 赵泽华
# 内置库
import csv
import os
import re
import sys
import time
#from tkinter import ttk
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
import maths
from water_capacity_smooth import water_capacity_smooth
from water_density_smooth import water_density_smooth

class Dissolution_Combustion:
    def __init__(self, dx: float = 0.1, time_interval: int = 500, plot_max_points: int = 500, port_timeout: float = 0.25, std_limit: float = 0.005, time_lower_limit: int = 30, time_upper_limit: int = 40, width_height_inches: tuple = (10, 7), dpi: int = 600, py_path: str = os.path.dirname(os.path.abspath(__file__))):
        '''
        dx: 积分、绘图步长
        time_interval: 记录数据间隔，单位毫秒
        plot_max_points: 绘图最大点数
        port_timeout: 串口超时时间，单位秒
        std_limit: 自动寻找平台期的标准差阈值
        time_lower_limit: 自动寻找平台期的最小时间窗口
        time_upper_limit: 自动寻找平台期的最大时间窗口
        width_height_inches: 保存图片尺寸，单位英尺
        dpi: 保存图片DPI
        '''
        # 初始化参数
        self.dx = dx    # 积分、绘图步长
        self.time_interval = time_interval  # 记录数据间隔，单位毫秒
        self.plot_max_points = plot_max_points  # 绘图最大点数
        self.port_timeout = port_timeout  # 串口超时时间，单位秒
        self.std_limit = std_limit  # 自动寻找平台期的标准差阈值
        self.time_lower_limit = time_lower_limit    # 自动寻找平台期的最小时间窗口
        self.time_upper_limit = time_upper_limit    # 自动寻找平台期的最大时间窗口
        self.width_height_inches = width_height_inches  # 保存图片尺寸，单位英尺
        self.dpi = dpi  # 保存图片DPI
        self.py_path = py_path  # main.py的绝对路径
        # 初始化根窗口
        #self.root = Tk()   # 一般版本
        self.root = ttk.Window(themename = "sandstone")  # 美化版本，自动适应高DPI
        '''
        # tkinter高DPI适配，可能会卡一些神奇的bug
        scale_factor = 1.0
        # ttkbootstrap会自动适应高DPI
        if sys.platform.startswith('win'):
            # Windows系统
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
            self.root.tk.call('tk', 'scaling', scale_factor / 0.75)
        elif sys.platform.startswith('darwin'):
            # Mac系统
            scale_factor = self.root.tk.call('tk', 'scaling')
            self.root.tk.call('tk', 'scaling', scale_factor)
            # 需要测试
        '''
        self.P = Figure(dpi = self.root.winfo_fpixels('1i'))# * scale_factor)
        self.P.subplots_adjust(left = 0.1, right = 0.9, top = 0.9, bottom = 0.15)
        self.f = self.P.add_subplot(111)
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
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
        self.canvas = FigureCanvasTkAgg(self.P, self.root)
        self.canvas.draw()
        self.canvas.draw_idle()
        PIL_image = pilImage.frombytes('RGB', self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        # 设置图形界面
        self.root.title("溶解热-燃烧热数据采集与处理软件")
        try:
            if sys.platform.startswith('darwin'):
                # Mac系统
                #self.root.iconbitmap(os.path.dirname(os.path.abspath(__file__)) + "/chem.icns")
                self.root.iconphoto(True, PhotoImage(file = os.path.dirname(os.path.abspath(__file__)) + "/chem.png"))
            else:
                # Windows系统等
                self.root.iconbitmap(os.path.dirname(os.path.abspath(__file__)) + "/chem.ico")
        except:
            pass
        # 初始化窗口大小
        self.root.minsize(800, 600)
        self.root.geometry("800x600")
        # 获取屏幕高度
        screen_height = self.root.winfo_screenheight()
        # 设置窗口大小默认高度为屏幕高度的75%，宽高比为4:3
        default_height = int(screen_height * 0.75)
        default_width = int(screen_height * 0.75 * 4 / 3)
        self.root.geometry(str(default_width) + "x" + str(default_height))
        # 初始化各个Frame
        self.Frame1 = ttk.Frame(self.root)
        self.Frame2 = ttk.Frame(self.root)
        self.Frame3 = ttk.Frame(self.root)
        self.Frame4 = ttk.Frame(self.root)
        # 默认显示Frame1
        self.Frame1_Data()
        self.canvas_plot.config(image = tk_image)
        self.canvas_plot.image = tk_image
        # 关闭时销毁根窗口
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.mainloop()

    '''
    以下为各模式图形界面的初始化函数
    Frame1_Data: 数据记录
    Frame2_Dissolution: 溶解热
    Frame3_Combustion: 燃烧热
    Frame4_Dissolution_Regression: 溶解热拟合

    样式
    relief = "raised" or "sunken"
    主框架borderwidth = 5，如self.framex, self.framex_left, self.framex_right_y
    有relief的次框架borderwidth = 1，如self.framex_right_1_left, self.framex_right_1_right
    无relief的次框架borderwidth = 2，如self.framex_left_y包含button或treeview或entry的框架
    包裹entry的次框架padding = 2
    '''
    # 数据记录
    def Frame1_Data(self):
        # 初始化Frame1变量
        # 初始化self变量
        self.mode = StringVar(value = "data")
        self.radiobutton_mode_selected = StringVar(value = "dissolution")
        self.absolute_path = str()
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.csv_state = 0  # 0代表未记录
        self.csv_data = [["time(s)", "Delta_T(K)", "state"]]  # 用于存储csv文件中的数据
        self.temp_Delta_t = [] # 用于存储串口读取的数据，长度不超过500
        self.temp_Delta_T = [] # 用于存储串口读取的数据，长度不超过500
        self.all_comports = []
        self.comport_selected = StringVar(value = "请刷新串口")
        self.comport = None
        self.read_comport()
        # 初始化内部变量
        button_mode_selected = StringVar(value = "数据记录")
        # 构建Frame1
        self.Frame1 = ttk.Frame(self.root, relief = "raised", borderwidth = 5)
        self.Frame1.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_paned = ttk.PanedWindow(self.Frame1, orient = "horizontal")
        frame1_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_left = ttk.Frame(frame1_paned, relief = "sunken", borderwidth = 5)
        frame1_paned.add(frame1_left, weight = 30)
        frame1_left_1 = ttk.Frame(frame1_left, borderwidth = 2)
        frame1_left_1.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.05)
        self.button_mode = ttk.OptionMenu(frame1_left_1, button_mode_selected, "数据记录", "溶解热", "燃烧热", "溶解热拟合", command = self.change_mode)
        self.button_mode.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_left_2 = ttk.Frame(frame1_left, borderwidth = 2)
        frame1_left_2.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_comport = ttk.OptionMenu(frame1_left_2, self.comport_selected, self.comport_selected.get(), *self.all_comports, command = self.change_comport)
        self.button_comport.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_left_3 = ttk.Frame(frame1_left, borderwidth = 2)
        frame1_left_3.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_comport_upgrade = ttk.Button(frame1_left_3, text = "刷新串口", command = self.get_comport)
        self.button_comport_upgrade.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_left_4 = ttk.Frame(frame1_left)
        frame1_left_4.place(relx = 0, rely = 0.15, relwidth = 1, relheight = 0.05)
        self.radiobutton_dissolution = ttk.Radiobutton(frame1_left_4, text = "溶解热", value = "dissolution", variable = self.radiobutton_mode_selected, command = self.data_mode)
        self.radiobutton_dissolution.place(relx = 0.25, rely = 0.5, anchor = "center")
        self.radiobutton_combustion = ttk.Radiobutton(frame1_left_4, text = "燃烧热", value = "combustion", variable = self.radiobutton_mode_selected, command = self.data_mode)
        self.radiobutton_combustion.place(relx = 0.75, rely = 0.5, anchor = "center")        
        frame1_left_5 = ttk.Frame(frame1_left, borderwidth = 2)
        frame1_left_5.place(relx = 0, rely = 0.2, relwidth = 1, relheight = 0.05)
        self.button_data_start = ttk.Button(frame1_left_5, text = "开始记录", command = self.data_start, state = "disabled")
        self.button_data_start.place(relx = 0, rely = 0, relwidth = 0.5, relheight = 1)
        self.button_data_stop = ttk.Button(frame1_left_5, text = "停止记录", command = self.data_stop, state = "disabled")
        self.button_data_stop.place(relx = 0.5, rely = 0, relwidth = 0.5, relheight = 1)
        frame1_left_6 = ttk.Frame(frame1_left, borderwidth = 2)
        frame1_left_6.place(relx = 0, rely = 0.25, relwidth = 1, relheight = 0.05)
        self.button_heat_start = ttk.Button(frame1_left_6, text = "开始加热", command = self.heat_start, state = "disabled")
        self.button_heat_start.place(relx = 0, rely = 0, relwidth = 0.5, relheight = 1)
        self.button_heat_stop = ttk.Button(frame1_left_6, text = "停止加热", command = self.heat_stop, state = "disabled")
        self.button_heat_stop.place(relx = 0.5, rely = 0, relwidth = 0.5, relheight = 1)
        frame1_left_7 = ttk.Frame(frame1_left, borderwidth = 2)
        frame1_left_7.place(relx = 0, rely = 0.3, relwidth = 1, relheight = 0.65)
        self.treeview_csv = ttk.Treeview(frame1_left_7, show = "headings", columns = ("time(s)", "Delta_T(K)"))
        self.treeview_csv.column("time(s)", width = 50, anchor = "center")
        self.treeview_csv.column("Delta_T(K)", width = 50, anchor = "center")
        self.treeview_csv.heading("time(s)", text = "time(s)")
        self.treeview_csv.heading("Delta_T(K)", text = "Delta_T(K)")
        self.treeview_csv.place(relx = 0, rely = 0, relwidth = 0.95, relheight = 1)
        treeview_scrollbar = ttk.Scrollbar(frame1_left_7, orient = "vertical")
        treeview_scrollbar.config(command = self.treeview_csv.yview)
        treeview_scrollbar.place(relx = 0.95, rely = 0, relwidth = 0.05, relheight = 1)
        frame1_left_8 = ttk.Frame(frame1_left)
        frame1_left_8.place(relx = 0, rely = 0.95, relwidth = 1, relheight = 0.05)
        self.label_path = ttk.Label(frame1_left_8, text = "作者：赵泽华 安孝彦", anchor = "center")
        self.label_path.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_right = ttk.Frame(frame1_paned)
        frame1_paned.add(frame1_right, weight = 70)
        frame1_right_paned = ttk.PanedWindow(frame1_right, orient = "vertical")
        frame1_right_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_right_1 = ttk.Frame(frame1_right_paned, relief = "sunken", borderwidth = 5)
        frame1_right_paned.add(frame1_right_1, weight = 35)
        self.text_result = ScrolledText(frame1_right_1, state = "disabled")
        self.text_result.config(state = "normal")
        self.text_result.insert("end", "数据记录模式使用说明\n")
        self.text_result.insert("end", "0. 点击左上角按钮切换模式\n")
        self.text_result.insert("end", "1. 选择正确的记录模式。\n")
        self.text_result.insert("end", "2. 点击刷新串口，程序将自动识别有数据输入的串口，并开始读取数据。如有多个有数据输入的串口，请自行选择正确的一个。\n")
        self.text_result.insert("end", "3. 点击开始记录，开始记录数据。\n")
        self.text_result.insert("end", "4. 如选择溶解热记录模式，在开始加热和结束加热时点击相应按钮。\n")
        self.text_result.insert("end", "5. 点击停止记录，停止记录数据，并保存。\n")
        self.text_result.insert("end", "6. 如数据丢失，可从与main.py同目录的tempfile.tmp中找到最近一次的记录数据。注意：溶解热的此数据需要处理后再使用。\n")
        self.text_result.insert("end", "7. 为保证csv文档的易读性，建议使用纯英文字符命名csv文件。\n\n")
        self.text_result.config(state = "disabled")
        self.text_result.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame1_right_2 = ttk.Frame(frame1_right_paned, relief = "sunken", borderwidth = 5)
        frame1_right_paned.add(frame1_right_2, weight = 65)
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        frame1_right_2.bind("<Configure>", self.resize_image)
        self.canvas_plot = ttk.Label(frame1_right_2, image = tk_image)
        self.canvas_plot.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

    # 溶解热计算
    def Frame2_Dissolution(self):
        # 初始化Frame2变量
        # 初始化self变量
        self.mode = StringVar(value = "dissolution")
        self.temperature = StringVar(value = "298.15")
        self.water_volume = StringVar(value = "500.0")
        self.water_density = StringVar(value = "0.9970470")
        self.water_capacity = StringVar(value = "4.1813")
        self.solute_molarmass = StringVar(value = "74.551")
        self.current = StringVar(value = "1.00")
        self.absolute_path = str()
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.stringvars_start_end()
        self.stringvars_dissolution()
        # 初始化内部变量
        button_mode_selected = StringVar(value = "溶解热")
        # 构建Frame2界面
        self.Frame2 = ttk.Frame(self.root, relief = "raised", borderwidth = 5)
        self.Frame2.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_paned = ttk.PanedWindow(self.Frame2, orient = "horizontal")
        frame2_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_left = ttk.Frame(frame2_paned, relief = "sunken", borderwidth = 5)
        frame2_paned.add(frame2_left, weight = 30)
        frame2_left_1 = ttk.Frame(frame2_left, borderwidth = 2)
        frame2_left_1.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.05)
        self.button_mode = ttk.OptionMenu(frame2_left_1, button_mode_selected, "溶解热", "数据记录", "燃烧热", "溶解热拟合", command = self.change_mode)
        self.button_mode.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_left_2 = ttk.Frame(frame2_left, borderwidth = 2)
        frame2_left_2.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_open = ttk.Button(frame2_left_2, text = "文件(.csv)", command = self.open_file)
        self.button_open.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_left_3 = ttk.Frame(frame2_left, borderwidth = 2)
        frame2_left_3.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_save = ttk.Button(frame2_left_3, text = "保存(.png)", command = self.save_file, state = "disabled")
        self.button_save.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_left_4 = ttk.Frame(frame2_left, borderwidth = 2)
        frame2_left_4.place(relx = 0, rely = 0.15, relwidth = 1, relheight = 0.8)
        self.treeview_csv = ttk.Treeview(frame2_left_4, show = "headings", columns = ("index", "time(s)", "Delta_T(K)"))
        self.treeview_csv.column("index", width = 25, anchor = "center")
        self.treeview_csv.column("time(s)", width = 50, anchor = "center")
        self.treeview_csv.column("Delta_T(K)", width = 50, anchor = "center")
        self.treeview_csv.heading("index", text = "index")
        self.treeview_csv.heading("time(s)", text = "time(s)")
        self.treeview_csv.heading("Delta_T(K)", text = "Delta_T(K)")
        self.treeview_csv.place(relx = 0, rely = 0, relwidth = 0.95, relheight = 1)
        treeview_scrollbar = ttk.Scrollbar(frame2_left_4, orient = "vertical")
        treeview_scrollbar.config(command = self.treeview_csv.yview)
        treeview_scrollbar.place(relx = 0.95, rely = 0, relwidth = 0.05, relheight = 1)
        frame2_left_5 = ttk.Frame(frame2_left)
        frame2_left_5.place(relx = 0, rely = 0.95, relwidth = 1, relheight = 0.05)
        self.label_path = ttk.Label(frame2_left_5, text = "作者: 赵泽华 安孝彦", anchor = "center")
        self.label_path.place(relx = 0.5, rely = 0.5, anchor = "center")
        frame2_right = ttk.Frame(frame2_paned)
        frame2_paned.add(frame2_right, weight = 70)
        frame2_right_paned = ttk.PanedWindow(frame2_right, orient = "vertical")
        frame2_right_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_right_1 = ttk.Frame(frame2_right_paned, relief = "sunken", borderwidth = 5)
        frame2_right_paned.add(frame2_right_1, weight = 20)
        frame2_right_1_paned = ttk.PanedWindow(frame2_right_1, orient = "horizontal")
        frame2_right_1_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_right_1_left = ttk.Frame(frame2_right_1_paned, relief = "sunken", borderwidth = 1, padding = 2)
        frame2_right_1_paned.add(frame2_right_1_left, weight = 30)
        frame2_right_1_left_1 = ttk.Frame(frame2_right_1_left, borderwidth = 2)
        frame2_right_1_left_1.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.25)
        label_start1 = ttk.Label(frame2_right_1_left_1, text = "Start 1")
        label_start1.config(anchor = "center")
        label_start1.place(relx = 0, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_start1 = ttk.Spinbox(frame2_right_1_left_1, textvariable = self.start1, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_start1.bind("<FocusIn>", lambda event: self.bind_return("start1"))
        self.entry_start1.bind("<FocusOut>", lambda event: self.unbind_return("start1"))        
        self.entry_start1.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = 1)
        label_end1 = ttk.Label(frame2_right_1_left_1, text = "End 1")    
        label_end1.config(anchor = "center")
        label_end1.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_end1 = ttk.Spinbox(frame2_right_1_left_1, textvariable = self.end1, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_end1.bind("<FocusIn>", lambda event: self.bind_return("end1"))
        self.entry_end1.bind("<FocusOut>", lambda event: self.unbind_return("end1"))
        self.entry_end1.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = 1)
        frame2_right_1_left_2 = ttk.Frame(frame2_right_1_left, borderwidth = 2)
        frame2_right_1_left_2.place(relx = 0, rely = 0.25, relwidth = 1, relheight = 0.25)
        label_start2 = ttk.Label(frame2_right_1_left_2, text = "Start 2")
        label_start2.config(anchor = "center")
        label_start2.place(relx = 0, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_start2 = ttk.Spinbox(frame2_right_1_left_2, textvariable = self.start2, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_start2.bind("<FocusIn>", lambda event: self.bind_return("start2"))
        self.entry_start2.bind("<FocusOut>", lambda event: self.unbind_return("start2"))
        self.entry_start2.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = 1)
        label_end2 = ttk.Label(frame2_right_1_left_2, text = "End 2")
        label_end2.config(anchor = "center")
        label_end2.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_end2 = ttk.Spinbox(frame2_right_1_left_2, textvariable = self.end2, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_end2.bind("<FocusIn>", lambda event: self.bind_return("end2"))
        self.entry_end2.bind("<FocusOut>", lambda event: self.unbind_return("end2"))
        self.entry_end2.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = 1)
        frame2_right_1_left_3 = ttk.Frame(frame2_right_1_left, borderwidth = 2)
        frame2_right_1_left_3.place(relx = 0, rely = 0.5, relwidth = 1, relheight = 0.25)
        label_start3 = ttk.Label(frame2_right_1_left_3, text = "Start 3")
        label_start3.config(anchor = "center")
        label_start3.place(relx = 0, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_start3 = ttk.Spinbox(frame2_right_1_left_3, textvariable = self.start3, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_start3.bind("<FocusIn>", lambda event: self.bind_return("start3"))
        self.entry_start3.bind("<FocusOut>", lambda event: self.unbind_return("start3"))
        self.entry_start3.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = 1)
        label_end3 = ttk.Label(frame2_right_1_left_3, text = "End 3")
        label_end3.config(anchor = "center")
        label_end3.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_end3 = ttk.Spinbox(frame2_right_1_left_3, textvariable = self.end3, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_end3.bind("<FocusIn>", lambda event: self.bind_return("end3"))
        self.entry_end3.bind("<FocusOut>", lambda event: self.unbind_return("end3"))
        self.entry_end3.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = 1)
        frame2_right_1_left_4 = ttk.Frame(frame2_right_1_left)
        frame2_right_1_left_4.place(relx = 0, rely = 0.75, relwidth = 1, relheight = 0.25)
        frame2_right_1_left_4_left = ttk.Frame(frame2_right_1_left_4, borderwidth = 2)
        frame2_right_1_left_4_left.place(relx = 0, rely = 0, relwidth = 0.5, relheight = 1)
        self.button_remake = ttk.Button(frame2_right_1_left_4_left, text = "重置", command = self.remake_file, state = "disabled")
        self.button_remake.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_right_1_left_4_right = ttk.Frame(frame2_right_1_left_4, borderwidth = 2)
        frame2_right_1_left_4_right.place(relx = 0.5, rely = 0, relwidth = 0.5, relheight = 1)
        self.button_integrate = ttk.Button(frame2_right_1_left_4_right, text = "计算", command = self.calculate_integration, state = "disabled")
        self.button_integrate.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_right_1_right = ttk.Frame(frame2_right_1_paned, relief = "sunken", borderwidth = 1, padding = 2)
        frame2_right_1_paned.add(frame2_right_1_right, weight = 70)
        # 参数第一行
        label_temperature = ttk.Label(frame2_right_1_right, text = "温度(K)")
        label_temperature.config(padding = 2)
        label_temperature.place(relx = 0, rely = 0, relwidth = 0.25, relheight = float(1 / 6))
        self.entry_temperature = ttk.Entry(frame2_right_1_right, textvariable = self.temperature, state = "disabled")
        self.entry_temperature.bind("<FocusOut>", lambda event: self.check_memory("temperature"))
        self.entry_temperature.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = float(1 / 6))
        label_water_volume = ttk.Label(frame2_right_1_right, text = "水体积(mL)")
        label_water_volume.config(padding = 2)
        label_water_volume.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = float(1 / 6))
        self.entry_water_volume = ttk.Entry(frame2_right_1_right, textvariable = self.water_volume, state = "disabled")
        self.entry_water_volume.bind("<FocusOut>", self.check_memory)
        self.entry_water_volume.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = float(1 / 6))
        # 参数第二行
        label_water_density = ttk.Label(frame2_right_1_right, text = "水密度(g/mL)")
        label_water_density.config(padding = 2)
        label_water_density.place(relx = 0, rely = float(1 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_water_density = ttk.Entry(frame2_right_1_right, textvariable = self.water_density, state = "disabled")
        self.entry_water_density.bind("<FocusOut>", self.check_memory)
        self.entry_water_density.place(relx = 0.25, rely = float(1 / 6), relwidth = 0.25, relheight = float(1 / 6))
        label_water_capacity = ttk.Label(frame2_right_1_right, text = "水热容(J/gK)")
        label_water_capacity.config(padding = 2)
        label_water_capacity.place(relx = 0.5, rely = float(1 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_water_capacity = ttk.Entry(frame2_right_1_right, textvariable = self.water_capacity, state = "disabled")
        self.entry_water_capacity.bind("<FocusOut>", self.check_memory)
        self.entry_water_capacity.place(relx = 0.75, rely = float(1 / 6), relwidth = 0.25, relheight = float(1 / 6))
        # 参数第三行
        label_solute_mass = ttk.Label(frame2_right_1_right, text = "溶质质量(g)")
        label_solute_mass.config(padding = 2)
        label_solute_mass.place(relx = 0, rely = float(2 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_solute_mass = ttk.Entry(frame2_right_1_right, textvariable = self.solute_mass, state = "disabled")
        self.entry_solute_mass.bind("<FocusOut>", self.check_memory)
        self.entry_solute_mass.place(relx = 0.25, rely = float(2 / 6), relwidth = 0.25, relheight = float(1 / 6))
        label_solute_molarmass = ttk.Label(frame2_right_1_right, text = "溶质式量(g/mol)")
        label_solute_molarmass.config(padding = 2)
        label_solute_molarmass.place(relx = 0.5, rely = float(2 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_solute_molarmass = ttk.Entry(frame2_right_1_right, textvariable = self.solute_molarmass, state = "disabled")
        self.entry_solute_molarmass.bind("<FocusOut>", self.check_memory)
        self.entry_solute_molarmass.place(relx = 0.75, rely = float(2 / 6), relwidth = 0.25, relheight = float(1 / 6))
        # 参数第四行
        label_R1 = ttk.Label(frame2_right_1_right, text = "加热前电阻(Ω)")
        label_R1.config(padding = 2)
        label_R1.place(relx = 0, rely = float(3 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_R1 = ttk.Entry(frame2_right_1_right, textvariable = self.R1, state = "disabled")
        self.entry_R1.bind("<FocusOut>", self.check_memory)
        self.entry_R1.place(relx = 0.25, rely = float(3 / 6), relwidth = 0.25, relheight = float(1 / 6))
        label_R2 = ttk.Label(frame2_right_1_right, text = "加热后电阻(Ω)")
        label_R2.config(padding = 2)
        label_R2.place(relx = 0.5, rely = float(3 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_R2 = ttk.Entry(frame2_right_1_right, textvariable = self.R2, state = "disabled")
        self.entry_R2.bind("<FocusOut>", self.check_memory)
        self.entry_R2.place(relx = 0.75, rely = float(3 / 6), relwidth = 0.25, relheight = float(1 / 6))
        # 参数第五行
        label_t1 = ttk.Label(frame2_right_1_right, text = "加热开始时间(s)")
        label_t1.config(padding = 2)
        label_t1.place(relx = 0, rely = float(4 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_t1 = ttk.Entry(frame2_right_1_right, textvariable = self.t1, state = "disabled")
        self.entry_t1.bind("<FocusOut>", self.check_memory)
        self.entry_t1.place(relx = 0.25, rely = float(4 / 6), relwidth = 0.25, relheight = float(1 / 6))
        label_t2 = ttk.Label(frame2_right_1_right, text = "加热结束时间(s)")
        label_t2.config(padding = 2)
        label_t2.place(relx = 0.5, rely = float(4 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_t2 = ttk.Entry(frame2_right_1_right, textvariable = self.t2, state = "disabled")
        self.entry_t2.bind("<FocusOut>", self.check_memory)
        self.entry_t2.place(relx = 0.75, rely = float(4 / 6), relwidth = 0.25, relheight = float(1 / 6))
        # 参数第六行
        label_current = ttk.Label(frame2_right_1_right, text = "电流(A)")
        label_current.config(padding = 2)
        label_current.place(relx = 0, rely = float(5 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_current = ttk.Entry(frame2_right_1_right, textvariable = self.current, state = "disabled")
        self.entry_current.bind("<FocusOut>", self.check_memory)
        self.entry_current.place(relx = 0.25, rely = float(5 / 6), relwidth = 0.25, relheight = float(1 / 6))
        label_dissolution_heat = ttk.Label(frame2_right_1_right, text = "溶解热(kJ)")
        label_dissolution_heat.config(padding = 2)
        label_dissolution_heat.place(relx = 0.5, rely = float(5 / 6), relwidth = 0.25, relheight = float(1 / 6))
        self.entry_dissolution_heat = ttk.Entry(frame2_right_1_right, textvariable = self.dissolution_heat, state = "disabled")
        self.entry_dissolution_heat.place(relx = 0.75, rely = float(5 / 6), relwidth = 0.25, relheight = float(1 / 6))
        frame2_right_2 = ttk.Frame(frame2_right_paned, relief = "sunken", borderwidth = 5)
        frame2_right_paned.add(frame2_right_2, weight = 15)
        self.text_result = ScrolledText(frame2_right_2)
        self.text_result.insert("end", "溶解热模式使用说明\n")
        self.text_result.insert("end", "0. 点击左上角按钮切换模式\n")
        self.text_result.insert("end", "1. 点击文件(.csv)导入文件，建议文件名不包含中文字符。\n")
        self.text_result.insert("end", "2. csv文件格式：第一行为标题行，第一列为升序的time(s)，第二列为Delta_T(K)，第三列为state；同一行数据间以半角逗号分隔。state为1是开始加热的标志点，state为2是结束加热的标志点。\n")
        self.text_result.insert("end", "3. 调整Start 1 < End 1 < Start 2 < End 2 < Start 3 < End 3至合适位置。\n")
        self.text_result.insert("end", "4. 点击计算进行积分和溶解热计算。\n")
        self.text_result.insert("end", "5. 点击保存(.png)保存结果，并输出一个dissolution.csv文档，其中储存了本次计算的参数和结果。dissolution.csv可以直接用于积分溶解热的拟合计算。\n")
        self.text_result.insert("end", "6. 输入框可以自动识别并提取其中的合法数字。\n")
        self.text_result.insert("end", "7. 常数，如温度、水的体积等会自动记忆。\n")
        self.text_result.insert("end", "8. 内置了CRC Handbook of Chemistry and Physics 95th Edition中水的密度和热容常数，根据输入温度自动取值。\n")
        self.text_result.insert("end", "9. 如导入文件后没有响应，检查文件的编码格式是否为UTF-8，检查文件内有无特殊字符。\n\n")
        self.text_result.config(state = "disabled")
        self.text_result.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame2_right_3 = ttk.Frame(frame2_right_paned, relief = "sunken", borderwidth = 5)
        frame2_right_paned.add(frame2_right_3, weight = 65)
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        frame2_right_3.bind("<Configure>", self.resize_image)
        self.canvas_plot = ttk.Label(frame2_right_3, image = tk_image)
        self.canvas_plot.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

    # 燃烧热计算
    def Frame3_Combustion(self):
        # 初始化Frame3变量
        # 初始化self变量
        self.mode = StringVar(value = "combustion")
        self.radiobutton_mode_selected = StringVar(value = "constant")
        self.temperature = StringVar(value = "298.15")
        self.water_volume = StringVar(value = "3000.0")
        self.water_density = StringVar(value = "0.9970470")
        self.water_capacity = StringVar(value = "4.1813")
        self.benzoic_enthalpy = StringVar(value = "-3228.2")
        self.cotton_heat = StringVar(value = "-16736")
        self.Nickel_heat = StringVar(value = "-3243")
        self.constant = StringVar()
        self.absolute_path = str()
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.stringvars_start_end()
        self.stringvars_combustion()
        # 初始化内部变量
        button_mode_selected = StringVar(value = "燃烧热")
        # 构建Frame3
        self.Frame3 = ttk.Frame(self.root, relief = "raised", borderwidth = 5)
        self.Frame3.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_paned = ttk.PanedWindow(self.Frame3, orient = "horizontal")
        frame3_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_left = ttk.Frame(frame3_paned, relief = "sunken", borderwidth = 5)
        frame3_paned.add(frame3_left, weight = 30)
        frame3_left_1 = ttk.Frame(frame3_left, borderwidth = 2)
        frame3_left_1.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.05)
        self.button_mode = ttk.OptionMenu(frame3_left_1, button_mode_selected, "燃烧热", "数据记录", "溶解热", "溶解热拟合", command = self.change_mode)
        self.button_mode.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_left_2 = ttk.Frame(frame3_left, borderwidth = 2)
        frame3_left_2.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_open = ttk.Button(frame3_left_2, text = "文件(.csv)", command = self.open_file)
        self.button_open.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_left_3 = ttk.Frame(frame3_left, borderwidth = 2)
        frame3_left_3.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_save = ttk.Button(frame3_left_3, text = "保存(.png)", command = self.save_file, state = "disabled")
        self.button_save.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_left_4 = ttk.Frame(frame3_left, borderwidth = 2)
        frame3_left_4.place(relx = 0, rely = 0.15, relwidth = 1, relheight = 0.8)
        self.treeview_csv = ttk.Treeview(frame3_left_4, show = "headings", columns = ("index", "time(s)", "Delta_T(K)"))
        self.treeview_csv.column("index", width = 25, anchor = "center")
        self.treeview_csv.column("time(s)", width = 50, anchor = "center")
        self.treeview_csv.column("Delta_T(K)", width = 50, anchor = "center")
        self.treeview_csv.heading("index", text = "index")
        self.treeview_csv.heading("time(s)", text = "time(s)")
        self.treeview_csv.heading("Delta_T(K)", text = "Delta_T(K)")
        self.treeview_csv.place(relx = 0, rely = 0, relwidth = 0.95, relheight = 1)
        treeview_scrollbar = ttk.Scrollbar(frame3_left_4, orient = "vertical")
        treeview_scrollbar.config(command = self.treeview_csv.yview)
        treeview_scrollbar.place(relx = 0.95, rely = 0, relwidth = 0.05, relheight = 1)
        frame3_left_5 = ttk.Frame(frame3_left)
        frame3_left_5.place(relx = 0, rely = 0.95, relwidth = 1, relheight = 0.05)
        self.label_path = ttk.Label(frame3_left_5, text = "作者：赵泽华 安孝彦", anchor = "center")
        self.label_path.place(relx = 0.5, rely = 0.5, anchor = "center")
        frame3_right = ttk.Frame(frame3_paned)
        frame3_paned.add(frame3_right, weight = 70)
        frame3_right_paned = ttk.PanedWindow(frame3_right, orient = "vertical")
        frame3_right_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_right_1 = ttk.Frame(frame3_right_paned, relief = "sunken", borderwidth = 5)
        frame3_right_paned.add(frame3_right_1, weight = 20)
        frame3_right_1_paned = ttk.PanedWindow(frame3_right_1, orient = "horizontal")
        frame3_right_1_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_right_1_left = ttk.Frame(frame3_right_1_paned, relief = "sunken", borderwidth = 1, padding = 2)
        frame3_right_1_paned.add(frame3_right_1_left, weight = 30)
        frame3_right_1_left_1 = ttk.Frame(frame3_right_1_left, borderwidth = 2)
        frame3_right_1_left_1.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.25)
        label_start1 = ttk.Label(frame3_right_1_left_1, text = "Start 1")
        label_start1.config(anchor = "center")
        label_start1.place(relx = 0, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_start1 = ttk.Spinbox(frame3_right_1_left_1, textvariable = self.start1, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_start1.bind("<FocusIn>", lambda event: self.bind_return("start1"))
        self.entry_start1.bind("<FocusOut>", lambda event: self.unbind_return("start1"))        
        self.entry_start1.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = 1)
        label_end1 = ttk.Label(frame3_right_1_left_1, text = "End 1")
        label_end1.config(anchor = "center")
        label_end1.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_end1 = ttk.Spinbox(frame3_right_1_left_1, textvariable = self.end1, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_end1.bind("<FocusIn>", lambda event: self.bind_return("end1"))
        self.entry_end1.bind("<FocusOut>", lambda event: self.unbind_return("end1"))
        self.entry_end1.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = 1)
        frame3_right_1_left_2 = ttk.Frame(frame3_right_1_left, borderwidth = 2)
        frame3_right_1_left_2.place(relx = 0, rely = 0.25, relwidth = 1, relheight = 0.25)
        label_start2 = ttk.Label(frame3_right_1_left_2, text = "Start 2")
        label_start2.config(anchor = "center")
        label_start2.place(relx = 0, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_start2 = ttk.Spinbox(frame3_right_1_left_2, textvariable = self.start2, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_start2.bind("<FocusIn>", lambda event: self.bind_return("start2"))
        self.entry_start2.bind("<FocusOut>", lambda event: self.unbind_return("start2"))
        self.entry_start2.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = 1)
        label_end2 = ttk.Label(frame3_right_1_left_2, text = "End 2")
        label_end2.config(anchor = "center")
        label_end2.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = 1)
        self.entry_end2 = ttk.Spinbox(frame3_right_1_left_2, textvariable = self.end2, command = self.input_, from_ = 0, to = 0, increment = 1, state = "disabled")
        self.entry_end2.bind("<FocusIn>", lambda event: self.bind_return("end2"))
        self.entry_end2.bind("<FocusOut>", lambda event: self.unbind_return("end2"))
        self.entry_end2.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = 1)
        frame3_right_1_left_3 = ttk.Frame(frame3_right_1_left)
        frame3_right_1_left_3.place(relx = 0, rely = 0.5, relwidth = 1, relheight = 0.25)
        frame3_right_1_left_3_left = ttk.Frame(frame3_right_1_left_3, borderwidth = 2)
        frame3_right_1_left_3_left.place(relx = 0, rely = 0, relwidth = 0.5, relheight = 1)
        self.button_remake = ttk.Button(frame3_right_1_left_3_left, text = "重置", command = self.remake_file, state = "disabled")
        self.button_remake.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_right_1_left_3_right = ttk.Frame(frame3_right_1_left_3, borderwidth = 2)
        frame3_right_1_left_3_right.place(relx = 0.5, rely = 0, relwidth = 0.5, relheight = 1)
        self.button_integrate = ttk.Button(frame3_right_1_left_3_right, text = "计算", command = self.calculate_integration, state = "disabled")
        self.button_integrate.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_right_1_left_4 = ttk.Frame(frame3_right_1_left)
        frame3_right_1_left_4.place(relx = 0, rely = 0.75, relwidth = 1, relheight = 0.25)
        # 两种测量模式
        # 若修改为三种，需要修改self.Frame3_Combustion, self.combustion_mode, maths.calculate_combustion
        self.radiobutton_constant = ttk.Radiobutton(frame3_right_1_left_4, text = "常数", value = "constant", variable = self.radiobutton_mode_selected, command = self.combustion_mode, state = "disabled")
        self.radiobutton_constant.place(relx = 0.25, rely = 0.5, anchor = "center")
        self.radiobutton_combustible = ttk.Radiobutton(frame3_right_1_left_4, text = "样品", value = "combustible", variable = self.radiobutton_mode_selected, command = self.combustion_mode, state = "disabled")
        self.radiobutton_combustible.place(relx = 0.75, rely = 0.5, anchor = "center")        
        '''
        # 三种测量模式
        # 若修改为两种，需要修改self.Frame3_Combustion, self.combustion_mode, self.remake_file, maths.calculate_combustion
        self.radiobutton_constant = ttk.Radiobutton(frame3_right_1_left_4, text = "常数", value = "constant", variable = self.radiobutton_mode_selected, command = self.combustion_mode, state = "disabled")
        self.radiobutton_constant.place(relx = float(1 / 6), rely = 0.5, anchor = "center")
        self.radiobutton_combustible = ttk.Radiobutton(frame3_right_1_left_4, text = "固体", value = "combustible", variable = self.radiobutton_mode_selected, command = self.combustion_mode, state = "disabled")
        self.radiobutton_combustible.place(relx = 0.5, rely = 0.5, anchor = "center")
        self.radiobutton_liquid = ttk.Radiobutton(frame3_right_1_left_4, text = "食用油", value = "liquid", variable = self.radiobutton_mode_selected, command = self.combustion_mode, state = "disabled")
        self.radiobutton_liquid.place(relx = float(5 / 6), rely = 0.5, anchor = "center")
        '''
        frame3_right_1_right = ttk.Frame(frame3_right_1_paned, relief = "sunken", borderwidth = 1, padding = 2)
        frame3_right_1_paned.add(frame3_right_1_right, weight = 70)
        # 参数第一行
        label_temperature = ttk.Label(frame3_right_1_right, text = "温度(K)")
        label_temperature.config(padding = 2)
        label_temperature.place(relx = 0, rely = 0, relwidth = 0.25, relheight = float(1 / 7))
        self.entry_temperature = ttk.Entry(frame3_right_1_right, textvariable = self.temperature, state = "disabled")
        self.entry_temperature.bind("<FocusOut>", lambda event: self.check_memory("temperature"))
        self.entry_temperature.place(relx = 0.25, rely = 0, relwidth = 0.25, relheight = float(1 / 7))
        label_water_volume = ttk.Label(frame3_right_1_right, text = "水体积(mL)")
        label_water_volume.config(padding = 2)
        label_water_volume.place(relx = 0.5, rely = 0, relwidth = 0.25, relheight = float(1 / 7))
        self.entry_water_volume = ttk.Entry(frame3_right_1_right, textvariable = self.water_volume, state = "disabled")
        self.entry_water_volume.bind("<FocusOut>", self.check_memory)
        self.entry_water_volume.place(relx = 0.75, rely = 0, relwidth = 0.25, relheight = float(1 / 7))
        # 参数第二行
        label_water_density = ttk.Label(frame3_right_1_right, text = "水密度(g/mL)")
        label_water_density.config(padding = 2)
        label_water_density.place(relx = 0, rely = float(1 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_water_density = ttk.Entry(frame3_right_1_right, textvariable = self.water_density, state = "disabled")
        self.entry_water_density.bind("<FocusOut>", self.check_memory)
        self.entry_water_density.place(relx = 0.25, rely = float(1 / 7), relwidth = 0.25, relheight = float(1 / 7))
        label_water_capacity = ttk.Label(frame3_right_1_right, text = "水热容(J/gK)")
        label_water_capacity.config(padding = 2)
        label_water_capacity.place(relx = 0.5, rely = float(1 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_water_capacity = ttk.Entry(frame3_right_1_right, textvariable = self.water_capacity, state = "disabled")
        self.entry_water_capacity.bind("<FocusOut>", self.check_memory)
        self.entry_water_capacity.place(relx = 0.75, rely = float(1 / 7), relwidth = 0.25, relheight = float(1 / 7))
        # 参数第三行
        self.label_combustible_mass = ttk.Label(frame3_right_1_right, text = "苯甲酸+棉线(g)")
        self.label_combustible_mass.config(padding = 2)
        self.label_combustible_mass.place(relx = 0, rely = float(2 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_combustible_mass = ttk.Entry(frame3_right_1_right, textvariable = self.combustible_mass, state = "disabled")
        self.entry_combustible_mass.bind("<FocusOut>", self.check_memory)
        self.entry_combustible_mass.place(relx = 0.25, rely = float(2 / 7), relwidth = 0.25, relheight = float(1 / 7))
        label_cotton_mass = ttk.Label(frame3_right_1_right, text = "棉线(g)")
        label_cotton_mass.config(padding = 2)
        label_cotton_mass.place(relx = 0.5, rely = float(2 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_cotton_mass = ttk.Entry(frame3_right_1_right, textvariable = self.cotton_mass, state = "disabled")
        self.entry_cotton_mass.bind("<FocusOut>", self.check_memory)
        self.entry_cotton_mass.place(relx = 0.75, rely = float(2 / 7), relwidth = 0.25, relheight = float(1 / 7))
        # 参数第四行
        label_Nickel_before_mass = ttk.Label(frame3_right_1_right, text = "镍丝(g)")
        label_Nickel_before_mass.config(padding = 2)
        label_Nickel_before_mass.place(relx = 0, rely = float(3 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_Nickel_before_mass = ttk.Entry(frame3_right_1_right, textvariable = self.Nickel_before_mass, state = "disabled")
        self.entry_Nickel_before_mass.bind("<FocusOut>", self.check_memory)
        self.entry_Nickel_before_mass.place(relx = 0.25, rely = float(3 / 7), relwidth = 0.25, relheight = float(1 / 7))
        label_Nickel_after_mass = ttk.Label(frame3_right_1_right, text = "燃烧后镍丝(g)")
        label_Nickel_after_mass.config(padding = 2)
        label_Nickel_after_mass.place(relx = 0.5, rely = float(3 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_Nickel_after_mass = ttk.Entry(frame3_right_1_right, textvariable = self.Nickel_after_mass, state = "disabled")
        self.entry_Nickel_after_mass.bind("<FocusOut>", self.check_memory)
        self.entry_Nickel_after_mass.place(relx = 0.75, rely = float(3 / 7), relwidth = 0.25, relheight = float(1 / 7))
        # 参数第五行
        label_benzoic_enthalpy = ttk.Label(frame3_right_1_right, text = "苯甲酸燃烧焓(kJ/mol)")
        label_benzoic_enthalpy.config(padding = 2)
        label_benzoic_enthalpy.place(relx = 0, rely = float(4 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_benzoic_enthalpy = ttk.Entry(frame3_right_1_right, textvariable = self.benzoic_enthalpy, state = "disabled")
        self.entry_benzoic_enthalpy.bind("<FocusOut>", self.check_memory)
        self.entry_benzoic_enthalpy.place(relx = 0.25, rely = float(4 / 7), relwidth = 0.25, relheight = float(1 / 7))
        label_cotton_heat = ttk.Label(frame3_right_1_right, text = "棉线燃烧热(J/g)")
        label_cotton_heat.config(padding = 2)
        label_cotton_heat.place(relx = 0.5, rely = float(4 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_cotton_heat = ttk.Entry(frame3_right_1_right, textvariable = self.cotton_heat, state = "disabled")
        self.entry_cotton_heat.bind("<FocusOut>", self.check_memory)
        self.entry_cotton_heat.place(relx = 0.75, rely = float(4 / 7), relwidth = 0.25, relheight = float(1 / 7))
        # 参数第六行
        label_Nickel_heat = ttk.Label(frame3_right_1_right, text = "镍丝燃烧热(J/g)")
        label_Nickel_heat.config(padding = 2)
        label_Nickel_heat.place(relx = 0, rely = float(5 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_Nickel_heat = ttk.Entry(frame3_right_1_right, textvariable = self.Nickel_heat, state = "disabled")
        self.entry_Nickel_heat.bind("<FocusOut>", self.check_memory)
        self.entry_Nickel_heat.place(relx = 0.25, rely = float(5 / 7), relwidth = 0.25, relheight = float(1 / 7))
        label_constant = ttk.Label(frame3_right_1_right, text = "量热计常数(J/K)")
        label_constant.config(padding = 2)
        label_constant.place(relx = 0.5, rely = float(5 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_constant = ttk.Entry(frame3_right_1_right, textvariable = self.constant, state = "disabled")
        self.entry_constant.bind("<FocusOut>", self.check_memory)
        self.entry_constant.place(relx = 0.75, rely = float(5 / 7), relwidth = 0.25, relheight = float(1 / 7))
        # 参数第七行
        label_combustion_heat = ttk.Label(frame3_right_1_right, text = "恒容燃烧热(J/g)")
        label_combustion_heat.config(padding = 2)
        label_combustion_heat.place(relx = 0, rely = float(6 / 7), relwidth = 0.25, relheight = float(1 / 7))
        self.entry_combustion_heat = ttk.Entry(frame3_right_1_right, textvariable = self.combustion_heat, state = "disabled")
        self.entry_combustion_heat.place(relx = 0.25, rely = float(6 / 7), relwidth = 0.25, relheight = float(1 / 7))
        frame3_right_2 = ttk.Frame(frame3_right_paned, relief = "sunken", borderwidth = 5)
        frame3_right_paned.add(frame3_right_2, weight = 15)
        self.text_result = ScrolledText(frame3_right_2)
        self.text_result.insert("end", "燃烧热模式使用说明\n")
        self.text_result.insert("end", "0. 点击左上角按钮切换模式\n")
        self.text_result.insert("end", "1. 点击文件(.csv)导入文件，建议文件名不包含中文字符。\n")
        self.text_result.insert("end", "2. csv文件格式：第一行为标题行，第一列为升序的time(s)，第二列为Delta_T(K)；同一行数据间以半角逗号分隔。\n")
        self.text_result.insert("end", "3. 调整Start 1 < End 1 < Start 2 < End 2至合适位置。\n")
        # 两种测量模式
        # 若修改为三种，需要修改self.Frame3_Combustion, self.combustion_mode, maths.calculate_combustion
        self.text_result.insert("end", "4. 选择正确的计算模式。常数、样品模式分别用来计算量热计常数和样品燃烧热。\n")
        '''
        # 三种测量模式
        # 若修改为两种，需要修改self.Frame3_Combustion, self.combustion_mode, self.remake_file, maths.calculate_combustion
        self.text_result.insert("end", "4. 选择正确的计算模式。常数、固体、食用油三种模式分别用来计算量热计常数、固体燃烧热和食用油燃烧热。\n")
        '''
        self.text_result.insert("end", "5. 点击计算进行积分和燃烧热计算。\n")
        self.text_result.insert("end", "6. 点击保存(.png)保存图片，并输出一个combustion.csv文档，其中储存了本次计算的参数和结果。\n")
        self.text_result.insert("end", "7. 输入框可以自动识别并提取其中的合法数字。\n")
        self.text_result.insert("end", "8. 常数，如温度、水的体积等会自动记忆。\n")
        self.text_result.insert("end", "9. 内置了CRC Handbook of Chemistry and Physics 95th Edition中水的密度和热容常数，根据输入温度自动取值。\n")
        self.text_result.insert("end", "10. 如导入文件后没有响应，检查文件的编码格式是否为UTF-8，检查文件内有无特殊字符。\n\n")
        self.text_result.config(state = "disabled")
        self.text_result.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame3_right_3 = ttk.Frame(frame3_right_paned, relief = "sunken", borderwidth = 5)
        frame3_right_paned.add(frame3_right_3, weight = 65)
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        frame3_right_3.bind("<Configure>", self.resize_image)
        self.canvas_plot = ttk.Label(frame3_right_3, image = tk_image)
        self.canvas_plot.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

    # 溶解热拟合
    def Frame4_Dissolution_Fit(self):
        # 初始化Frame4变量
        # 初始化self变量
        self.mode = StringVar(value = "dissolution_regression")
        self.absolute_path = str()
        self.f.clear()
        self.f.set_xlabel("$n$")
        self.f.set_ylabel("$Q_s$ (kJ/mol)")
        # 初始化内部变量
        button_mode_selected = StringVar(value = "溶解热拟合")
        # 构建Frame4
        self.Frame4 = ttk.Frame(self.root, relief = "raised", borderwidth = 5)
        self.Frame4.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_paned = ttk.PanedWindow(self.Frame4, orient = "horizontal")
        frame4_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_left = ttk.Frame(frame4_paned, relief = "sunken", borderwidth = 5)
        frame4_paned.add(frame4_left, weight = 30)
        frame4_left_1 = ttk.Frame(frame4_left, borderwidth = 2)
        frame4_left_1.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.05)
        self.button_mode = ttk.OptionMenu(frame4_left_1, button_mode_selected, "溶解热拟合", "数据记录", "溶解热", "燃烧热", command = self.change_mode)
        self.button_mode.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_left_2 = ttk.Frame(frame4_left, borderwidth = 2)
        frame4_left_2.place(relx = 0, rely = 0.05, relwidth = 1, relheight = 0.05)
        self.button_open = ttk.Button(frame4_left_2, text = "文件(.csv)", command = self.open_dissolution_file)
        self.button_open.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_left_3 = ttk.Frame(frame4_left, borderwidth = 2)
        frame4_left_3.place(relx = 0, rely = 0.1, relwidth = 1, relheight = 0.05)
        self.button_save = ttk.Button(frame4_left_3, text = "保存(.png)", command = self.save_dissolution_file, state = "disabled")
        self.button_save.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_left_4 = ttk.Frame(frame4_left, borderwidth = 2)
        frame4_left_4.place(relx = 0, rely = 0.15, relwidth = 1, relheight = 0.8)
        self.treeview_csv = ttk.Treeview(frame4_left_4, show = "headings", columns = ("index", "n", "Qs(kJ/mol)"))
        self.treeview_csv.column("index", width = 25, anchor = "center")
        self.treeview_csv.column("n", width = 50, anchor = "center")
        self.treeview_csv.column("Qs(kJ/mol)", width = 50, anchor = "center")
        self.treeview_csv.heading("index", text = "index")
        self.treeview_csv.heading("n", text = "n")
        self.treeview_csv.heading("Qs(kJ/mol)", text = "Qs(kJ/mol)")
        self.treeview_csv.place(relx = 0, rely = 0, relwidth = 0.95, relheight = 1)
        treeview_scrollbar = ttk.Scrollbar(frame4_left_4, orient = "vertical")
        treeview_scrollbar.config(command = self.treeview_csv.yview)
        treeview_scrollbar.place(relx = 0.95, rely = 0, relwidth = 0.05, relheight = 1)
        frame4_left_5 = ttk.Frame(frame4_left)
        frame4_left_5.place(relx = 0, rely = 0.95, relwidth = 1, relheight = 0.05)
        self.label_path = ttk.Label(frame4_left_5, text = "作者：赵泽华 安孝彦", anchor = "center")
        self.label_path.place(relx = 0.5, rely = 0.5, anchor = "center")
        frame4_right = ttk.Frame(frame4_paned)
        frame4_paned.add(frame4_right, weight = 70)
        frame4_right_paned = ttk.PanedWindow(frame4_right, orient = "vertical")
        frame4_right_paned.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_right_1 = ttk.Frame(frame4_right_paned, relief = "sunken", borderwidth = 5)
        frame4_right_paned.add(frame4_right_1, weight = 35)
        self.text_result = ScrolledText(frame4_right_1)
        self.text_result.insert("end", "溶解热拟合模式使用说明\n")
        self.text_result.insert("end", "0. 点击左上角按钮切换模式\n")
        self.text_result.insert("end", "1. 点击文件(.csv)导入文件，默认文件名为dissolution.csv。\n")
        self.text_result.insert("end", "2. 导入的csv文件由本程序的溶解热模式自动生成。文件第一行为标题行，此后每一行必须按照实际实验顺序排列，且只能出现一次。输入文件不合法将无法计算，如格式有误请自行编辑。\n")
        self.text_result.insert("end", "3. 拟合方程为Qs = Qs0 × a × n / (1 + a × n)。\n")
        self.text_result.insert("end", "4. 点击保存(.png)保存图片。\n\n")
        self.text_result.config(state = "disabled")
        self.text_result.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)
        frame4_right_2 = ttk.Frame(frame4_right_paned, relief = "sunken", borderwidth = 5)
        frame4_right_paned.add(frame4_right_2, weight = 65)
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        frame4_right_2.bind("<Configure>", self.resize_image)
        self.canvas_plot = ttk.Label(frame4_right_2, image = tk_image)
        self.canvas_plot.place(relx = 0, rely = 0, relwidth = 1, relheight = 1)

    '''
    以下为变量声明函数
    '''
    # 溶解热和燃烧热计算中的起止点
    def stringvars_start_end(self):
        self.start1 = StringVar()
        self.end1 = StringVar()
        self.start2 = StringVar()
        self.end2 = StringVar()
        self.start3 = StringVar()
        self.end3 = StringVar()
        self.Start1 = int()
        self.End1 = int()
        self.Start2 = int()
        self.End2 = int()
        self.Start3 = int()
        self.End3 = int()
    
    # 部分溶解热计算参数
    def stringvars_dissolution(self):
        self.solute_mass = StringVar(value = "5.0000")
        self.R1 = StringVar(value = "10.00")
        self.R2 = StringVar(value = "10.00")
        self.t1 = StringVar()
        self.t2 = StringVar()
        self.dissolution_heat = StringVar()
        self.temperature_memory = self.temperature.get()
        self.water_volume_memory = self.water_volume.get()
        self.water_density_memory = self.water_density.get()
        self.water_capacity_memory = self.water_capacity.get()
        self.solute_mass_memory = self.solute_mass.get()
        self.solute_molarmass_memory = self.solute_molarmass.get()
        self.R1_memory = self.R1.get()
        self.R2_memory = self.R2.get()
        self.t1_memory = self.t1.get()
        self.t2_memory = self.t2.get()
        self.current_memory = self.current.get()
    
    # 部分燃烧热计算参数
    def stringvars_combustion(self):
        self.combustible_mass = StringVar(value = "1.0000")
        self.cotton_mass = StringVar(value = "0.0100")
        self.Nickel_before_mass = StringVar(value = "0.0080")
        self.Nickel_after_mass = StringVar(value = "0.0030")
        self.combustion_heat = StringVar()
        self.temperature_memory = self.temperature.get()
        self.water_volume_memory = self.water_volume.get()
        self.water_density_memory = self.water_density.get()
        self.water_capacity_memory = self.water_capacity.get()
        self.combustible_mass_memory = self.combustible_mass.get()
        self.cotton_mass_memory = self.cotton_mass.get()
        self.Nickel_before_mass_memory = self.Nickel_before_mass.get()
        self.Nickel_after_mass_memory = self.Nickel_after_mass.get()
        self.benzoic_enthalpy_memory = self.benzoic_enthalpy.get()
        self.cotton_heat_memory = self.cotton_heat.get()
        self.Nickel_heat_memory = self.Nickel_heat.get()
        self.constant_memory = self.constant.get()

    # 溶解热参数entry
    def entries_dissolution(self, state):
        self.entry_temperature.config(textvariable = self.temperature, state = state)
        self.entry_water_volume.config(textvariable = self.water_volume, state = state)
        self.entry_water_density.config(textvariable = self.water_density, state = state)
        self.entry_water_capacity.config(textvariable = self.water_capacity, state = "disabled")
        self.entry_solute_mass.config(textvariable = self.solute_mass, state = state)
        self.entry_solute_molarmass.config(textvariable = self.solute_molarmass, state = state)
        self.entry_R1.config(textvariable = self.R1, state = state)
        self.entry_R2.config(textvariable = self.R2, state = state)
        self.entry_t1.config(textvariable = self.t1, state = state)
        self.entry_t2.config(textvariable = self.t2, state = state)
        self.entry_current.config(textvariable = self.current, state = state)
        self.entry_dissolution_heat.config(textvariable = self.dissolution_heat, state = state)
    
    # 燃烧热参数entry
    def entries_combustion(self, state):
        self.entry_temperature.config(textvariable = self.temperature, state = state)
        self.entry_water_volume.config(textvariable = self.water_volume, state = state)
        self.entry_water_density.config(textvariable = self.water_density, state = state)
        self.entry_water_capacity.config(textvariable = self.water_capacity, state = state)
        self.entry_combustible_mass.config(textvariable = self.combustible_mass, state = state)
        self.entry_cotton_mass.config(textvariable = self.cotton_mass, state = state)
        self.entry_Nickel_before_mass.config(textvariable = self.Nickel_before_mass, state = state)
        self.entry_Nickel_after_mass.config(textvariable = self.Nickel_after_mass, state = state)
        self.entry_benzoic_enthalpy.config(textvariable = self.benzoic_enthalpy, state = state)
        self.entry_cotton_heat.config(textvariable = self.cotton_heat, state = state)
        self.entry_Nickel_heat.config(textvariable = self.Nickel_heat, state = state)
        self.entry_constant.config(textvariable = self.constant, state = state)
        self.entry_combustion_heat.config(textvariable = self.combustion_heat, state = state)

    '''
    以下为根窗口的控制函数
    '''
    # 切换窗口
    def change_mode(self, event):
        self.Frame1.destroy()
        self.Frame2.destroy()
        self.Frame3.destroy()
        self.Frame4.destroy()
        if event == "数据记录":
            self.Frame1_Data()
        elif event == "溶解热":
            self.Frame2_Dissolution()
        elif event == "燃烧热":
            self.Frame3_Combustion()
        elif event == "溶解热拟合":
            self.Frame4_Dissolution_Fit()
    
    # 从绝对路径获取文件名和扩展名
    def file_name_extension(self, absolute_path):
        file_name = absolute_path.split("/")[-1]
        extension = file_name.split(".")[-1]
        file_name = file_name.split(".")[0]
        return file_name, extension

    # 根据frame大小重绘图片
    def resize_image(self, event):
        frame_width, frame_height = event.width, event.height
        new_width, new_height = frame_width / self.P.dpi, frame_height / self.P.dpi
        self.P.set_size_inches(new_width, new_height, forward = True)
        self.canvas.draw()
        PIL_image = pilImage.frombytes('RGB', self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        self.canvas_plot.config(image = tk_image)
        self.canvas_plot.image = tk_image

    '''
    以下为数据记录模式的控制函数
    '''
    # 获取可用串口
    def get_comport(self):
        # 禁用按钮
        self.button_comport_upgrade.config(state = "disabled")
        self.button_data_start.config(state = "disabled")
        self.button_data_stop.config(state = "disabled")
        self.button_heat_start.config(state = "disabled")
        self.button_heat_stop.config(state = "disabled")
        # 提示信息
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 正在检测串口信息，请耐心等待！\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        # 关闭正在运行的串口
        self.comport.close() if self.comport else None
        # 获取串口信息
        self.all_comports = getComPorts(select = True, timeout =self.port_timeout)
        # 重置开始时间、数据记录、绘图
        self.time_start = time.time()
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.treeview_csv.delete(*self.treeview_csv.get_children())
        # 提示信息
        self.text_result.config(state = "normal")
        if self.all_comports:
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口检测完成，" + f"可用串口为{' '.join(self.all_comports)}\n")
        else:
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口检测完成，无可用串口\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        # 如果有可用串口
        if self.all_comports:
            # 如果当前选择的串口不在可用串口中
            if self.comport_selected.get() not in self.all_comports:
                # 选择第一个可用串口并打开
                self.comport_selected.set(self.all_comports[0])
                #self.change_comport(self.comport_selected.get())
                # 如果还没有开始读数(读数在打开程序后只需要启动一次)
                #if not self.comport_reading:
                #    self.read_comport()
            # 如果当前选择的串口在可用串口中
            #else:
                #self.button_data_start.config(state = "normal")
            self.change_comport(self.comport_selected.get())
        # 如果没有可用串口
        else:
            self.comport_selected.set("请刷新串口")
            self.comport.close() if self.comport else None
            self.comport = None
        # 更新按钮状态
        self.button_comport.set_menu(self.comport_selected.get(), *self.all_comports)
        self.button_comport_upgrade.config(state = "normal")

    # 重选串口
    def change_comport(self, event):
        self.comport.close() if self.comport else None
        self.comport = None
        self.comport_selected.set(event)
        self.button_comport.set_menu(self.comport_selected.get(), *self.all_comports)
        self.comport = EasySerial(event)
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口已切换为{event}\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.treeview_csv.delete(*self.treeview_csv.get_children())
        try:
            # 打开与py文件同目录的临时文件，用逗号分隔的形式存储数据，方便后续处理
            # exe文件不能用os.path.abspath获取当前目录
            self.temp_file = open(self.py_path + "/tempfile.tmp", "w", encoding = "UTF-8")
            self.temp_file.write("time(s),Delta_T(K)\n")
            self.temp_file.flush()
            self.time_start = time.time()
            self.comport.open()
            self.button_data_start.config(state = "normal")
        except:
            self.comport.close()
            self.button_data_start.config(state = "disabled")
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口打开失败，请尝试其他串口，或检查USB线缆连接状态。\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")

    # 读取串口数据
    def read_comport(self):
        try:
            # 读取串口数据
            Delta_T = self.comport.read()
            self.time_end = time.time()
            Delta_t = self.time_end - self.time_start
            # 将数据写入临时文件和csv文件
            try:
                self.temp_file.write(f"{Delta_t:.3f},{Delta_T:.3f}\n")
                self.temp_file.flush()
                self.treeview_csv.insert("", "end", values = (f"{Delta_t:.3f}", f"{Delta_T:.3f}"))
                self.treeview_csv.yview_moveto(1)
                self.temp_Delta_t.append(Delta_t)
                if len(self.temp_Delta_t) >= self.plot_max_points:
                    self.temp_Delta_t = self.temp_Delta_t[-self.plot_max_points:]
                self.temp_Delta_T.append(Delta_T)
                if len(self.temp_Delta_T) >= self.plot_max_points:
                    self.temp_Delta_T = self.temp_Delta_T[-self.plot_max_points:]
            except TypeError:
                pass
            if self.csv_state == 1:
                self.csv_data.append([Delta_t, Delta_T, 0])
            self.f.clear()
            self.f.set_xlabel("$t$ (s)")
            self.f.set_ylabel("$\Delta T$ (K)")
            self.f.plot(self.temp_Delta_t, self.temp_Delta_T, color = '#1F77B4')
            self.canvas.draw()
            PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
            tk_image = ImageTk.PhotoImage(PIL_image)
            self.canvas_plot.configure(image = tk_image)
            self.canvas_plot.image = tk_image

        except BufferError:
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口读取数据失败，请检查串口连接状态。\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")
        except IOError:
            self.comport.close()
            self.comport.open()
        except AttributeError:
            pass
        except FunctionTimedOut:
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 串口读取数据失败，请检查串口连接状态。\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")
        # self.comport_reading = True
        self.reading_comport = self.Frame1.after(self.time_interval, self.read_comport)

    # 开始记录数据
    def data_start(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.temp_file.close()
        self.temp_file = open(self.py_path + "/tempfile.tmp", "w", encoding = "UTF-8")
        self.temp_file.write("time(s),Delta_T(K)\n")
        self.temp_file.flush()
        self.time_start = time.time()
        self.csv_data = [["time(s)", "Delta_T(K)", "state"]]
        self.csv_state = 1
        self.button_mode.configure(state = "disabled")
        self.button_data_start.config(state = "disabled")
        self.button_comport.configure(state = "disabled")
        self.button_comport_upgrade.config(state = "disabled")
        self.radiobutton_combustion.config(state = "disabled")
        self.radiobutton_dissolution.config(state = "disabled")
        if self.radiobutton_mode_selected.get() == "dissolution":
            self.button_heat_start.config(state = "normal")
        elif self.radiobutton_mode_selected.get() == "combustion":
            self.button_data_stop.config(state = "normal")
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.treeview_csv.delete(*self.treeview_csv.get_children())
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 开始记录\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")

    # 停止记录数据
    def data_stop(self):
        self.csv_state = 0
        self.csv_path = filedialog.asksaveasfilename(title = "保存数据", initialfile = f"{time.strftime('%Y%m%d%H%M%S', time.localtime())}{self.radiobutton_mode_selected.get()}data.csv", filetypes = [("CSV", ".csv")])
        if self.csv_path == "":
            self.data_stop()
            return
        with open(self.csv_path, "w", encoding = "UTF-8", newline = "") as f:
            csv.writer(f).writerows(self.csv_data)
        showinfo(title = "提示", message = f"数据成功保存至{self.csv_path}")
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 停止记录\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        self.temp_file.close()
        self.temp_file = open(self.py_path + "/tempfile.tmp", "w", encoding = "UTF-8")
        self.temp_file.write("time(s),Delta_T(K)\n")
        self.temp_file.flush()
        self.time_start = time.time()
        self.temp_Delta_t = []
        self.temp_Delta_T = []
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        self.treeview_csv.delete(*self.treeview_csv.get_children())
        self.button_data_stop.config(state = "disabled")
        self.button_mode.configure(state = "normal")
        self.button_data_start.config(state = "normal")
        self.button_comport.configure(state = "normal")
        self.button_comport_upgrade.config(state = "normal")
        self.radiobutton_combustion.config(state = "normal")
        self.radiobutton_dissolution.config(state = "normal")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    # 开始加热 
    def heat_start(self):
        self.temp_file.write("start heating\n")
        self.temp_file.flush()
        self.csv_data[-1][2] = 1
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 开始加热\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        self.button_heat_start.config(state = "disabled")
        self.button_heat_stop.config(state = "normal")

    # 停止加热
    def heat_stop(self):
        self.temp_file.write("stop heating\n")
        self.temp_file.flush()
        self.csv_data[-1][2] = 2
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 停止加热\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        self.button_heat_stop.config(state = "disabled")
        self.button_data_stop.config(state = "normal")

    # 选择数据记录模式
    def data_mode(self):
        if self.radiobutton_mode_selected.get() == "dissolution":
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 当前选择溶解热模式\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")
        elif self.radiobutton_mode_selected.get() == "combustion":
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 当前选择燃烧热模式\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")

    '''
    以下为溶解热/燃烧热模式的控制函数
    '''
    # 打开文件
    def open_file(self):
        absolute_path = filedialog.askopenfilename(filetypes = [("CSV", ".csv"), ("TXT", ".txt"), ("ALL", "*.*")])
        if absolute_path == "":
            return
        self.absolute_path = absolute_path
        # 重置所有输入框的值，锁定所有输入框
        self.stringvars_start_end()
        self.entry_start1.config(textvariable = self.start1, state = "disabled")
        self.entry_end1.config(textvariable = self.end1, state = "disabled")
        self.entry_start2.config(textvariable = self.start2, state = "disabled")
        self.entry_end2.config(textvariable = self.end2, state = "disabled")
        if self.mode.get() == "combustion":
            self.stringvars_combustion()
            try:
                self.constant.set(self.parameters_combustion[-2])
                self.entry_constant.config(textvariable = self.constant)
            except:
                pass
            self.entries_combustion(state = "disabled")
        elif self.mode.get() == "dissolution":
            self.entry_start3.config(textvariable = self.start3, state = "disabled")
            self.entry_end3.config(textvariable = self.end3, state = "disabled")
            self.stringvars_dissolution()
            self.entries_dissolution(state = "disabled")
        # 锁定除file之外的所有button
        self.button_save.config(state = "disabled")
        self.button_remake.config(state = "disabled")
        self.button_integrate.config(state = "disabled")
        # 读取文件
        self.file_name, self.extension = self.file_name_extension(self.absolute_path)
        self.csv = np.loadtxt(self.absolute_path, delimiter = ",", skiprows = 1)
        # 将csv中的数据按时间排序
        self.csv_time = self.csv[:, 0]
        self.csv_time = np.argsort(self.csv_time)
        self.csv = self.csv[self.csv_time]
        self.len_csv = len(self.csv)
        # 将csv中的数据加载到treeview_csv中，如果是溶解热数据则找出第三列为1和2的标志点并更新entry
        self.text_result.config(state = "normal")
        self.text_result.delete(1.0, "end")
        self.text_result.config(state = "disabled")
        self.treeview_csv.delete(*self.treeview_csv.get_children())
        for i in range(self.len_csv):
            self.treeview_csv.insert("", i, values = (i, f"{self.csv[i][0]:.3f}", f"{self.csv[i][1]:.3f}"))
            if self.mode.get() == "dissolution":
                try:
                    if self.csv[i][2] == 1:
                        self.t1.set(str(self.csv[i][0]))
                        self.t1_memory = self.t1.get()
                    elif self.csv[i][2] == 2:
                        self.t2.set(str(self.csv[i][0]))
                        self.t2_memory = self.t2.get()
                except:
                    pass
        # 更新文件名
        self.label_path.config(text = self.file_name)
        # 清除图像
        self.f.clear()
        # 计算平滑曲线
        self.smooth = maths.B_Spline(self.csv[:, 0], self.csv[:, 1], self.dx)
        self.x_smooth = np.arange(self.csv[:, 0].min(), self.csv[:, 0].max(), self.dx)
        self.y_smooth = self.smooth(self.x_smooth)
        # 更新输入框范围
        self.remake_file()

    # 重置窗口状态
    def remake_file(self):
        # 更新输入框的值
        self.start_end_points = maths.find_start_end_point(self.csv, self.mode.get(), self.time_lower_limit, self.time_upper_limit, self.std_limit)
        if self.mode.get() == "combustion":
            try:
                self.Start1 = self.start_end_points[0]
                self.End1 = self.start_end_points[1]
                self.Start2 = self.start_end_points[2]
                self.End2 = self.start_end_points[3]
                self.start1.set(str(self.Start1))
                self.end1.set(str(self.End1))
                self.start2.set(str(self.Start2))
                self.end2.set(str(self.End2))
            except:
                self.Start1 = int(self.len_csv * 0.00 / 3.00)
                self.End1 = int(self.len_csv * 1.00 / 3.00)
                self.Start2 = int(self.len_csv * 2.00 / 3.00)
                self.End2 = int(self.len_csv * 3.00 / 3.00 - 1)
                self.start1.set(str(self.Start1))
                self.end1.set(str(self.End1))
                self.start2.set(str(self.Start2))
                self.end2.set(str(self.End2))
            self.entry_start1.config(textvariable = self.start1, state = "normal", from_ = 0, to = self.End1- 1)
            self.entry_end1.config(textvariable = self.end1, state = "normal", from_ = self.Start1 + 1, to = self.Start2 - 1)
            self.entry_start2.config(textvariable = self.start2, state = "normal", from_ = self.End1 + 1, to = self.End2 - 1)
            self.entry_end2.config(textvariable = self.end2, state = "normal", from_ = self.Start2 + 1, to = self.len_csv - 1)
            self.entries_combustion(state = "normal")
            self.radiobutton_constant.config(state = "normal")
            self.radiobutton_combustible.config(state = "normal")
            '''
            # 三种测量模式
            # 若修改为两种，需要修改self.Frame3_Combustion, self.combustion_mode, self.remake_file, maths.calculate_combustion
            self.radiobutton_liquid.config(state = "normal")
            '''
            if self.radiobutton_mode_selected.get() == "constant":
                self.entry_constant.config(state = "readonly")
                self.entry_combustion_heat.config(state = "disabled")
            else:
                self.entry_combustion_heat.config(state = "readonly")
        elif self.mode.get() == "dissolution":
            try:
                self.Start1 = self.start_end_points[0]
                self.End1 = self.start_end_points[1]
                self.Start2 = self.start_end_points[2]
                self.End2 = self.start_end_points[3]
                self.Start3 = self.start_end_points[4]
                self.End3 = self.start_end_points[5]
                self.start1.set(str(self.Start1))
                self.end1.set(str(self.End1))
                self.start2.set(str(self.Start2))
                self.end2.set(str(self.End2))
                self.start3.set(str(self.Start3))
                self.end3.set(str(self.End3))
            except:
                self.Start1 = int(self.len_csv * 0.00 / 5.00)
                self.End1 = int(self.len_csv * 1.00 / 5.00)
                self.Start2 = int(self.len_csv * 2.00 / 5.00)
                self.End2 = int(self.len_csv * 3.00 / 5.00)
                self.Start3 = int(self.len_csv * 4.00 / 5.00)
                self.End3 = int(self.len_csv * 5.00 / 5.00 - 1)
                self.start1.set(str(self.Start1))
                self.end1.set(str(self.End1))
                self.start2.set(str(self.Start2))
                self.end2.set(str(self.End2))
                self.start3.set(str(self.Start3))
                self.end3.set(str(self.End3))
            self.entry_start1.config(textvariable = self.start1, state = "normal", from_ = 0, to = self.End1 - 1)
            self.entry_end1.config(textvariable = self.end1, state = "normal", from_ = self.Start1 + 1, to = self.Start2 - 1)
            self.entry_start2.config(textvariable = self.start2, state = "normal", from_ = self.End1 + 1, to = self.End2 - 1)
            self.entry_end2.config(textvariable = self.end2, state = "normal", from_ = self.Start2 + 1, to = self.Start3 - 1)
            self.entry_start3.config(textvariable = self.start3, state = "normal", from_ = self.End2 + 1, to = self.End3 - 1)
            self.entry_end3.config(textvariable = self.end3, state = "normal", from_ = self.Start3 + 1, to = self.len_csv - 1)
            self.entry_t1.config(textvariable = self.t1)
            self.entry_t2.config(textvariable = self.t2)
            self.entries_dissolution(state = "normal")
            self.entry_dissolution_heat.config(state = "readonly")
        # 线性回归
        self.calculate_regression()
        # 解锁除file、remake之外的所有button
        self.button_remake.config(state = "normal")
        self.button_integrate.config(state = "normal")

    # 保存文件
    def save_file(self):
        if self.mode.get() == "combustion":
            result_path = self.absolute_path.replace(self.file_name + '.' + self.extension, "combustion.csv")
            # 如果与当前打开的csv文件同目录的文件夹下没有combustion.csv文件
            if not os.path.exists(result_path):
                with open(result_path, mode = "w", encoding = "UTF-8", newline = "") as f:
                    writer = csv.writer(f)
                    writer.writerow(["filename", "Start1", "End 1", "Start 2", "End 2", "T_left(K)", "T_right(K)", \
                                "temperature(K)", "water_volume(mL)", "water_density(g/mL)", "water_capacity(J/gK)", \
                                "combustible_mass(g)", "cotton_mass(g)", "Nickel_before_mass(g)", "Nickel_after_mass(g)", \
                                "benzoic_enthalpy(kJ/mol)", "cotton_heat(J/g)", "Nickel_heat(J/g)", "constant(J/K)", "combustion_heat(J/g)"])
            try:
                with open(result_path, mode = "a", encoding = "UTF-8", newline = "") as f:
                    writer = csv.writer(f)
                    writer.writerow(self.parameters_combustion)
            except PermissionError:
                self.text_result.config(state = "normal")
                self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 保存失败！请关闭{self.mode.get()}.csv文件后再次尝试保存\n")
                self.text_result.config(state = "disabled")
                self.text_result.see("end")                
                showwarning(title = "警告", message = f"保存失败！请关闭{self.mode.get()}.csv文件后再次尝试保存")
                return
        elif self.mode.get() == "dissolution":
            result_path = self.absolute_path.replace(self.file_name + '.' + self.extension, "dissolution.csv")
            # 如果与当前打开的csv文件同目录的文件夹下没有dissolution.csv文件
            if not os.path.exists(result_path):
                with open(result_path, mode = "w", encoding = "UTF-8", newline = "") as f:
                    writer = csv.writer(f)
                    writer.writerow(["filename", "Start1", "End 1", "Start 2", "End 2", "Start 3", "End 3", "T1_left", "T1_right", "T2_left", "T2_right", \
                                "temperature(K)", "water_volume(mL)", "water_density(g/mL)", "water_capacity(J/gK)", \
                                "solute_mass(g)", "solute_molarmass(g/mol)", "R1(Omega)", "R2(Omega)", "t1(s)", "t2(s)", "current(A)", "dissolution_heat(kJ)"])
            try:
                with open(result_path, mode = "a", encoding = "UTF-8", newline = "") as f:
                    writer = csv.writer(f)
                    writer.writerow(self.parameters_dissolution)
            except PermissionError:
                self.text_result.config(state = "normal")
                self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} 保存失败！请关闭{self.mode.get()}.csv文件后再次尝试保存\n")
                self.text_result.config(state = "disabled")
                self.text_result.see("end")
                showwarning(title = "警告", message = f"保存失败！请关闭{self.mode.get()}.csv文件后再次尝试保存")
                return
        self.P.set_size_inches(self.width_height_inches)
        self.P.savefig(fname = self.absolute_path.replace(self.extension, "png"), dpi = self.dpi)
        self.button_save.config(state = "disabled")
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {self.mode.get()}.csv文件保存成功\n")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {self.file_name}.png保存成功\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        showinfo(title = "提示", message = f"保存成功！\n{self.file_name}.png保存至{self.absolute_path.replace(self.file_name + '.' + self.extension, '')}\n计算数据保存至同目录下的{self.mode.get()}.csv文件")

    # 起止点输入框判断
    def input_(self):
        # 判断textvariable是否为数字、大小是否合法，否则恢复原值
        #判断是否为数字
        if not self.start1.get().isdigit():
            self.start1.set(str(self.Start1))
        if not self.end1.get().isdigit():
            self.end1.set(str(self.End1))
        if not self.start2.get().isdigit():
            self.start2.set(str(self.Start2))
        if not self.end2.get().isdigit():
            self.end2.set(str(self.End2))
        if self.mode.get() == "dissolution":
            if not self.start3.get().isdigit():
                self.start3.set(str(self.Start3))
            if not self.end3.get().isdigit():
                self.end3.set(str(self.End3))
        # 判断大小是否合法
        if self.mode.get() == "combustion" and not 0 <= int(self.start1.get()) < int(self.end1.get()) < int(self.start2.get()) < int(self.end2.get()) < self.len_csv:
            self.start1.set(str(self.Start1))
            self.end1.set(str(self.End1))
            self.start2.set(str(self.Start2))
            self.end2.set(str(self.End2))
        if self.mode.get() == "dissolution" and not 0 <= int(self.start1.get()) < int(self.end1.get()) < int(self.start2.get()) < int(self.end2.get()) < int(self.start3.get()) < int(self.end3.get()) < self.len_csv:
            self.start1.set(str(self.Start1))
            self.end1.set(str(self.End1))
            self.start2.set(str(self.Start2))
            self.end2.set(str(self.End2))
            self.start3.set(str(self.Start3))
            self.end3.set(str(self.End3))
        # 判断值是否改变，如果改变，清空combustion或dissolution的计算结果
        if self.mode.get() == "combustion":
            if self.Start1 != int(self.start1.get()) or self.End1 != int(self.end1.get()) or self.Start2 != int(self.start2.get()) or self.End2 != int(self.end2.get()):
                if self.radiobutton_mode_selected.get() == "constant":
                    self.constant.set("")
                    self.entry_constant.config(textvariable = self.constant)
                elif self.radiobutton_mode_selected.get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                    self.combustion_heat.set("")
                    self.entry_combustion_heat.config(textvariable = self.combustion_heat)
        elif self.mode.get() == "dissolution":
            if self.Start1 != int(self.start1.get()) or self.End1 != int(self.end1.get()) or self.Start2 != int(self.start2.get()) or self.End2 != int(self.end2.get()) or self.Start3 != int(self.start3.get()) or self.End3 != int(self.end3.get()):
                self.dissolution_heat.set("")
                self.entry_dissolution_heat.config(textvariable = self.dissolution_heat)
        # 更新存储的数值和输入框范围
        self.Start1 = int(self.start1.get())
        self.End1 = int(self.end1.get())
        self.Start2 = int(self.start2.get())
        self.End2 = int(self.end2.get())
        self.entry_start1.config(from_ = 0, to = self.End1 - 1)
        self.entry_end1.config(from_ = self.Start1 + 1, to = self.Start2 - 1)
        self.entry_start2.config(from_ = self.End1 + 1, to = self.End2 - 1)
        self.entry_end2.config(from_ = self.Start2 + 1, to = self.len_csv - 1)
        if self.mode.get() == "dissolution":
            self.Start3 = int(self.start3.get())
            self.End3 = int(self.end3.get())
            self.entry_end2.config(from_ = self.Start2 + 1, to = self.Start3 - 1)
            self.entry_start3.config(from_ = self.End2 + 1, to = self.End3 - 1)
            self.entry_end3.config(from_ = self.Start3 + 1, to = self.len_csv - 1)
        # 重新计算回归直线
        self.calculate_regression()

    # 绘图
    def plot_(self, code: str):
        # 清空图像
        self.f.clear()
        self.f.set_xlabel("$t$ (s)")
        self.f.set_ylabel("$\Delta T$ (K)")
        # 绘制起止点和散点图
        self.f.scatter(self.csv[:, 0], self.csv[:, 1], s = 5, color = "dimgray", label = "$\Delta T$ - $t$ data")
        self.f.scatter(self.csv[self.Start1, 0], self.csv[self.Start1, 1], s = 15, color = 'darkorange', label = "linear fit 1 endpoints")
        self.f.scatter(self.csv[self.End1, 0], self.csv[self.End1, 1], s = 15, color = 'darkorange')
        self.f.scatter(self.csv[self.Start2, 0], self.csv[self.Start2, 1], s = 15, color = 'limegreen', label = "linear fit 2 endpoints")
        self.f.scatter(self.csv[self.End2, 0], self.csv[self.End2, 1], s = 15, color = 'limegreen')
        if self.mode.get() == "dissolution":
            self.f.scatter(self.csv[self.Start3, 0], self.csv[self.Start3, 1], s = 15, color = 'violet', label = "linear fit 3 endpoints")
            self.f.scatter(self.csv[self.End3, 0], self.csv[self.End3, 1], s = 15, color = 'violet')
            try:
                t1_temperature = self.smooth(float(self.t1.get()))
                t2_temperature = self.smooth(float(self.t2.get()))
                self.f.scatter(float(self.t1.get()), float(t1_temperature), s = 15, color = 'red', label = "heating endpoints")
                self.f.scatter(float(self.t2.get()), float(t2_temperature), s = 15, color = 'red')
            except:
                pass
        # 绘制平滑曲线
        self.f.plot(self.x_smooth, self.y_smooth, linewidth = 1, color = '#1F77B4', label = "$\Delta T$ - $t$ curve")
        # 绘制线性回归
        self.y1 = self.k1 * self.x_smooth + self.b1
        self.y2 = self.k2 * self.x_smooth + self.b2
        self.f.plot(self.x_smooth, self.y1, ls = "--", linewidth = 1, color = 'darkorange', label = "linear fit 1")
        self.f.plot(self.x_smooth, self.y2, ls = "--", linewidth = 1, color = 'limegreen', label = "linear fit 2")
        if self.mode.get() == "dissolution":
            self.y3 = self.k3 * self.x_smooth + self.b3
            self.f.plot(self.x_smooth, self.y3, ls = "--", linewidth = 1, color = 'violet', label = "linear fit 3")
        # 绘制积分面积
        if code == "integration":
            # 绘制分界线
            T1_small, T1_big = [self.T1_right, self.T1_left] if self.T1_left > self.T1_right else [self.T1_left, self.T1_right]
            Delta_T1 = T1_big - T1_small
            T1_y = np.arange(T1_small - Delta_T1 * 0.1, T1_big + Delta_T1 * 0.1, self.dx)
            T1_x = np.full(len(T1_y), self.x1)
            if self.mode.get() == "combustion":
                self.f.plot(T1_x, T1_y, ls = "--", color = 'red', linewidth = 1, label = "Reynolds auxiliary line")
            elif self.mode.get() == "dissolution":
                T2_small, T2_big = [self.T2_right, self.T2_left] if self.T2_left > self.T2_right else [self.T2_left, self.T2_right]
                Delta_T2 = T2_big - T2_small
                T2_y = np.arange(T2_small - Delta_T2 * 0.1, T2_big + Delta_T2 * 0.1, self.dx)
                T2_x = np.full(len(T2_y), self.x2)
                self.f.plot(T1_x, T1_y, ls = "--", color = 'red', linewidth = 1)
                self.f.plot(T2_x, T2_y, ls = "--", color = 'red', linewidth = 1, label = "Reynolds auxiliary line")
            # 绘制积分面积
            T1_x_area_left = np.arange(self.csv[self.End1, 0], self.x1, self.dx)
            T1_x_area_right = np.arange(self.x1, self.csv[self.Start2, 0], self.dx)
            T1_y_area_left_linear = self.k1 * T1_x_area_left + self.b1
            T1_y_area_right_linear = self.k2 * T1_x_area_right + self.b2
            T1_y_area_left_smooth = self.smooth(T1_x_area_left)
            T1_y_area_right_smooth = self.smooth(T1_x_area_right)
            self.f.fill_between(T1_x_area_left, T1_y_area_left_linear, T1_y_area_left_smooth, color = 'dimgray', alpha = 0.2)
            self.f.fill_between(T1_x_area_right, T1_y_area_right_linear, T1_y_area_right_smooth, color = 'dimgray', alpha = 0.2)
            if self.mode.get() == "dissolution":
                T2_x_area_left = np.arange(self.csv[self.End2, 0], self.x2, self.dx)
                T2_x_area_right = np.arange(self.x2, self.csv[self.Start3, 0], self.dx)
                T2_y_area_left_linear = self.k2 * T2_x_area_left + self.b2
                T2_y_area_right_linear = self.k3 * T2_x_area_right + self.b3
                T2_y_area_left_smooth = self.smooth(T2_x_area_left)
                T2_y_area_right_smooth = self.smooth(T2_x_area_right)
                self.f.fill_between(T2_x_area_left, T2_y_area_left_linear, T2_y_area_left_smooth, color = 'dimgray', alpha = 0.2)
                self.f.fill_between(T2_x_area_right, T2_y_area_right_linear, T2_y_area_right_smooth, color = 'dimgray', alpha = 0.2)
        # 绘图设置
        self.f.legend()
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        self.canvas_plot.configure(image = tk_image)
        self.canvas_plot.image = tk_image

    # 计算线性回归
    def calculate_regression(self):
        # 判断csv是否已读入
        #if str(type(self.csv)) == "<class 'NoneType'>":
        #    return
        # 线性回归
        self.k1, self.b1, self.stddev_k1, self.stddev_b1, self.r_square1 = maths.linear_regression(self.csv, self.Start1, self.End1)
        self.k2, self.b2, self.stddev_k2, self.stddev_b2, self.r_square2 = maths.linear_regression(self.csv, self.Start2, self.End2)
        if self.mode.get() == "dissolution":
            self.k3, self.b3, self.stddev_k3, self.stddev_b3, self.r_square3 = maths.linear_regression(self.csv, self.Start3, self.End3)
        # 更新text_result
        self.text_result.config(state = "normal")
        self.text_result.delete(1.0, "end")
        self.text_result.insert("end", f"Linear Fit 1: Delta_T/K = ({self.k1:.6} ± {self.stddev_k1:.3}) t/s + ({self.b1:.6} ± {self.stddev_b1:.3}), r-square = {self.r_square1:.9f}\n")
        self.text_result.insert("end", f"Linear Fit 2: Delta_T/K = ({self.k2:.6} ± {self.stddev_k2:.3}) t/s + ({self.b2:.6} ± {self.stddev_b2:.3}), r-square = {self.r_square2:.9f}\n")
        if self.mode.get() == "dissolution":
            self.text_result.insert("end", f"Linear Fit 3: Delta_T/K = ({self.k3:.6} ± {self.stddev_k3:.3}) t/s + ({self.b3:.6} ± {self.stddev_b3:.3}), r-square = {self.r_square3:.9f}\n")
        self.text_result.config(state = "disabled")
        # 绘图
        self.plot_(code = "regression")

    # 计算校正点
    def calculate_integration(self):
        # 计算校正点
        self.x1, S1_left, S1_right = maths.Reynolds(self.csv, self.Start1, self.End1, self.Start2, self.End2, self.dx)
        self.T1_left = self.k1 * self.x1 + self.b1
        self.T1_right = self.k2 * self.x1 + self.b2
        if self.mode.get() == "dissolution":
            self.x2, S2_left, S2_right = maths.Reynolds(self.csv, self.Start2, self.End2, self.Start3, self.End3, self.dx)
            self.T2_left = self.k2 * self.x2 + self.b2
            self.T2_right = self.k3 * self.x2 + self.b3
        # 绘图
        self.plot_(code = "integration")
        # 计算燃烧热
        if self.mode.get() == "combustion":
            # 加载参数
            self.parameters_combustion = [f"{self.file_name}.{self.extension}", self.Start1, self.End1, self.Start2, self.End2, self.T1_left, self.T1_right, \
                               self.temperature.get(), self.water_volume.get(), self.water_density.get(), self.water_capacity.get(), \
                                self.combustible_mass.get(), self.cotton_mass.get(), self.Nickel_before_mass.get(), self.Nickel_after_mass.get(), \
                                    self.benzoic_enthalpy.get(), self.cotton_heat.get(), self.Nickel_heat.get(), self.constant.get(), self.combustion_heat.get()]
            self.parameters_combustion = maths.calculate_combustion(self.parameters_combustion, self.radiobutton_mode_selected.get())
            # 更新计算结果
            if self.radiobutton_mode_selected.get() == "constant":
                self.constant.set(self.parameters_combustion[-2])
                self.entry_constant.config(textvariable = self.constant)
            elif self.radiobutton_mode_selected.get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                self.combustion_heat.set(self.parameters_combustion[-1])
                self.entry_combustion_heat.config(textvariable = self.combustion_heat)
        # 计算溶解热
        elif self.mode.get() == "dissolution":
            # 加载参数
            self.parameters_dissolution = [f"{self.file_name}.{self.extension}", self.Start1, self.End1, self.Start2, self.End2, self.Start3, self.End3, self.T1_left, self.T1_right, self.T2_left, self.T2_right, \
                               self.temperature.get(), self.water_volume.get(), self.water_density.get(), self.water_capacity.get(), \
                                self.solute_mass.get(), self.solute_molarmass.get(), self.R1.get(), self.R2.get(), self.t1.get(), self.t2.get(), self.current.get(), self.dissolution_heat.get()]
            self.parameters_dissolution = maths.calculate_dissolution(self.parameters_dissolution)
            # 更新计算结果
            self.dissolution_heat.set(self.parameters_dissolution[-1])
            self.entry_dissolution_heat.config(textvariable = self.dissolution_heat)
        # 更新text_result
        self.text_result.config(state = "normal")
        self.text_result.delete(1.0, "end")
        self.text_result.insert("end", f"Linear Fit 1: Delta_T/K = ({self.k1:.6} ± {self.stddev_k1:.3}) t/s + ({self.b1:.6} ± {self.stddev_b1:.3}), r-square = {self.r_square1:.9f}\n")
        self.text_result.insert("end", f"Linear Fit 2: Delta_T/K = ({self.k2:.6} ± {self.stddev_k2:.3}) t/s + ({self.b2:.6} ± {self.stddev_b2:.3}), r-square = {self.r_square2:.9f}\n")
        if self.mode.get() == "dissolution":
            self.text_result.insert("end", f"Linear Fit 3: Delta_T/K = ({self.k3:.6} ± {self.stddev_k3:.3}) t/s + ({self.b3:.6} ± {self.stddev_b3:.3}), r-square = {self.r_square3:.9f}\n")
        if self.mode.get() == "combustion":
            self.text_result.insert("end", f"x0 = {self.x1:.2f}\n")
            self.text_result.insert("end", f"S_left = {S1_left:.2f}  S_right = {S1_right:.2f}\n")
            self.text_result.insert("end", f"T_left = {self.T1_left:.3f} K  T_right = {self.T1_right:.3f} K\n")
        elif self.mode.get() == "dissolution":
            self.text_result.insert("end", f"x1 = {self.x1:.2f}, x2 = {self.x2:.2f}\n")
            self.text_result.insert("end", f"S1_left = {S1_left:.2f}  S1_right = {S1_right:.2f}  S2_left = {S2_left:.2f}  S2_right = {S2_right:.2f}\n")
            self.text_result.insert("end", f"T1_left = {self.T1_left:.3f} K  T1_right = {self.T1_right:.3f} K  T2_left = {self.T2_left:.3f} K  T2_right = {self.T2_right:.3f} K\n")
        self.text_result.config(state = "disabled")
        # 设置save为可用
        self.button_save.config(state = "normal")

    # 为spinbox绑定回车键
    def bind_return(self, event):
        if event == "start1":
            self.entry_start1.bind("<Return>", lambda event: self.input_())
        elif event == "end1":
            self.entry_end1.bind("<Return>", lambda event: self.input_())
        elif event == "start2":
            self.entry_start2.bind("<Return>", lambda event: self.input_())
        elif event == "end2":
            self.entry_end2.bind("<Return>", lambda event: self.input_())
        elif event == "start3":
            self.entry_start3.bind("<Return>", lambda event: self.input_())
        elif event == "end3":
            self.entry_end3.bind("<Return>", lambda event: self.input_())

    # 为spinbox解除回车键绑定
    def unbind_return(self, event):
        if event == "start1":
            self.entry_start1.unbind("<Return>")
        if event == "end1":
            self.entry_end1.unbind("<Return>")
        if event == "start2":
            self.entry_start2.unbind("<Return>")
        if event == "end2":
            self.entry_end2.unbind("<Return>")
        if event == "start3":
            self.entry_start3.unbind("<Return>")
        if event == "end3":
            self.entry_end3.unbind("<Return>")
        self.input_()

    # 检查输入参数是否合法
    def check_memory(self, event):
        # 判断是否为数字
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        # 检查输入是否为数字，若不是则恢复上一次的输入
        def _check_memory(memory: str, realtime: StringVar):
            # 只保留数字、小数点和负号
            realtime.set(re.sub(r"[^\d.-]+", "", realtime.get()))
            # 若输入与原先不同
            if realtime.get() != memory:
                # 若输入不是数字，则恢复上一次的输入
                if not is_number(realtime.get()):
                    realtime.set(memory)
                # 若输入是数字，则更新记忆
                else:
                    memory = realtime.get()
                # 清除已计算的值
                if self.mode.get() == "dissolution":
                    self.dissolution_heat.set("")
                    self.entry_dissolution_heat.config(textvariable = self.dissolution_heat)
                elif self.mode.get() == "combustion":
                    if self.radiobutton_mode_selected.get() == "constant":
                        self.constant.set("")
                        self.entry_constant.config(textvariable = self.constant)
                    elif self.radiobutton_mode_selected.get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                        self.combustion_heat.set("")
                        self.entry_combustion_heat.config(textvariable = self.combustion_heat)
                self.plot_(code = "regression")
            return memory
        # 每次检查所有输入框
        self.temperature_memory = _check_memory(self.temperature_memory, self.temperature)
        self.water_volume_memory = _check_memory(self.water_volume_memory, self.water_volume)
        self.water_density_memory = _check_memory(self.water_density_memory, self.water_density)
        self.water_capacity_memory = _check_memory(self.water_capacity_memory, self.water_capacity)
        if self.mode.get() == "dissolution":
            self.solute_mass_memory = _check_memory(self.solute_mass_memory, self.solute_mass)
            self.solute_molarmass_memory = _check_memory(self.solute_molarmass_memory, self.solute_molarmass)
            self.R1_memory = _check_memory(self.R1_memory, self.R1)
            self.R2_memory = _check_memory(self.R2_memory, self.R2)
            self.t1_memory = _check_memory(self.t1_memory, self.t1)
            self.t2_memory = _check_memory(self.t2_memory, self.t2)
            self.current_memory = _check_memory(self.current_memory, self.current)
        elif self.mode.get() == "combustion":
            self.combustible_mass_memory = _check_memory(self.combustible_mass_memory, self.combustible_mass)
            self.cotton_mass_memory = _check_memory(self.cotton_mass_memory, self.cotton_mass)
            self.Nickel_before_mass_memory = _check_memory(self.Nickel_before_mass_memory, self.Nickel_before_mass)
            self.Nickel_after_mass_memory = _check_memory(self.Nickel_after_mass_memory, self.Nickel_after_mass)
            self.benzoic_enthalpy_memory = _check_memory(self.benzoic_enthalpy_memory, self.benzoic_enthalpy)
            self.cotton_heat_memory = _check_memory(self.cotton_heat_memory, self.cotton_heat)
            self.Nickel_heat_memory = _check_memory(self.Nickel_heat_memory, self.Nickel_heat)
            if self.radiobutton_mode_selected.get() == "combustible" or self.radiobutton_mode_selected.get() == "liquid":
                self.constant_memory = _check_memory(self.constant_memory, self.constant)
        # 如果更改的是温度，更新水的密度和热容
        if event == "temperature":
            temperature = "{:.2f}".format(float(self.temperature.get()))
            try:
                self.water_density.set(water_density_smooth[temperature])
            except:
                pass
            try:
                self.water_capacity.set(water_capacity_smooth[temperature])
            except:
                pass
            '''
            try:
                water_density_smooth = np.loadtxt(os.path.dirname(os.path.abspath(__file__)) + "/water_density_smooth.dat", dtype = str)
                for i in range(len(water_density_smooth)):
                    if temperature == water_density_smooth[i][0]:
                        self.water_density.set(water_density_smooth[i][1])
                        break
            except:
                # 缺失水密度数据
                pass
            try:
                water_capacity_smooth = np.loadtxt(os.path.dirname(os.path.abspath(__file__)) + "/water_capacity_smooth.dat", dtype = str)
                for i in range(len(water_capacity_smooth)):
                    if temperature == water_capacity_smooth[i][0]:
                        self.water_capacity.set(water_capacity_smooth[i][1])
                        break
            except:
                # 缺失水热容数据
                pass
            '''

    # 选择燃烧热计算模式
    def combustion_mode(self):
        if self.radiobutton_mode_selected.get() == "constant":
            # 清空燃烧热计算结果，禁止编辑量热计常数和燃烧热
            self.combustion_heat.set("")
            self.entry_constant.config(state = "readonly")
            self.entry_combustion_heat.config(textvariable = self.combustion_heat, state = "disabled")
            # 更新label
            self.label_combustible_mass.config(text = "苯甲酸+棉线(g)")
            # 更新提示
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 当前选择量热计常数模式\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")
        # 两种测量模式
        # 若修改为三种，需要修改self.Frame3_Combustion, self.combustion_mode, maths.calculate_combustion        
        elif self.radiobutton_mode_selected.get() == "combustible":
            # 清空燃烧热计算结果，禁止编辑燃烧热，允许编辑量热计常数
            self.combustion_heat.set("")
            self.entry_constant.config(state = "normal")
            self.entry_combustion_heat.config(textvariable = self.combustion_heat, state = "readonly")
            # 更新label
            self.label_combustible_mass.config(text = "样品+棉线(g)")
            # 更新提示
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 当前选择样品燃烧热模式\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")
            '''
        # 三种测量模式
        # 若修改为两种，需要修改self.Frame3_Combustion, self.combustion_mode, self.remake_file, maths.calculate_combustion
        elif self.radiobutton_mode_selected.get() == "combustible":
            # 清空燃烧热计算结果，禁止编辑燃烧热，允许编辑量热计常数
            self.combustion_heat.set("")
            self.entry_constant.config(state = "normal")
            self.entry_combustion_heat.config(textvariable = self.combustion_heat, state = "readonly")
            # 更新label
            self.label_combustible_mass.config(text = "固体+棉线(g)")
            # 更新提示
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 当前选择固体燃烧热模式\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")
            '''
        elif self.radiobutton_mode_selected.get() == "liquid":
            # 清空燃烧热计算结果，禁止编辑燃烧热，允许编辑量热计常数
            self.combustion_heat.set("")
            self.entry_constant.config(state = "normal")
            self.entry_combustion_heat.config(textvariable = self.combustion_heat, state = "readonly")
            # 更新label
            self.label_combustible_mass.config(text = "食用油(g)")
            self.text_result.config(state = "normal")
            self.text_result.insert("end", f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 当前选择液体燃烧热模式\n")
            self.text_result.config(state = "disabled")
            self.text_result.see("end")

    '''
    以下为溶解热拟合模式的控制函数
    '''
    # 打开溶解热数据文件dissolution.csv
    def open_dissolution_file(self):
        absolute_path = filedialog.askopenfilename(filetypes = [("CSV", ".csv"), ("TXT", ".txt"), ("ALL", "*.*")])
        if absolute_path == "":
            return
        self.absolute_path = absolute_path
        self.button_save.config(state = "disabled")
        # 更新text_result
        self.text_result.config(state = "normal")
        self.text_result.delete("1.0", "end")
        self.text_result.insert("end", "使用说明\n")
        self.text_result.insert("end", "1. 点击文件(.csv)导入文件，默认文件名为dissolution.csv。\n")
        self.text_result.insert("end", "2. 导入的csv文件由本程序的溶解热模式生成。文件第一行为标题行，此后每一行必须按照实际实验顺序排列，且只能出现一次。如格式有误请自行编辑。\n")
        self.text_result.insert("end", "3. 拟合方程为Qs = Qs0 × a × n / (1 + a × n)。\n")
        self.text_result.insert("end", "4. 点击保存(.png)保存图片。\n\n")
        self.text_result.config(state = "disabled")
        self.file_name, self.extension = self.file_name_extension(self.absolute_path)
        dissolution_csv = np.loadtxt(self.absolute_path, delimiter = ",", skiprows = 1, usecols = (12, 13, 15, 16, 22))
        len_csv = len(dissolution_csv)
        '''
        csv文件的一行有如下数据
        "filename", "Start1", "End 1", "Start 2", "End 2", "Start 3", "End 3", "T1_left", "T1_right", "T2_left", "T2_right", \
        "temperature(K)", "water_volume(mL)", "water_density(g/mL)", "water_capacity(J/gK)", \
        "solute_mass(g)", "solute_molarmass(g/mol)", "R1(Ω)", "R2(Ω)", "t1(s)", "t2(s)", "current(A)", "dissolution_heat(kJ)
        需要提取的数据有每一行的：
        water_volume(mL), water_density(g/mL), solute_mass(g), solute_molarmass(g/mol), dissolution_heat(kJ)
        即从0开始编号的12、13、15、16、22列
        '''
        dissolution_parameters = []
        for i in range(len_csv):
            dissolution_parameters.append([dissolution_csv[i][0], dissolution_csv[i][1], dissolution_csv[i][2], dissolution_csv[i][3], dissolution_csv[i][4]])
        Qs, n, Qs0, a, stddev_Qs0, stddev_a, r_square = maths.dissolution_heat_regression(dissolution_parameters)
        # 更新treeview_csv
        self.treeview_csv.delete(*self.treeview_csv.get_children())
        for i in range(len_csv):
            self.treeview_csv.insert("", i, values = (i, f"{n[i]:.4g}", f"{Qs[i]:.2f}"))
        # 更新绘图
        self.f.clear()
        self.f.scatter(n, Qs, s = 50, marker = '+', color = 'dimgray', label = "$Q_s$-$n$ data points")
        n_plot = np.arange(0, max(n) * 1.2, self.dx)
        Qs_plot = (Qs0 * a * n_plot) / (1 + a * n_plot)
        self.f.plot(n_plot, Qs_plot, color = '#1F77B4', label = "fitted curve")
        self.f.set_xlabel("$n$")
        self.f.set_ylabel("$Q_s$ (kJ/mol)")
        self.f.legend()
        self.canvas.draw()
        PIL_image = pilImage.frombytes("RGB", self.canvas.get_width_height(), self.canvas.tostring_rgb())
        tk_image = ImageTk.PhotoImage(PIL_image)
        self.canvas_plot.configure(image = tk_image)
        self.canvas_plot.image = tk_image
        # 更新text_result
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"拟合结果\n")
        self.text_result.insert("end", f"Qs0 = {Qs0:.6} ± {stddev_Qs0:.3} (kJ/mol)    a = {a:.6} ± {stddev_a:.3}\n")
        self.text_result.insert("end", f"Qs (kJ/mol) = {Qs0:.6} × {a:.6} × n / (1 + {a:.6} × n), r_square = {r_square:.9f}\n\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        # 更新文件名
        self.label_path.config(text = self.file_name)
        # 更新button_save
        self.button_save.config(state = "normal")

    # 保存溶解热拟合模式的绘图
    def save_dissolution_file(self):
        self.P.set_size_inches(self.width_height_inches)
        self.P.savefig(fname = self.absolute_path.replace(self.extension, "png"), dpi = self.dpi)
        self.text_result.config(state = "normal")
        self.text_result.insert("end", f"{time.strftime('%Y.%m.%d %H:%M:%S', time.localtime())} {self.file_name}.png保存成功\n")
        self.text_result.config(state = "disabled")
        self.text_result.see("end")
        showinfo(title = "提示", message = f"保存成功！\n{self.file_name}.png保存至{self.absolute_path.replace(self.file_name + '.' + self.extension, '')}")
