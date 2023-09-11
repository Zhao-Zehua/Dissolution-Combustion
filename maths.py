# Author: 赵泽华
# 第三方库
import numpy as np
from scipy import optimize
from scipy.interpolate import BSpline, splrep

# 线性回归
# 使用scipy
def linear_regression(csv, Start: int, End: int):
    def equation(x, k, b):
        return k * x + b
    End += 1    # 植树问题，输入的起止点为闭区间
    N = End - Start # 散点总数
    x = csv[Start : End, 0] # 获取散点横坐标，左闭右开
    y = csv[Start : End, 1] # 获取散点纵坐标，左闭右开
    popt, pcov = optimize.curve_fit(equation, x, y)    # popt为最优拟合参数，pcov为拟合参数的协方差矩阵
    perr = np.sqrt(np.diag(pcov))   # perr为拟合参数的标准差
    k, b = popt
    stddev_k, stddev_b = perr
    # 计算拟合曲线的R平方
    residuals = y - equation(x, *popt)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_square = 1 - (ss_res / ss_tot)
    return k, b, stddev_k, stddev_b, r_square

'''
# 线性回归
# 由数学定义计算
def linear_regression(csv, Start: int, End: int):
    End += 1    # 植树问题，输入的起止点为闭区间
    N = End - Start # 散点总数
    x = csv[Start : End, 0] # 获取散点横坐标，左闭右开
    y = csv[Start : End, 1] # 获取散点纵坐标，左闭右开
    k = (np.sum(x * y) - np.sum(x) * np.sum(y) / N) / (np.sum(np.power(x, 2)) - (np.sum(x)) ** 2 / N)   # 回归直线的斜率
    b = (np.sum(y) - k * np.sum(x)) / N # 回归直线的截距
    Sxx = np.sum(np.power(x, 2)) - np.sum(x) ** 2 / N # x的总离差平方和
    Syy = np.sum(np.power(y, 2)) - np.sum(y) ** 2 / N   # y的总离差平方和
    sr = np.sqrt((Syy - k ** 2 * Sxx) / (N - 2))  # 回归标准差
    stddev_k = np.sqrt(sr ** 2 / Sxx) # 斜率标准差
    stddev_b = sr * np.sqrt(1 / (N - np.sum(x) ** 2 / np.sum(np.power(x, 2))))    # 截距标准差
    r_square = np.sum(np.power((x * k + b - np.mean(y)), 2)) / Syy  # r^2
    return k, b, stddev_k, stddev_b, r_square
'''

# 定积分
def integration(x, y, k, b, dx):
    dS = abs((y - k * x - b) * dx - k * dx * dx * 0.5)  # 定积分，得到绝对面积
    return dS   # 返回积分结果

# B-样条平滑曲线
def B_Spline(x, y, dx): # 平滑步长dx
    # 计算B-样条的节点和系数
    t, c, k = splrep(x, y)
    # 创建平滑函数
    smooth = BSpline(t, c, k)
    return smooth   # 返回平滑函数

# 雷诺校正点
def Reynolds(csv, Start1: int, End1: int, Start2: int, End2: int, dx: float):  # 积分步长dx
    # 依据起止点进行线性回归
    k1, b1 = linear_regression(csv, Start1, End1)[0 : 2]
    k2, b2 = linear_regression(csv, Start2, End2)[0 : 2]
    # 平滑曲线拟合
    x_csv = csv[End1 : (Start2 + 1), 0] # 读取横坐标，类型为array
    y_csv = csv[End1 : (Start2 + 1), 1] # 读取纵坐标，类型为array
    smooth = B_Spline(x_csv, y_csv, dx) # 创建平滑函数
    x_smooth = np.arange(x_csv.min(), x_csv.max(), dx)  # 生成平滑曲线横坐标
    y_smooth = smooth(x_smooth) # 根据平滑函数生成平滑曲线纵坐标
    len_smooth = x_smooth.size  # 获取平滑曲线总散点数
    # 计算定积分
    S = [[], []]    # 两条回归直线与平滑曲线的定积分，分别以dx为步长，储存在前后两个list中
    for i in range(len_smooth):
        S[0].append(integration(x_smooth[i], y_smooth[i], k1, b1, dx))  # 以dx为步长计算第一条回归直线的定积分，存储在S[0]中
        S[1].append(integration(x_smooth[i], y_smooth[i], k2, b2, dx))  # 以dx为步长计算第二条回归直线的定积分，存储在S[1]中
    # 搜索使得两侧积分面积相等的点
    S1, S2 = 0, sum(S[1])   # 初始化两侧积分面积
    equal_point = 0
    for i in range(len_smooth):
        S1 += S[0][i]
        S2 -= S[1][i]
        if S1 >= S2:
            equal_point = i
            break
    x0 = x_smooth[equal_point]  # 获取雷诺校正点横坐标
    return x0, S1, S2

# 溶解热计算
def calculate_dissolution(parameters: dict):
    '''
    从图形界面获取参数
    parameters = [file_name_extension, Start1, End1, Start2, End2, Start3, End3, T1_left, T1_right, T2_left, T2_right, temperature, water_volume, water_density, water_capacity, solute_mass, solute_molarmass, R1, R2, t1, t2, current, dissolution_heat]
    '''
    # 获取参数
    try:
        T1_left = float(parameters["T1_left"])
        T1_right = float(parameters["T1_right"])
        T2_left = float(parameters["T2_left"])
        T2_right = float(parameters["T2_right"])
        R1 = float(parameters["R1(Omega)"])
        R2 = float(parameters["R2(Omega)"])
        t1 = float(parameters["t1(s)"])
        t2 = float(parameters["t2(s)"])
        current = float(parameters["current(A)"])
    except ValueError:
        pass
    # 计算溶解热
    R = (R1 + R2) / 2
    t = t2 - t1
    Q = current ** 2 * R * t
    dissolution_heat = Q * (T1_left - T1_right) / (T2_right - T2_left) / 1000   # 单位：kJ
    parameters["dissolution_heat(kJ)"] = f"{dissolution_heat:.4f}"
    return parameters

# 溶解热回归
def dissolution_heat_regression(dissolution_csv):
    '''
    从图形界面获取参数
    dissolution_csv = [[water_volume, water_density, solute_mass, solute_molarmass, dissolution_heat], ...]

    需要计算的是水的物质的量n1、溶质的逐级物质的量sum_n2、物质的量浓度n、逐级溶解热sum_Q、积分溶解热Qs
    公式：
    n1 = ρV / 18.015
    n = n1 / sum_n2
    Qs = sum_Q / sum_n2
    '''
    # 积分溶解热
    def equation(n, Qs0, a):
        return (Qs0 * a * n) / (1 + a * n)
    n = []
    Qs = []
    sum_n2 = 0
    sum_Q = 0
    water_volume = float(dissolution_csv[0][0])
    water_density = float(dissolution_csv[0][1])
    water_molarmass = 18.015
    n1 = water_density * water_volume / water_molarmass
    for i in range(len(dissolution_csv)):
        solute_mass = float(dissolution_csv[i][2])
        solute_molarmass = float(dissolution_csv[i][3])
        sum_n2 += solute_mass / solute_molarmass
        Q = float(dissolution_csv[i][4])
        sum_Q += Q
        n.append(n1 / sum_n2)
        Qs.append(sum_Q / sum_n2)
    # 使用线性拟合确定初值
    n_p0 = np.array(np.copy(n))
    Qs_p0 = np.array(np.copy(Qs))
    n_p0 = 1 / n_p0
    Qs_p0 = 1 / Qs_p0
    Start, End = 0, len(n) - 1
    csv = np.stack((n_p0, Qs_p0), axis = 1)
    k, b, stddev_k, stddev_b, r_square_p0 = linear_regression(csv, Start, End)
    p0 = [1 / b, b / k]
    # 使用scipy非线性拟合确定最优拟合参数
    popt, pcov = optimize.curve_fit(equation, n, Qs, p0 = p0)    # popt为最优拟合参数，pcov为拟合参数的协方差矩阵
    perr = np.sqrt(np.diag(pcov))   # perr为拟合参数的标准差
    Qs0, a = popt
    stddev_Qs0, stddev_a = perr
    # 将n和Qs转换为numpy的array
    n = np.array(n)
    Qs = np.array(Qs)
    # 计算拟合曲线的R平方
    residuals = Qs - equation(n, *popt)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((Qs - np.mean(Qs)) ** 2)
    r_square = 1 - (ss_res / ss_tot)
    '''
    # 以下为scipy非线性拟合
    p0 = [30, 0.25]
    if np.abs(solute_molarmass - 74.5) < 1: # 认为是KCl
        p0 = [20, 0.4]
    elif np.abs(solute_molarmass - 101.1) < 1:   # 认为是KNO3
        p0 = [40, 0.1]
    popt, pcov = optimize.curve_fit(equation, n, Qs, p0 = p0)    # popt为最优拟合参数，pcov为拟合参数的协方差矩阵
    perr = np.sqrt(np.diag(pcov))   # perr为拟合参数的标准差
    Qs0, a = popt
    stddev_Qs0, stddev_a = perr
    # 将n和Qs转换为numpy的array
    n = np.array(n)
    Qs = np.array(Qs)
    # 计算拟合曲线的R平方
    residuals = Qs - equation(n, *popt)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((Qs - np.mean(Qs)) ** 2)
    r_square = 1 - (ss_res / ss_tot)
    '''
    '''
    # 以下为线性拟合
    n = np.array(n)
    Qs = np.array(Qs)
    n = 1 / n
    Qs = 1 / Qs
    Start, End = 0, len(n) - 1
    # 将n和Qs合并为二维array，第一列为n，第二列为Qs
    csv = np.stack((n, Qs), axis = 1)
    k, b, stddev_k, stddev_b, r_square = linear_regression(csv, Start, End)
    Qs0 = 1 / b
    a = b / k
    stddev_Qs0 = stddev_b / b ** 2
    stddev_a = np.sqrt((stddev_b / k) ** 2 + (b * stddev_k / (k ** 2)) ** 2)
    '''
    return Qs, n, Qs0, a, stddev_Qs0, stddev_a, r_square

# 积分/微分溶解/冲淡热计算
def dissolution_heat_test(Qs0, a, n_test = [200, 150, 100, 80, 50]):
    n_test = np.array(n_test)
    # 积分溶解热
    Qs_int_dissolution = (Qs0 * a * n_test) / (1 + a * n_test)
    # 积分冲淡热(取绝对值)
    Qs_int_dilution = np.diff(Qs_int_dissolution) * 1000
    # 微分溶解热
    Qs_diff_dissolution = Qs0 * (a * n_test / (1 + a * n_test)) ** 2
    # 微分冲淡热
    Qs_diff_dilution = Qs0 * a * 1000 / (1 + a * n_test) ** 2
    # 数据格式处理
    Qs_int_dissolution = np.round(Qs_int_dissolution, 2)
    Qs_int_dilution = np.round(np.abs(Qs_int_dilution), 2)
    Qs_diff_dissolution = np.round(Qs_diff_dissolution, 2)
    Qs_diff_dilution = np.round(Qs_diff_dilution, 2)
    Qs_int_dilution = np.concatenate((["NA"], Qs_int_dilution), axis = 0)
    '''
    n_test = np.concatenate((["n0"], n_test), axis = 0)
    Qs_int_dissolution = np.concatenate((["int_dissolution(kJ/mol)"], Qs_int_dissolution), axis = 0)
    Qs_int_dilution = np.concatenate((["int_dilution(J/mol)", "NA"], Qs_int_dilution), axis = 0)
    Qs_diff_dissolution = np.concatenate((["diff_dissolution(kJ/mol)"], Qs_diff_dissolution), axis = 0)
    Qs_diff_dilution = np.concatenate((["diff_dilution(J/mol)"], Qs_diff_dilution), axis = 0)
    '''
    # 拼接为表格并格式化
    title = ["n0", "Qs(kJ/mol)", "Qd(J/mol)", "Qs'_n2(kJ/mol)", "Qs'_n0(J/mol)"]
    data = np.stack((n_test, Qs_int_dissolution, Qs_int_dilution, Qs_diff_dissolution, Qs_diff_dilution), axis = 1)
    data = np.vstack((title, data))

    return data

# 燃烧热计算
def calculate_combustion(parameters: dict, code: str):
    '''
    从图形界面获取参数
    parameters = [file_name_extension, Start1, End1, Start2, End2, T_left, T_right, temperature, water_volume, water_density, water_capacity, combustible_mass, cotton_mass, Nickel_before_mass, Nickel_after_mass, benzoic_enthalpy, cotton_heat, Nickel_heat, constant, combustion_heat]
    '''
    # 获取参数
    try:
        T_left = float(parameters["T_left(K)"])
        T_right = float(parameters["T_right(K)"])
        temperature = float(parameters["room_temperature(K)"])
        water_volume = float(parameters["water_volume(mL)"])
        water_density = float(parameters["water_density(g/mL)"])
        water_capacity = float(parameters["water_capacity(J/gK)"])
        combustible_mass = float(parameters["combustible_mass(g)"])
        cotton_mass = float(parameters["cotton_mass(g)"])
        Nickel_before_mass = float(parameters["Nickel_before_mass(g)"])
        Nickel_after_mass = float(parameters["Nickel_after_mass(g)"])
        benzoic_enthalpy = float(parameters["benzoic_enthalpy(kJ/mol)"])
        cotton_heat = float(parameters["cotton_heat(J/g)"])
        Nickel_heat = float(parameters["Nickel_heat(J/g)"])
    except ValueError:
        pass
    # 计算燃烧热
    water_total_capacity = water_volume * water_density * water_capacity    # 单位J/K
    Q_cotton = cotton_mass * cotton_heat    # 单位J
    Q_Nickel = (Nickel_before_mass - Nickel_after_mass) * Nickel_heat    # 单位J
    if code == "constant":  # 计算量热计常数
        benzoic_heat = (benzoic_enthalpy * 1000 + 0.5 * 8.3144621 * temperature) / 122.123  # 将苯甲酸的恒压燃烧热(kJ/mol)转换为恒容燃烧热(J/g)
        Q_benzoic = (combustible_mass - cotton_mass) * benzoic_heat    # 单位J
        Q = Q_cotton + Q_Nickel + Q_benzoic
        constant = -Q / (T_right - T_left) - water_total_capacity
        parameters["constant(J/K)"] = f"{constant:.1f}"
    # 两种测量模式
    # 若修改为三种，需要修改self.Frame3_Combustion, self.combustion_mode, self.remake_file, maths.calculate_combustion
    elif code == "combustible":
        constant = float(parameters["constant(J/K)"])
        Q_x = -Q_Nickel - Q_cotton - (constant + water_total_capacity) * (T_right - T_left)    # 单位J
        combustion_heat = Q_x / (combustible_mass - cotton_mass)    # 单位J/g
        parameters["combustion_heat(J/g)"] = f"{combustion_heat:.1f}"
        '''
    # 三种测量模式
    # 若修改为两种，需要修改self.Frame3_Combustion, self.combustion_mode, self.remake_file, maths.calculate_combustion
    elif code == "combustible":
        constant = float(parameters[18])
        Q_x = -Q_Nickel - Q_cotton - (constant + water_total_capacity) * (T_right - T_left)    # 单位J
        combustion_heat = Q_x / (combustible_mass - cotton_mass)    # 单位J/g
        parameters[-1] = f"{combustion_heat:.1f}"
        '''
    elif code == "liquid":
        constant = float(parameters["constant(J/K)"])
        Q_x = -Q_Nickel - Q_cotton - (constant + water_total_capacity) * (T_right - T_left)    # 单位J
        combustion_heat = Q_x / combustible_mass    # 单位J/g
        parameters["combustion_heat(J/g)"] = f"{combustion_heat:.1f}"

# 寻找初始起止点
def find_start_end_point(csv, code: str, time_lower_limit: int or float, time_upper_limit: int or float, std_limit: float): # 建议时间下限30s，时间上限40s，标准差上限0.01
    # 第一列为index，第二列为标准差
    standard_deviation = []
    points = []
    count = 4 if code == "燃烧热" else 6
    platform = True
    start_index = 0
    end_index = 1
    if csv is None: return 
    while end_index < len(csv):
        time_range = csv[end_index][0] - csv[start_index][0]
        if time_range > time_upper_limit:
            start_index += 1
        elif time_range < time_lower_limit:
            end_index += 1
        else:
            standard_deviation.append([end_index, np.std(csv[start_index:end_index, 1])])
            end_index += 1
    # 寻找起止点
    points.append(0)
    for i in standard_deviation:
        index, std = i
        if std <= std_limit and platform == False:
            points.append(index)
            platform = True
            count -= 1
        elif std > std_limit and platform == True:
            # 排除延后效应的影响
            time_now = csv[index][0]
            while time_now - csv[index][0] < time_lower_limit / 1.0:    # 1.0可调节，越大对延后的校正越弱
                index -= 1
            points.append(index)
            platform = False
            count -= 1
        if count == 2:
            break
    points.append(len(csv) - 1)
    return points
