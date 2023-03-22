import numpy as np
from scipy.interpolate import BSpline, splrep

# 线性回归
def linear_regression(csv, Start: int, End: int):
    End += 1    # 植树问题，输入的起止点为闭区间
    N = End - Start # 散点总数
    x = csv[Start : End, 0] # 获取散点横坐标，左闭右开
    y = csv[Start : End, 1] # 获取散点纵坐标，左闭右开
    k = (np.sum(x * y) - np.sum(x) * np.sum(y) / N) / (np.sum(np.power(x, 2)) - (np.sum(x)) ** 2 / N)   # 回归直线的斜率
    b = (np.sum(y) - k * np.sum(x)) / N # 回归直线的截距
    # 以下是用来计算标准差的，注释掉是因为没有用
    # Sxx = np.sum(np.power(x, 2)) - np.sum(x) ** 2 / N # x的总离差平方和
    Syy = np.sum(np.power(y, 2)) - np.sum(y) ** 2 / N   # y的总离差平方和
    # sr = np.sqrt((Syy - k ** 2 * Sxx) / (N - 2))  # 回归标准差
    # stddev_k = np.sqrt(sr ** 2 / Sxx) # 斜率标准差
    # stddev_b = sr * np.sqrt(1 / (N - np.sum(x) ** 2 / np.sum(np.power(x, 2))))    # 截距标准差
    r_square = np.sum(np.power((x * k + b - np.mean(y)), 2)) / Syy  # r^2
    return k, b, r_square

# 定积分
def integration(x, y, k, b, dx):
    dS = (y - k * x - b) * dx - k * dx * dx * 0.5  # 定积分，得到的面积有符号
    return dS    # 返回积分结果

# B-样条平滑曲线
def B_Spline(x, y, dx): # 平滑步长dx默认为0.005
    # 计算B-样条的节点和系数
    t, c, k = splrep(x, y)
    # 创建平滑函数
    smooth = BSpline(t, c, k)
    return smooth   # 返回平滑函数

# 雷诺校正点
def Reynolds(csv, Start1: int, End1: int, Start2: int, End2: int, dx: float):  # 积分步长dx默认为0.005
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
    equal_point = 0 # 初始化下标，从最左侧开始搜索
    S_total = 0 + sum(S[1]) # 从最左侧开始搜索，此时左侧总面积为0,右侧总面积为S[1]之和，初始化总面积
    flag = 1 if S_total > 0 else -1  # 初始化结束标志，当S_total * flag <= 0时结束搜索
    while S_total * flag > 0:
        S_total = S_total + S[0][equal_point] - S[1][equal_point]   # 不满足终止条件，向右移动一个点，更新总面积
        equal_point += 1    # 下标也向右移动一个点
    x0 = x_smooth[equal_point]  # 搜索结束，根据下标查找对应的横坐标
    return x0, abs(S_total) # 返回横坐标和结束时的总面积，总面积越接近0越精确