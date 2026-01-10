#!/usr/bin/env python3
"""
示例任务：火车票抢票通知
监控火车票余票，有票时发送通知
"""

import sys
import os
from datetime import datetime, timedelta


def check_ticket_availability(from_station: str, to_station: str, date: str):
    """
    检查火车票余票

    Args:
        from_station: 出发站
        to_station: 到达站
        date: 出发日期 (YYYY-MM-DD)

    Returns:
        list: 可用车次列表
    """
    print(f"[{datetime.now()}] 查询 {from_station} -> {to_station} ({date}) 的余票...")

    # 这里需要实际的 12306 查询逻辑
    # 可以使用 requests 调用 12306 接口或使用第三方库

    # 示例：模拟查询结果
    available_trains = []

    # 模拟有票的情况
    if datetime.now().hour % 2 == 0:  # 偶数小时模拟有票
        available_trains = [
            {
                "train_no": "G123",
                "from_station": from_station,
                "to_station": to_station,
                "start_time": "08:00",
                "arrive_time": "12:30",
                "date": date,
                "seats": {
                    "二等座": "有",
                    "一等座": "3",
                    "商务座": "无"
                }
            }
        ]
        print(f"  发现 {len(available_trains)} 个有票车次！")
    else:
        print("  暂无余票")

    return available_trains


def send_notification(trains: list):
    """发送抢票通知"""
    # 这里可以集成通知发送逻辑
    # 实际使用时可以调用通知模块或 Webhook

    for train in trains:
        print(f"\n🎉 有票了！")
        print(f"  车次: {train['train_no']}")
        print(f"  时间: {train['start_time']} - {train['arrive_time']}")
        print(f"  余票: {train['seats']}")


def main():
    """主函数"""
    # 从环境变量或命令行参数获取查询信息
    from_station = os.getenv("TICKET_FROM", "北京")
    to_station = os.getenv("TICKET_TO", "上海")

    # 默认查询明天
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    date = os.getenv("TICKET_DATE", tomorrow)

    print(f"[{datetime.now()}] 火车票监控任务启动")
    print(f"  查询: {from_station} -> {to_station}")
    print(f"  日期: {date}")

    try:
        available_trains = check_ticket_availability(from_station, to_station, date)

        if available_trains:
            send_notification(available_trains)
            # 有票时返回特殊码，便于触发通知
            return 100  # 100 表示有票

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
