import time
import datetime
import random


def stock_task(task_id):
    print(f"[{datetime.datetime.now()}] [Stock] 开始执行任务: {task_id}")
    time.sleep(2)
    # 模拟业务逻辑
    return "股票数据: 收盘价上涨 5%"


def jd_checkin(task_id):
    print(f"[{datetime.datetime.now()}] [JD] 开始执行任务: {task_id}")
    # 模拟失败
    if random.random() < 0.3:
        raise Exception("模拟网络波动：签到接口请求超时")
    return "签到成功，获得 10 京豆"


def ticket_monitor(task_id):
    print(f"[{datetime.datetime.now()}] [Ticket] 监控中...")
    return "暂无余票"