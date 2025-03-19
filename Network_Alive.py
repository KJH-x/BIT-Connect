# pyright: reportUnknownMemberType=true
# encoding = utf-8
# Network_Alive

# import logger
import msvcrt
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Literal

import AIO_login
import log

logger = log.setup_logger()


class UnreachableError(SyntaxError):
    """表示不应该到达的代码分支的异常类。

    Args:
        msg (str): 错误信息
    """

    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


def date_log() -> int:
    """获取当前日期的数字表示。

    Returns:
        int: 当前日期的天数(1-31)
    """
    return int(datetime.now().strftime("%d"))


def report_time() -> str:
    """获取当前时间的格式化字符串。

    Returns:
        str: 格式化的时间字符串，格式为"HH:MM:SS"
    """
    return datetime.now().strftime("%H:%M:%S")


def wait_for_keypress(msg: str) -> None:
    """显示消息并等待用户按键。

    Args:
        msg (str): 要显示的消息
    """
    logger.info(msg)
    msvcrt.getch()


def time_convert() -> str:
    """计算并格式化从程序启动到现在的运行时间。

    Returns:
        str: 格式化的持续时间字符串，格式为"HH:MM:SS"
    """
    duration = datetime.now()-START_TIME
    secs = duration.seconds % 60
    mins = int((duration.seconds) / 60) % 60
    hours = duration.days * 24+int((duration.seconds) / 3600)
    return f"{hours:d}:{mins:02d}:{secs:02d}"


# 创建全局Operation实例
aio_handler = None


def operation(operation: Literal[0, 1]) -> int:
    """执行AIO脚本的各种操作。

    Args:
        operation (int): 操作类型
            0: 登出操作
            1: 登录操作
            2: 验证操作

    Returns:
        int: 操作的返回码
            2: 脚本丢失
            14: 需要创建配置文件
            其他值: 具体操作的返回状态
    """
    global aio_handler
    try:
        if aio_handler is None:
            aio_handler = AIO_login.Operation()

        match operation:
            case 0:
                aio_handler.logout()
                return 0
            case 1:
                aio_handler.login()
                return 0
            # case 2:
            #     aio_handler.verify()
                # return 0

            case _:
                return -1
    except Exception as e:
        logger.exception(f"操作执行失败: {e}")
        return -1


def relogin(interval: int = 2) -> None:
    """执行重新登录操作，包含登出和登录两个步骤。

    Args:
        interval (int, optional): 操作之间的等待时间(秒)。默认为2秒。
    """
    operation(0)
    time.sleep(interval)
    operation(1)
    time.sleep(interval)


def summary(statistic: dict[str, int], fail_log: list[tuple[int, str]]) -> None:
    """显示程序运行的统计信息和失败日志。

    Args:
        statistic (dict[str, int]): 包含各类操作计数的字典
        fail_log (list[tuple[int, str]]): 失败记录列表，每个元素为(日期, 时间)的元组
    """
    os.system("cls")
    rpd = date_log()

    print(45*'-')
    print(f"[INFO] 启动至今<{time_convert()}>概况:")
    print(45*'-')
    print(
        f"|失败:{statistic['失败']:^5d}|成功:{statistic['成功']:^5d}|强制:{statistic['强制']:^5d}|跳过:{statistic['跳过']:^5d}|")
    print(45*'-')
    print(f"今日({rpd:02d}日)自动重登记录：")
    chk = 0
    for log in fail_log:
        if log[0] == rpd:
            chk = 1
            print(f"  - {log[1]}")
        else:
            fail_log.remove(log)
    print("  - （无记录）") if not chk else 1
    print(45*'-')
    return


def entrance_protect() -> bool:
    """程序入口保护函数，检查依赖并启动主循环。

    Returns:
        bool: 是否成功启动程序
    """
    logger.info("正在检查依赖脚本")
    while not check_component():
        continue
    os.system("cls")
    print(welcome_msg)
    main_loop()
    return True


def check_component() -> bool:
    """检查程序依赖组件是否可用。

    Returns:
        bool: 所有必需组件是否都可用
            True: 所有组件可用
            False: 存在不可用组件
    """
    global aio_path
    if os.access(f"{aio_path}/AIO_login.py", os.R_OK):
        return True
    else:
        logger.warning(f"在\"{aio_path}\"")
        logger.warning("找不到登录脚本(默认情况下它应该和本脚本在同一个文件夹)")
        logger.info("也许你想手动输入脚本路径？(放在别的地方了)")
        new_path = input(
            f"[INFO] 新的路径(直接回车以重新检查):").strip().replace("\\\\", "/")
        if len(new_path) > 12 and new_path[-12:].lower() == 'aio_login.py':
            aio_path = new_path[:-12]
        elif len(new_path) > 2 and new_path[-2:] == '/':
            aio_path = new_path[-2:]
        elif len(new_path) > 2:
            aio_path = new_path
        elif new_path == '':
            pass
        else:
            raise UnreachableError("无法理解的路径")
        logger.info(aio_path)
        return False
    # if not operation(2):
        # input("check_component:operation 2 check pass")
        # return True
    # else:
        # input("check_component:operation 2 check fail")
        # return False


def main_loop() -> None:
    """程序主循环函数。

    执行以下操作：
    1. 定期ping目标地址检测网络连接状态
    2. 在检测到断网时自动重新登录
    3. 统计各类操作的次数
    4. 记录失败日志
    5. 响应用户的Ctrl+C操作
    """
    statistic = {'失败': 0, '成功': 0, '强制': 0, '跳过': 0}
    fail_log: list[tuple[int, str]] = []  # 失败日志列表
    t1, t2 = 0.0, 0.0  # 用于记录ping操作的开始时间和结束时间
    command = ["ping", PING_TARGET, "-n", "2"]  # ping命令的参数列表
    while True:
        try:
            logger.info(f"正在ping {PING_TARGET}, [Ctrl+C] 强制重登")
            try:
                t1 = time.time()
                subprocess.run(command, stdout=subprocess.DEVNULL, check=True)
                t2 = time.time()

            except KeyboardInterrupt as e:
                logger.exception(f"An exception occurred: {e}")
                statistic['强制'] += 1
                logger.info("[USER] [Ctrl+C] 强制重登")
                time.sleep(0.2)
                sys.stdout.write('\r\033[K')
                relogin()
                continue

            except subprocess.CalledProcessError as e:
                logger.info(f"Expected Error: return_not_zero")
                logger.exception(f"An exception occurred: {e}")
                t2 = t1 + 5
                pass

            if t2 - t1 > 4.5:  # 如果ping操作超过4.5秒，判定为失败
                statistic['失败'] += 1
                fail_log.append((date_log(), report_time()))
                logger.warning("ping 判定：离线")
                relogin()

                if (statistic["失败"] + statistic["成功"] + statistic["强制"]) % 5 == 0:
                    summary(statistic, fail_log)  # 每5次检测，输出统计信息

            else:  # 如果ping操作未超过4.5秒，判定为成功
                statistic['成功'] += 1
                logger.info("ping 判定：在线")

                if (statistic["失败"] + statistic["成功"] + statistic["强制"]) % 5 == 0:
                    summary(statistic, fail_log)
                logger.info("休眠一分钟， [Ctrl+C] 跳过休眠")

                time.sleep(60)
        except KeyboardInterrupt as e:
            statistic['跳过'] += 1
            logger.info("用户 跳过休眠")
            continue
        except Exception as e:
            logger.exception(f"An exception occurred: {e}")
            print()
            raise e


PING_TARGET = 'bilibili.com'
VERSION = 'v1.2.1'
aio_path = sys.path[0]
START_TIME = datetime.now()
welcome_msg = f"""
---------------------------------------------------------------------
[INFO] 欢迎使用校园网自动重连脚本
---------------------------------------------------------------------
| 当前版本{VERSION}，访问Github仓库以获取最新版脚本
| https://github.com/KJH-x/BIT-Connect/
---------------------------------------------------------------------
| 在判定期间可通过[Ctrl+C]跳过并强制重新登陆，
| 在睡眠期间可通过[Ctrl+C]打断睡眠开始下一轮ping
| 本消息将在下次概况刷新消失，访问仓库阅读 Readme.md 文件以了解更多
| 托盘右键菜单退出，或关闭程序框体退出， 双击托盘图标切换框体可见性
| 通过 Start.tray.pyw 启动将会在 5s 后自动隐藏
---------------------------------------------------------------------
"""

if __name__ == "__main__":
    os.chdir(sys.path[0])
    while not entrance_protect():
        continue
