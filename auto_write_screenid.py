import ipaddress
import socket
import subprocess
import sys
import telnetlib
import logging
import time
import re
import os
from typing import Union
import netifaces
import concurrent.futures

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)


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
    try:
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
            interfaces = netifaces.interfaces()
            # 遍历所有网络接口
            addr_info = None
            for interface in interfaces:
                if interface == "en0":
                    addr_info = netifaces.ifaddresses(interface)
                    break
            if addr_info and netifaces.AF_INET in addr_info:
                address = addr_info[netifaces.AF_INET][0]
                subnet_mask = address.get("netmask")
                gateway_ip = netifaces.gateways()['default'][netifaces.AF_INET][0]
        try:
            network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
        except Exception as e:
            print(f"无法获取本机地址：{e}")
            sys.exit()
        # 获取可用主机范围
        addresses = list(network.hosts())
    except Exception:
        while True:
            try:
                gateway_ip = input("请输入正确的网关地址：")
                ipaddress.IPv4Network(gateway_ip)
                break
            except ipaddress.AddressValueError:
                print("请输入正确的网关地址")
        subnet_mask = "255.255.255.0"
        network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
        # 获取可用主机范围
        addresses = [str(ip) for ip in network.hosts()]
    return addresses


def scan_port(host, port) -> Union[list, bool, telnetlib.Telnet]:
    screen = None
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
            start_time = time.time()
            # 循环防止未来得及读取到屏幕id的情况
            while True:
                if time.time() - start_time > 10:
                    break
                time.sleep(0.3)
                s = tn.read_very_eager().decode("utf-8")
                pattern = r'deviceId=([^\r\n]*)'
                match = re.search(pattern, s)
                if match:
                    screen = match.group()
                    break
        else:
            tn.close()
        if screen is not None:
            return [screen, tn, host]
    except Exception:
        return False


def get_current_wifi_ssid():
    try:
        # 使用 netsh 命令获取当前连接的 WiFi 信息
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, check=True)

        # 解析输出，查找 SSID
        ssid_match = re.search(r'SSID\s+:\s+(.+)', result.stdout)
        if ssid_match:
            ssid = ssid_match.group(1).strip()
            return ssid

        return None  # 如果没有找到 SSID
    except subprocess.CalledProcessError:
        return None  # 如果命令执行失败


def detect_devices_thread(addresses, screen_info, screens, device_num):
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(scan_port, addresses, [23] * len(addresses))
        for result in results:
            if result:
                tmp = {"Screen": result[0], "Telnet": result[1], "IP": result[2]}
                if result[0] not in screens and result[0].strip() != "deviceId=":
                    screen_info.append(tmp)
                    screens.append(result[0])
                if result[0].strip() == "deviceId=":
                    print("发现无id设备，请找到屏幕并将其关闭")
                    return False
        if str(len(screen_info)) == "0":
            print("未发现设备")
            return False
        elif len(screen_info) >= device_num:
            return True
        else:
            return False


def the_second_detect_devices_thread(addresses, screen_info, screens, device_num, tns_ids):
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(scan_port, addresses, [23] * len(addresses))
        for result in results:
            if result:
                if result[0] in screens:
                    screens.remove(result[0])
                if result[0].strip() == "deviceId=":
                    tns_ids.append(result[1])
        if str(len(screen_info)) == "0":
            print("未发现设备")
            return False
        elif len(tns_ids) == device_num:
            print("设定的设备数量与检测到的无id设备数量一致")
            return True
        elif len(tns_ids) < device_num:
            print("设定的设备数量大于检测到的无id设备数量")
            return False
        else:
            print("设定的设备数量小于检测到的无id设备数量，请确认附近是否有其他无id的设备,若有请将其进行断电")
            return False


def main():
    while True:
        ssid = get_current_wifi_ssid()
        if "xiaomi" not in ssid:
            print("未连接到小米路由器，请将电脑WiFi连接至 【xiaomi】wifi")
            time.sleep(3)
            continue
        else:
            break
    print("已连接WiFi：【xiaomi】")
    while True:
        try:
            device_num = int(input("请输入需要扫描的设备数量:"))
            break
        except Exception:
            print("输入有误，请重新输入")
    screen_info = []
    screens = []
    tns_ids = []
    addresses = lan_ip_detect()
    addresses = [str(ip) for ip in addresses]
    while True:
        result = detect_devices_thread(addresses, screen_info, screens, device_num)
        if result:
            with open("screenId.ini", "w") as f:
                for i in screens:
                    f.write(i + "\n")
            break
        time.sleep(1)
    print("共检测到" + str(len(screen_info)) + f"个设备: {[{i['Screen']: i['IP']} for i in screen_info]}")
    while True:
        option = input("请开始烧录，烧录完后输入Y回车继续")
        try:
            if option.upper() == "Y":
                break
        except Exception:
            continue
    while True:
        result = the_second_detect_devices_thread(addresses, screen_info, screens, device_num, tns_ids)
        if result:
            break
        time.sleep(1)
    # 遍历 screens 将其中的id 写入到空id屏幕中
    print("id库：", screens)
    for screen_id, tn in zip(screens, tns_ids):
        screen_id = screen_id.split("=", 1)[1].strip()
        tn.write(b"echo '' > /customer/screenId.ini\n")
        tn.write(b"echo [screen] > /customer/screenId.ini\n")
        tn.write(b"echo deviceId=" + screen_id.encode('utf-8') + b" >> /customer/screenId.ini&& echo $?\n")
        tn.read_until(b"0", timeout=2)
        time.sleep(0.3)
        s = tn.read_very_eager().decode("utf-8")
        if "0" in s:
            print(f"已写入设备{screen_id}")
            tn.write(b"sync && /software/restart_bluetooth.sh\n")
            # 删除本地文件中的屏幕id
            with open("screenId.ini", "r", encoding='utf-8') as f:
                lines = [i.replace("\n", "") for i in (f.readlines())]
            for i in lines:
                if screen_id in i:
                    lines.remove(i)
            with open("screenId.ini", "w") as f:
                for i in lines:
                    f.write(i + "\n")

    input("所有屏幕id均已写入完成，按回车键退出")


if __name__ == '__main__':
    main()
