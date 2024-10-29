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
                pattern = r'deviceId=\s*(\s+)'
                match = re.search(pattern, s)
                tn.write(b"if [ $(wc -l < /customer/screenId.ini) -lt 2 ]; then echo $(ls /);fi\n")
                tn.read_until(b'appconfigs', timeout=0.5)
                pt = tn.read_very_eager().decode("utf-8")
                if match:
                    print("条件满足")
                    screen = match.group(0)
                    break
                elif 'upgrade' in pt:
                    screen = ""
                    break
        else:
            tn.close()
        if screen is not None:
            return [screen, tn, host]
    except Exception:
        return False


def rename_screenId(tn):
    tn_list = [i['Telnet'] for i in tn if 'Telnet' in i]
    host_list = [i['IP'] for i in tn if 'IP' in i]
    option = input("是否需要指定屏幕ID：\n1. 是\n2. 否")
    while True:
        if option not in ["1", "2"]:
            print("输入有误，请重新输入")
        else:
            break
    if option == "1":
        screen = input("请输入屏幕ID, 可以使用“空格”、“-”、“、”、“;”进行分隔：")
        pattern = r'[ \-\u3001;]'
        names = re.split(pattern, screen)
    else:
        names = []
        for i in tn:
            names.append("PinturaTest" + (str(time.time())[:6]))
    while True:
        if len(names) != len(tn):
            print("屏幕ID数量与检测到的设备数量不匹配，请重新输入设备id")
        else:
            break

    cmd_line1 = b' echo "" > /customer/screenId.ini\n'
    cmd_line2 = b'echo [screen] > /customer/screenId.ini\n'
    cmd_line3 = b'echo deviceId='
    for j, k, f in zip(tn_list, names, host_list):
        print(f"j：{j}, k：{k}, {cmd_line1}")
        j.write(cmd_line1)
        j.write(cmd_line2)
        cmd_line3 = cmd_line3 + k.encode('utf-8') + b' >> /customer/screenId.ini && echo $?\n'
        j.write(cmd_line3)
        j.read_until(b"0", timeout=2)
        time.sleep(0.3)
        s = j.read_very_eager().decode("utf-8")
        if "0" in s:
            print(f"已写入设备{k}, ip: {f}")
            j.write(b"sync && /software/restart_bluetooth.sh\n")
        j.close()







def main():
    screen_info = []
    addresses = lan_ip_detect()
    addresses = [str(ip) for ip in addresses]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(scan_port, addresses, [23] * len(addresses))
        for result in results:
            if result:
                screen_info.append({"Screen": result[0], "Telnet": result[1], "IP": result[2]})
    print(screen_info)
    if str(len(screen_info)) == "0":
        input("未发现设备")
        sys.exit()
    print("共检测到" + str(len(screen_info)) + "个设备")
    rename_screenId(screen_info)
    input("所有屏幕id均已写入完成，按回车键退出")



if __name__ == '__main__':
    main()
