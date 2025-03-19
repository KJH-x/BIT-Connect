# pyright: reportMissingTypeStubs = false
# pyright: reportMissingTypeArgument = false
# pyright: reportUnknownParameterType = false
# pyright: reportUnknownMemberType = false
import ctypes
import os
import subprocess
import sys
import time
from subprocess import Popen
from typing import Any

import win32con
import win32gui
import win32process
from PIL import Image
from pystray import Menu, MenuItem
from pystray._win32 import Icon

from AIO_login import Operation
from log import setup_logger

logger = setup_logger()


def toggle_window_visibility(process: Popen[Any]) -> None:
    """
    Toggles the visibility of a window by its handle.
    """
    handle = get_window_by_pid(process)
    if win32gui.IsWindowVisible(handle):
        # Window is visible, hide it
        win32gui.ShowWindow(handle, win32con.SW_HIDE)
        logger.debug(f"Hide Window {handle:08X}")
    else:
        win32gui.ShowWindow(handle, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(handle)
        logger.debug(f"Show Window {handle:08X}")


def get_window_by_pid(process: Popen[Any]) -> int:
    windows: list[int] = []

    def enum_windows_callback(hWnd: int, lParam: int) -> None:
        if win32process.GetWindowThreadProcessId(hWnd)[1] == process.pid:
            windows.append(hWnd)

    # Here 0 for type check, no effect.
    win32gui.EnumWindows(enum_windows_callback, 0)
    if windows:
        return windows[0]

    else:
        return 0


def on_tray_click(process: Popen[Any]) -> None:
    """
    Callback function that is called when the tray icon is clicked.
    """
    logger.info(f"User double clicked tray icon")
    toggle_window_visibility(process)


class BitConnectIcon(Icon):
    WM_LBUTTONDBLCLK = 0x0203

    def __init__(self, *args, **kwargs):
        self.process = kwargs.pop('process', None)
        super().__init__(*args, **kwargs)

    def _on_notify(self, wparam, lparam):
        super()._on_notify(wparam, lparam)
        if lparam == self.WM_LBUTTONDBLCLK and self.process:
            toggle_window_visibility(self.process)


def create_tray_icon(process: Popen[Any]) -> None:
    """
    Creates a system tray icon using pystray.
    """
    icon_image = Image.open("./Network_Alive.ico")
    tray_instance = BitConnectIcon(
        '双击显示/隐藏窗口',
        icon_image,
        title="BitNet Manager",
        process=process
    )
    tray_instance.menu = Menu(
        MenuItem('显示/隐藏', lambda: on_tray_click(process)),
        MenuItem('退出', lambda: terminate_program(process, tray_instance))
    )
    # tray_instance.title("自动重登")
    ctypes.windll.shcore.SetProcessDpiAwareness(True)

    # 添加定期检查进程状态
    def check_process() -> None:
        if process.poll() is not None:
            logger.info("Exit with subprocess closed")
            tray_instance.stop()
            sys.exit(0)
        else:
            timer = threading.Timer(0.5, check_process)
            timer.start()

    import threading
    timer = threading.Timer(0.5, check_process)
    timer.start()

    logger.info(f"Start tray instance")
    tray_instance.run()


def terminate_program(process: Popen[Any], tray_instance: Any):
    try:
        if process.poll() is None:
            process.kill()
    except:
        pass
    tray_instance.stop()

    logger.info("Normal Exit")
    sys.exit(0)


if __name__ == '__main__':
    os.chdir(sys.path[0])

    Network_Alive = subprocess.Popen(
        "python ./Network_Alive.py",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    logger.debug(f"Popen: Network_Alive PID={Network_Alive.pid}")

    if os.path.exists("./BITer.json"):
        # Operation().verify()
        # logger.info("信息完整")
        time.sleep(5)
        toggle_window_visibility(Network_Alive)
        create_tray_icon(Network_Alive)
    else:
        sys.exit(1)
