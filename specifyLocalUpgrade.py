from asyncio.windows_events import NULL
import concurrent.futures
import logging
import os
import platform
import functools
import sys
import telnetlib
import time
from typing import Union
import re
from ftplib import FTP
import subprocess
import ipaddress
import socket
import gettext
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from functools import partial

spicyfy_screen = "PSf47be7L010322"
local_ip = NULL


def lan_ip_detect():
    try:
        # 先获取本机地址
        host_name = socket.gethostname()
        host = socket.gethostbyname(host_name)
        global local_ip
        local_ip = host
        # 执行命令并获取输出
        result = subprocess.run(["ipconfig"], capture_output=True, text=True).stdout
        index = result.rfind(host)
        result = result[index::]
        index = result.find("Subnet Mask")
        if index == -1:
            index = result.find("子网掩码")
        result = result[index::]
        pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        subnet_mask = re.search(pattern, result).group()
        index = result.find("Default Gateway")
        if index == -1:
            index = result.find("默认网关")
        result = result[index::]
        pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        gateway_ip = re.search(pattern, result).group()
        print(
            _(
                "本机地址：{host}\n子网掩码：{subnet_mask}\n网关地址：{gateway_ip}"
            ).format(host=host, subnet_mask=subnet_mask, gateway_ip=gateway_ip)
        )
        network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
        # 获取可用主机范围
        addresses = list(network.hosts())
        start_ip = list(network.hosts())[0]
        end_ip = list(network.hosts())[-1]
        start_ip = str(start_ip)
        end_ip = str(end_ip)
    except Exception:
        while True:
            try:
                gateway_ip = input(_("请输入正确的网关地址："))
                ipaddress.IPv4Network(gateway_ip)
                break
            except ipaddress.AddressValueError:
                print(_("请输入正确的网关地址"))
        subnet_mask = "255.255.255.0"
        network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
        # 获取可用主机范围
        addresses = [str(ip) for ip in network.hosts()]
        start_ip = addresses[0]
        end_ip = addresses[-1]
    return start_ip, end_ip, addresses


def ip_match(str):
    pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    match = re.search(pattern, str)
    if match:
        return match.group()
    else:
        return False


def tel_print(str: bytes):
    content = str.rfind(b"\r\n")
    if content == -1:
        return ""
    else:
        return content


def retry(
    retry_times: int, exception: (Exception,), delay: int = 0, backoff: float = 1.0
):
    """
    重试函数
    :param retry_times: 重试次数
    :param exception: 异常类型
    :param delay: 延迟时间
    :param backoff: 退避系数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _retry_times, _delay, _backoff = retry_times, delay, backoff
            for i in range(_retry_times):
                try:
                    result = func(*args, **kwargs)
                    if result:
                        return result
                    else:
                        raise Exception(_("操作失败"))
                except Exception as e:
                    print(
                        _("[{func_name}] 第 {i} 次失败: {e}").format(
                            func_name=func.__name__, i=i, e=e
                        )
                    )
                    if i == _retry_times:
                        input(_("操作失败，按回车键退出程序") + "\n")
                        sys.exit()
                    if _delay > 0:
                        time.sleep(_delay)
                        _delay *= backoff

        return wrapper

    return decorator


def get_latest_print(tn: telnetlib.Telnet):
    times = 0
    while True:
        time.sleep(0.5)
        content = tn.read_very_eager()
        index1 = content.rfind(b"\r\n")
        index = content.rfind(b"\r\n", 0, index1)
        if index != -1:
            content = content[index + 2 : index1 : 1]
            return content
        else:
            times += 1
            if times >= 7:
                logging.error(_("内容为：{content}").format(content=content))
                return False


def scan_port(host, port) -> Union[list, bool, telnetlib.Telnet]:
    try:
        tn = telnetlib.Telnet(host, port, timeout=0.5)
        s = tn.read_until(b"login: ", timeout=0.5)
        index = tel_print(s)
        result = s[index::].decode("utf-8")
        if "login: " in result:
            tn.write(b"root\n")
            tn.read_until(b"Password: ", timeout=2)
            tn.write(b"ya!2dkwy7-934^\n")
            tn.read_until(
                b"login: can't chdir to home directory '/home/root'", timeout=2
            )
            tn.write(b"cat customer/screenId.ini\n")
            # 没有屏幕id可以打开
            print(host)
            # 循环防止未来得及读取到屏幕id的情况
            while True:
                time.sleep(0.3)
                s = tn.read_very_eager().decode("utf-8")
                pattern = r"deviceId=\s*(\w+)"
                match = re.search(pattern, s).group(1)
                if match:
                    screen = match
                    break
            return [screen, tn, host]
        else:
            tn.close()
    except Exception:
        return False


def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def i18n_setup():
    """使用打包/源码统一方式定位 locales，并可通过 APP_LANG 强制语言。

    - 优先读取环境变量 APP_LANG（默认 en_EN）
    - 预检查 .mo 是否存在，缺失时打印诊断
    - 找不到目标语言时回退到 en_EN 或源码
    """
    base_dir = resource_path("")
    locale_dir = os.path.join(base_dir, "locales")
    lang_code = os.environ.get("APP_LANG", "en_EN")

    mo_file = os.path.join(locale_dir, lang_code, "LC_MESSAGES", "messages.mo")
    if not os.path.exists(mo_file):
        print(f"[i18n] WARN: missing mo file: {mo_file}")

    try:
        t = gettext.translation(
            "messages", localedir=locale_dir, languages=[lang_code], fallback=False
        )
    except Exception:
        print(f"[i18n] FALLBACK to en_EN or source, localedir={locale_dir}")
        t = gettext.translation(
            "messages", localedir=locale_dir, languages=["en_EN"], fallback=True
        )
    return t.gettext


_ = i18n_setup()


def http_server(start_port=8000, path: str = ""):
    """
    启动一个 HTTP 文件服务，支持自动换端口和指定目录
    :param start_port: 起始端口
    :param path: 要服务的目录（默认当前目录）
    """
    port = start_port
    if not path:
        path = os.getcwd()  # 默认当前目录

    # 用 partial 传递 directory 参数
    Handler = partial(SimpleHTTPRequestHandler, directory=path)

    while True:
        try:
            server = HTTPServer(("0.0.0.0", port), Handler)
            # 在后台线程中启动 HTTP 服务，避免阻塞主流程
            Thread(target=server.serve_forever, daemon=True).start()
            print(f"Serving {path} at http://127.0.0.1:{port}")
            return port
        except OSError as e:
            if e.errno in (98, 10048):  # 端口占用
                print(_("端口 {port} 被占用，更换端口...").format(port=port))
                port += 1
                time.sleep(1)
            else:
                raise


@retry(retry_times=3, exception=(Exception,), delay=1, backoff=1)
def scan_ip_range(start_ip, end_ip, port, addresses):
    screen = NULL
    tn_s = NULL
    host_list = NULL
    # 使用线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future = [executor.submit(scan_port, str(ip), port) for ip in addresses]
        completed = 0
        # 等待线程执行完毕
        for f in concurrent.futures.as_completed(future):
            completed += 1
            dengyu = "=" * (int(completed / (len(addresses)) * 100))
            kong = " " * (100 - int(completed / (len(addresses)) * 100))
            total_jindu = f"{dengyu}{kong}"
            print(
                "\r" + _("正在检索设备：【{bar}】").format(bar=total_jindu),
                end="",
                flush=True,
            )
            if f.result():
                list_a, tn, host = f.result()
                if list_a == spicyfy_screen:
                    screen = list_a
                    tn_s = tn
                    host_list = host
                else:
                    continue
    if not screen:
        # input(_("\n未发现设备，按回车键退出程序"))
        # sys.exit()
        raise Exception(_("未发现设备"))

    print(_("\n检测到指定屏幕：{screen}，开始升级").format(screen=spicyfy_screen))
    ota_package_path = resource_path("resource/ota_package/SStarOta.bin.gz")
    ota_package_name = os.path.dirname(ota_package_path)
    http_port = http_server(8000, ota_package_name)

    tn_s.write(b"rm /upgrade/SStarOta.bin.gz\n")
    time.sleep(1)

    tn_s.write(
        f"wget http://{local_ip}:{http_port}/SStarOta.bin.gz -O /upgrade/SStarOta.bin.gz && echo success-$?\n".encode(
            "utf-8"
        )
    )
    tn_s.read_until(b"success-0", timeout=50)
    print(_("固件上传成功"))
    tn_s.write(b"/upgrade/upgrade.sh &\n")
    tn_s.write(b"/software/script/upgrade.sh &\n")
    time.sleep(20)
    max_wait_time = 240
    while True:
        print(_("倒计时：{max_wait_time}").format(max_wait_time=max_wait_time))
        max_wait_time -= 1
        if max_wait_time <= 0:
            print(_("升级超时"))
            return False
        try:
            tn = telnetlib.Telnet(host_list, 23, timeout=0.5)
            content = tn.read_until(b"login: ", timeout=0.5)
            input(_("升级成功，按回车键退出程序"))
            sys.exit()
        except Exception:
            continue


def main():
    # 设置要扫描的IP地址范围和端口号
    start_ip, end_ip, addresses = lan_ip_detect()
    port = 23  # Telnet端口号
    # 扫描指定范围内的IP地址的指定端口
    scan_ip_range(start_ip, end_ip, port, addresses)


if __name__ == "__main__":
    main()
