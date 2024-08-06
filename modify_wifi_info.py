import ipaddress
import socket
import subprocess
import sys
import telnetlib
from ftplib import FTP
import logging
import time
import re
import os
import configparser
from typing import Union
import concurrent.futures
import netifaces

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# 扫描指定范围内的IP地址的指定端口

def tel_print(str: bytes):
    content = str.rfind(b"\r\n")
    if content == -1:
        return ""
    else:
        return content


def get_latest_print(tn: telnetlib.Telnet):
    times = 0
    while True:
        time.sleep(0.5)
        content = tn.read_very_eager()
        index1 = content.rfind(b"\r\n")
        index = content.rfind(b"\r\n", 0, index1)
        if index != -1:
            content = content[index + 2:index1:1]
            return content
        else:
            times += 1
            if times >= 7:
                logging.error(f"内容为：{content}")
                return False


def lan_ip_detect():
    os_type = os.name
    # 先获取本机地址
    host_name = socket.gethostname()
    host = socket.gethostbyname(host_name)
    if os_type == "nt":
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
        print(f"本机地址：{host}\n子网掩码：{subnet_mask}\n网关地址：{gateway_ip}")
    elif os_type == "posix":
        print("识别为 mac")
        interfaces = netifaces.interfaces()
        # 遍历所有网络接口
        addr_info = None
        local_ips = []
        subnet_mask = []
        for interface in interfaces:
            ifaddresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in ifaddresses:
                for link in ifaddresses[netifaces.AF_INET]:
                    ip = link['addr']
                    if not ip.startswith("127.") and not ip.startswith("169.254"):
                        addresses = netifaces.ifaddresses(interface)
                        for i in addresses.values():
                           for j in i:
                               if 'netmask' in j:
                                if j['netmask'].startswith("255."):
                                    local_ips.append(j['addr'])
                                    subnet_mask.append(j['netmask'])
        if len(local_ips) == 1 and len(subnet_mask) == 1:
            gateway_ip = netifaces.gateways()['default'][netifaces.AF_INET][0]
            subnet_mask = subnet_mask[0]
            print(f'subnet_mask={subnet_mask}, gateway_ip={gateway_ip}')
        else:
            input(f'未能获取到 ip 地址==>local_ips:{local_ips}, sub_mask:{subnet_mask}')
            sys.exit()
    try:
        network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
    except Exception as e:
        print(f"无法获取本机地址：{e}")
        sys.exit()
    # 获取可用主机范围
    addresses = list(network.hosts())
    return addresses


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
            tn.read_until(b"login: can't chdir to home directory '/home/root'", timeout=2)
            tn.write(b"cat customer/screenId.ini\n")
            # 循环防止未来得及读取到屏幕id的情况
            while True:
                time.sleep(0.3)
                s = tn.read_very_eager().decode("utf-8")
                pattern = r"deviceId=\s*(\w+)"
                match = re.search(pattern, s)
                if match:
                    screen = match.group(1)
                    break
            return [screen, tn, host]
        else:
            tn.close()
    except Exception:
        return False


def modify_wifi(screen: str, tn: telnetlib.Telnet, host: str):
    def operate():
        passwd_ok = False
        while True:
            wifi_name = input("请输入wifi名称：")
            if wifi_name is None or wifi_name == "":
                continue
            else:
                while True:
                    wifi_password = input("请输入wifi密码：")
                    if wifi_password is None or wifi_password == "":
                        continue
                    else:
                        passwd_ok = True
                        break
                if passwd_ok:
                    break
        return wifi_name, wifi_password
    wifi_name, wifi_password = operate()
    while True:
        confirm_info = input(f"{RED}请检查WiFi名称和密码是否正确！！！！！{RESET}\n{BLUE}WiFi名：{RESET}{wifi_name}, {BLUE}WiFi密码：{RESET}{wifi_password}\n 是否正确？（Y/N）：")
        try:
            if confirm_info.upper() == "Y":
                print(f"开始修改设备：{host} 的 WiFi 信息")
                break
            elif confirm_info.upper() == "N":
                wifi_name, wifi_password = operate()
            else:
                continue
        except Exception:
            print("输入错误请重新输入")

    quote_char = "'"
    content = ['ctrl_interface=/tmp/wifi/run/wpa_supplicant', 'update_config=1', 'network={', f'ssid={quote_char}"' + wifi_name + f'"{quote_char}', f'psk={quote_char}"' + wifi_password + f'"{quote_char}', 'key_mgmt=WPA-PSK', '}']
    times1 = 1
    while True:
        tn.write(b"echo '' > /appconfigs/wpa_supplicant.conf\n")
        for i in content:
            tmp_content = "echo " + i + " >> /appconfigs/wpa_supplicant.conf\n"
            tmp_content = tmp_content.encode('utf-8')
            tn.write(tmp_content)
        time.sleep(0.5)
        cmd_line_check = "cat /appconfigs/wpa_supplicant.conf | grep " + wifi_name +"& cat /appconfigs/wpa_supplicant.conf | grep " + wifi_password
        tn.write(cmd_line_check.encode('utf-8') + b"\n")
        tn.write(b'echo $? \n')
        tn_content = get_latest_print(tn).decode('utf-8')
        if tn_content == "0":
            print(f"设备：{host} \t{screen} WiFi信息已更改")
            break
        else:
            print(f"设备：{host} \t{screen} WiFi信息更改失败, 进行第{times1 + 1}次更改")
            if times1 >= 10:
                print(f'设备{host}多次切换失败请联系售后')
                sys.exit()
            times1 += 1



    tn.write(b"/software/restart_wifi.sh \n")



def cmd_check(tn: telnetlib.Telnet, cmd: list, text: str):
    times1 = 0
    text = text.encode('utf-8')
    while True:
        for i in cmd:
            tn.write(i.encode('utf-8') + b'\n')
            time.sleep(0.5)
        result = get_latest_print(tn)
        if result:
            if text in result:
                return True
            else:
                if times1 >= 10:
                    return False
                times1 += 1
                continue




addresses = lan_ip_detect()
port = 23
screen_list = []
tn_list = []
host_list = []
with concurrent.futures.ThreadPoolExecutor() as executor:
    future = [executor.submit(scan_port, str(ip), port) for ip in addresses]
    completed = 0
    # 等待线程执行完毕
    for f in concurrent.futures.as_completed(future):
        completed += 1
        dengyu = "=" * (int(completed / (len(addresses)) * 100))
        kong = " " * (100 - int(completed / (len(addresses)) * 100))
        total_jindu = f"\r正在检索设备：【{dengyu}{kong}】"
        print(total_jindu, end="", flush=True)
        if f.result():
            screen, tn, host = f.result()
            screen_list.append(screen)
            tn_list.append(tn)
            host_list.append(host)
    try:
        if len(screen_list) >= 1:
            print(f"\n发现以下屏幕：")
            for index, (item_a, item_b) in enumerate(zip(screen_list, host_list)):
                print(f"{index + 1}. {item_a}：\t{item_b}")
        else:
            input(f"未发现屏幕，按回车退出程序")
            sys.exit()

    except Exception as e:
        input(f"未发现屏幕,按回车退出程序")
        sys.exit()

    if not screen_list:
        input("\n未发现设备，按回车键退出程序")
        sys.exit()
    # 选择操作的屏幕
    operate_screen = []
    operate_tn = []
    operate_host = []
    while True:
        continue_to_circle = False
        option = input('\n请选择要操作的屏幕，直接输入序号，可以以英文“,”、“;”和空格分割，0则为全部：\n')
        option = re.split(r'[ ,;]+', option.strip())
        if len(option) == 1 and option[0] == "0":
            operate_screen = screen_list
            operate_tn = tn_list
            operate_host = host_list
            break
        for i in option:
            if i not in [str(j) for j in range(1, len(screen_list) + 1)]:
                print("选项错误，请重新输入")
                continue_to_circle = True
                break
        if continue_to_circle:
            continue
        for i in option:
            operate_screen.append(screen_list[int(i) - 1])
            operate_tn.append(tn_list[int(i) - 1])
            operate_host.append(host_list[int(i) - 1])
        break

    future = [executor.submit(modify_wifi, screen, tn, host) for screen, tn, host in
              zip(operate_screen, operate_tn, operate_host)]
    concurrent.futures.wait(future)
    input("切换完成!!!按回车键退出程序")
