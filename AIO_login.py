import argparse
import calendar
import hmac
import json
import math
import os
import re
import sys
from base64 import b64encode
from datetime import datetime
from enum import Enum
from getpass import getpass
from hashlib import sha1
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests
from requests import Session

import log

logger = log.setup_logger()


# 以下代码基于：https://github.com/Aloxaf/10_0_0_55_login 修改


class Action(Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    QUERY = "query"
    VERIFY = "verify"


class AlreadyOnlineException(Exception):
    pass


class AlreadyLoggedOutException(Exception):
    pass


class UsernameUnmatchedException(Exception):
    pass


class QueryEmptyUser(Exception):
    pass


class WrongUserInfo(Exception):
    pass


class UnreachableError(SyntaxError):
    """Branch that should not be reached
    """

    def __init__(self, msg:str):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
    pass


def report_time() -> str:
    return datetime.now().strftime(TLF)


CONFIG_PATH = "./BITer.json"


def read_config() -> tuple[str, str]:
    """从脚本所在文件夹读取用户信息

    Return:
        - tuple[str, str]: (username, password)
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf8") as config_file:
            config = json.load(config_file)
            return config["username"], config["password"]

    except FileNotFoundError:
        logger.warning("未找到配置文件，正在创建...")
        return write_config()

    except json.decoder.JSONDecodeError:
        logger.warning("文件错误，正在重写...")
        return write_config()


def write_config() -> tuple[str, str]:
    """写入登录配置文件

    Return:
        - tuple[str, str]: (username, password)
    """
    with open(CONFIG_PATH, "w", encoding="utf8") as config_file:
        username = input(f" - 请输入账号:")
        password = getpass(f" - 请输入密码(你不会看到输入的内容):",)
        config_file.write(
            f"{{\"username\":\"{username}\",\"password\":\"{password}\"}}"
        )
    return username, password


def clear_config() -> None:
    with open(CONFIG_PATH, "w", encoding="utf8") as config_file:
        config_file.write(
            f"{{\"username\":\"\",\"password\":\"\"}}"
        )
    return


API_BASE = "http://10.0.0.55"
TYPE_CONST = 1
N_CONST = 200
TLF = "%H:%M:%S"


class User:
    def __init__(self, username: str, password: str) -> None:
        """初始化变量
        """
        self.username = username
        self.password = password

        self.ip, self.acid = parse_homepage()
        self.session = Session()

    def operation(self, action: Action) -> dict[str, str]:
        """检查当前登录情况

        Raises:
            - AlreadyOnlineException: 重复登录
            - AlreadyLoggedOutException: 重复登出
            - UsernameUnmatchedException: 登出用户名错误

        Returns:
            - json: response
        """
        is_logged_in, username = get_user_info()

        if username and username != self.username:
            raise UsernameUnmatchedException(
                f"[WARN][{report_time()}] 当前在线用户:{username:1s}与尝试操作用户{self.username:1s}账号不同，使用-a mkjson参数重新填写"
            )

        elif is_logged_in:
            if action is Action.LOGIN:
                if username is not None:
                    raise AlreadyOnlineException(
                        f"[WARN][{report_time()}] 重复登录，当前在线：{username}")

                else:
                    raise AlreadyOnlineException(
                        f"[WARN][{report_time()}] 重复登录")
            elif action is Action.VERIFY:
                return traffic_query()
            elif action is Action.QUERY:
                return traffic_query()

        elif not is_logged_in:
            if action is Action.LOGOUT:
                raise AlreadyLoggedOutException(
                    f"[WARN][{report_time()}] {username}重复登出")
            elif action is Action.QUERY:
                raise AlreadyLoggedOutException(
                    f"[WARN][{report_time()}] 已登出，取消查询")

        else:
            raise UnreachableError(
                f"[WARN][{report_time()}] {action} is not supported.")

        if params := self._make_params(action):

            response = self.session.get(
                API_BASE + "/cgi-bin/srun_portal",
                params=params
            )
            res = dict(json.loads(
                response.text[6:-1])) if response.text.startswith("jsonp") else {}
            res["username"] = self.username
            return res
        else:
            raise WrongUserInfo(
                f"[WARN][{report_time()}] 信息错误，使用-a mkjson参数重新填写")

    def _get_token(self) -> str:
        """获取token

        Returns:
            - str: token
        """
        result = {}
        params = {
            "callback": "jsonp",
            "username": self.username,
            "ip": self.ip
        }

        response = self.session.get(
            API_BASE + "/cgi-bin/get_challenge", params=params
        )
        result = dict(json.loads(response.text[6:-1]))

        if result.get("challenge"):
            return str(result.get("challenge"))
        else:
            return ""

    def _make_params(self, action: Action) -> dict[str, Any]:
        """制作请求参数

        Args:
            action: Action enum specifying operation type

        Returns:
            dict[str, str]: Request parameters
        """
        token = self._get_token()

        params = {
            "callback": "jsonp",
            "username": self.username,
            "action": action.value,
            "ac_id": self.acid,
            "ip": self.ip,
            "type": TYPE_CONST,
            "n": N_CONST,
        }

        data = {
            "username": self.username,
            "password": self.password,
            "acid": self.acid,
            "ip": self.ip,
            "enc_ver": "srun_bx1",
        }

        hmd5 = hmac.new(token.encode(), b"", "MD5").hexdigest()
        json_data = json.dumps(data, separators=(",", ":"))
        info = "{SRBX1}" + fkbase64(xencode(json_data, token))
        chksum = sha1(
            "{0}{1}{0}{2}{0}{3}{0}{4}{0}{5}{0}{6}{0}{7}".format(
                token, self.username, hmd5, self.acid, self.ip, N_CONST, TYPE_CONST, info
            ).encode()
        ).hexdigest()

        params.update(
            {
                "password": "{MD5}" + hmd5,
                "chksum": chksum,
                "info": info
            }
        )

        return params


def parse_homepage() -> tuple[str, str]:
    """解析并获取ip与acid

    Raises:
        Exception: If acid not in redirected URL or IP not in response

    Returns:
        tuple[str, str]: (ip, ac_id)
    """

    res = requests.get(API_BASE)

    # ac_id appears in the url query parameter of the redirected URL
    query = parse_qs(urlparse(res.url).query)
    ac_id = query.get("ac_id")

    if not ac_id:
        raise Exception("failed to get acid")

    # ip appears in the response HTML
    class IPParser(HTMLParser):
        def __init__(self, *args:str, **kwargs:dict[str, list[str]]):
            super().__init__(*args, **kwargs)
            self.ip = None

        def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
                if tag == "input":
                    attr_dict: dict[str, Optional[str]] = dict(attrs)
                    if attr_dict.get("name") == "user_ip":
                        self.ip = attr_dict.get("value")

        def get_ip(self, *args:str, **kwargs:dict[str, list[str]])->Optional[str]:
            super().feed(*args, **kwargs)
            return self.ip or None

    parser = IPParser()
    ip = parser.get_ip(res.text)

    if not ip:
        raise Exception("failed to get ip")

    return ip, ac_id[0]


def get_user_info() -> tuple[bool, str | None]:
    """获取当前登录用户信息

    Returns:
        tuple[bool, str | None]: (is_logged_in, username)
    """

    is_logged_in = True
    username = None

    resp = requests.get(API_BASE + "/cgi-bin/rad_user_info")
    data = resp.text

    if data == "not_online_error":
        is_logged_in = False
    else:
        username = data.split(",")[0]

    return is_logged_in, username


def fkbase64(raw_s: str) -> str:
    """base64掩码加密

    Returns:
        - str: encoded string
    """
    trans = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",
        "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA",
    )
    ret = b64encode(bytes(ord(i) & 0xFF for i in raw_s))
    return ret.decode().translate(trans)


def xencode(msg:str, key:str):
    """加密算法，用于网络认证过程中的数据加密

    该函数包含两个内部函数：
    - sencode: 将消息和密钥转换为32位整数数组
    - lencode: 将加密后的整数数组转换回字符串

    Args:
        msg (str): 需要加密的消息
        key (str): 加密密钥

    Returns:
        str: 加密后的字符串
    """
    def sencode(msg:str, key:bool):
        def ordat(msg:str, idx:int):
            if len(msg) > idx:
                return ord(msg[idx])
            return 0

        msg_len = len(msg)
        pwd:list[int] = []
        for i in range(0, msg_len, 4):
            pwd.append(ordat(msg, i) | ordat(msg, i + 1) << 8 |
                       ordat(msg, i + 2) << 16 | ordat(msg, i + 3) << 24)
        if key:
            pwd.append(msg_len)
        return pwd

    def lencode(msg: list[int], key: bool) -> str:
        msg_len: int = len(msg)
        ll: int = (msg_len - 1) << 2
        if key:
            m: int = msg[msg_len - 1]
            if m < ll - 3 or m > ll:
                return ""
            ll = m
        str_parts: list[str] = []
        for num in msg:
            byte0: str = chr(num & 0xFF)
            byte1: str = chr((num >> 8) & 0xFF)
            byte2: str = chr((num >> 16) & 0xFF)
            byte3: str = chr((num >> 24) & 0xFF)
            str_parts.append(byte0 + byte1 + byte2 + byte3)
        full_str: str = "".join(str_parts)
        if key:
            return full_str[0:ll]
        return full_str

    if msg == "":
        return ""
    pwd = sencode(msg, True)
    pwdk = sencode(key, False)
    if len(pwdk) < 4:
        pwdk = pwdk + [0] * (4 - len(pwdk))
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    m = 0
    e = 0
    d = 0
    p = 0
    q = math.floor(6 + 52 / (n + 1))
    while 0 < q:
        d = d + c & (0x8CE0D9BF | 0x731F2640)
        e = d >> 2 & 3
        p = 0
        while p < n:
            y = pwd[p + 1]
            m = z >> 5 ^ y << 2
            m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = pwd[p] + m & (0xEFB8D130 | 0x10472ECF)
            z = pwd[p]
            p = p + 1
        y = pwd[0]
        m = z >> 5 ^ y << 2
        m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[n] = pwd[n] + m & (0xBB390742 | 0x44C6F8BD)
        z = pwd[n]
        q = q - 1
    return lencode(pwd, False)


def traffic_query() -> dict[str, str]:
    """当且仅当登陆成功后请求此jQuery来获取详细信息

    Returns:
        dict[str, str]: Query result with traffic and balance details
    """
    query_url = f"{API_BASE}/cgi-bin/rad_user_info?callback=1677774013868"
    user_detail: dict[str, str] = dict(json.loads(re.findall(
        r"\{[\s\S]*\}", requests.get(url=query_url).text)[0]))

    query_result: dict[str, str] = {}
    query_result['time_online'] = user_detail.get('sum_seconds', "")
    query_result['traffic_remain'] = user_detail.get('remain_bytes', "")
    query_result['traffic_used'] = user_detail.get('sum_bytes', "")
    query_result['balance_main'] = user_detail.get('user_balance', "")
    query_result['balance_wallet'] = user_detail.get('wallet_balance', "")

    today = datetime.now()
    month_days = calendar.monthrange(today.year, today.month)[1]
    passed_days = today.day - 1

    balance = 200*1024*1024*1024*passed_days / \
        month_days-int(query_result['traffic_used'])

    query_result['traffic_balance'] = str(balance == abs(balance))
    query_result['exceed_part'] = str(abs(balance))
    query_result['exceed_part_per_day'] = str(abs(balance)/passed_days)

    query_result['record_date'] = str(today.date())

    return query_result


class Operation:
    def __init__(self):
        self.username, self.password = read_config()

    def login(self) -> None:
        while True:
            user = User(self.username, self.password)
            res = user.operation(Action.LOGIN)
            if res.get('error_msg') == "Password is error.":
                logger.warning("密码错误，请重新输入账号密码")
                write_config()
                self.username, self.password = read_config()
            else:
                break
        logger.info(f"用户{res.get('username')} IP({res.get('online_ip')}) 登录成功")

    def logout(self) -> None:
        while True:
            user = User(self.username, self.password)
            res = user.operation(Action.LOGOUT)
            if res.get('error_msg') == "Password is error.":
                logger.warning("密码错误，请重新输入账号密码")
                write_config()
                self.username, self.password = read_config()
            else:
                break
        logger.info(f"用户{res.get('username')} IP({res.get('online_ip')}) 现已登出")

    # def verify(self) -> bool:
    #     user = User(self.username, self.password)
    #     res = user.operation(Action.VERIFY)
    #     logger.debug(f"{res}")
    #     if len(res) > 1:
    #         logger.info("信息验证成功")
    #         return True
    #     else:
    #         logger.warning("信息错误，使用-a mkjson参数重新填写")
    #         return False

    def config(self, action: str) -> None:
        """Manage configuration file operations.
        
        Args:
            action: Configuration action ('chkjson', 'mkjson', or 'clear')
        
        Returns:
            None
        """
        if action == "chkjson":
            read_config()
        elif action == "mkjson":
            write_config()
        elif action == "clear":
            clear_config()


def main() -> None:
    """读取命令，分析参数，回报执行状态

    Returns:
        - None
    """
    arg_choices = [
        "login", "登录", "登陆", "上线",
        "logout",  "登出", "下线", "退出",
        "chkjson", "mkjson", "clear",
        # "verify"
    ]

    parser = argparse.ArgumentParser(description="Login to BIT network")
    parser.add_argument(
        "-a", "--action",
        choices=arg_choices,
        help="login or logout"
    )

    for arg in sys.argv:
        sys.argv[sys.argv.index(arg)] = arg.lower()
    args = parser.parse_args()

    try:
        handler = Operation()
        action = str(args.action)

        if action in ["login", "登录", "登陆", "上线"]:
            handler.login()
        elif action in ["logout", "登出", "下线", "退出"]:
            handler.logout()
        # elif action == "verify":
        #     handler.verify()
        elif action in ["chkjson", "mkjson", "clear"]:
            handler.config(action)
        else:
            exit(13)

    except UnreachableError as e:
        logger.error(str(e))
        exit(10)
    except Exception as e:
        logger.error(str(e))
        exit(11)
    except KeyboardInterrupt:
        logger.warning("手动退出")
        exit(12)

    exit(0)


if __name__ == "__main__":
    os.system("chcp 65001>nul")
    os.chdir(sys.path[0])
    main()
