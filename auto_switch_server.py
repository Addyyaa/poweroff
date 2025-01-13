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
import psutil

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
    gateways = netifaces.gateways()
    gateway = gateways['default'][2][0]
    addresses = []
    # 获取网络接口状态
    stats = psutil.net_if_stats()
    # 获取所有网络接口地址信息
    for interface, addrs in psutil.net_if_addrs().items():
        # 检查接口是否是活动的
        if interface in stats and stats[interface].isup:
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    addresses.append({f'{interface}': addr.address, 'netmask': addr.netmask})
    ipv4 = addresses
    address = ''
    for i in ipv4:
        if "wlan" in str(i.keys()).lower() or 'eth' in str(i.keys()).lower() or '本地连接' in i.keys() or 'lan' in str(
                i.keys()).lower():
            address = i
            break
        else:
            address = ipv4[0]
            break
    address = dict(address)
    network = list(ipaddress.IPv4Network(f"{gateway}/{address['netmask']}", strict=False).hosts())
    return network


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


def modify_location(screen: str, tn: telnetlib.Telnet, host: str, version: str):
    times1 = 0
    times2 = 0
    while True:
        if version == "1":
            tn.write(b"echo [local] > /software/local.ini \n")
            tn.write(b"echo local=1 >> /software/local.ini \n")
            tn.write(b'echo [mqtt] >  /software/mqtt.ini \n')
            tn.write(b'echo cn_host=cloud-service.austinelec.com >>  /software/mqtt.ini \n')
            tn.write(b'echo cn_port=1883 >>  /software/mqtt.ini \n')
            tn.write(b'echo en_host=cloud-service-us.austinelec.com >>  /software/mqtt.ini \n')
            tn.write(b'echo en_port=1883 >>  /software/mqtt.ini \n')
            tn.write(b'sync\n')
            tn.write(b"cat /software/mqtt.ini | grep cloud-service.austinelec.com\n")
            while True:
                result = get_latest_print(tn)
                if result:
                    if b'cn_host=cloud-service.austinelec.com' in result:
                        print(f"设备：{host} \t{screen}服务地址已更改")
                        break
                    else:
                        print(f"设备：{host} 服务地址更改失败")
                        if times1 >= 10:
                            print(f'设备{host}多次切换失败请联系售后')
                            sys.exit()
                        times1 += 1
                        continue
            tn.write(b'cat /software/local.ini | grep 1\n')
            result = get_latest_print(tn)
            if result:
                if b'local=1' in result:
                    print(f"设备：{host} 配置1已更改")
                    break
                else:
                    print(f"设备：{host} 配置1更改失败")
                    if times1 >= 10:
                        print(f'设备{host}多次切换失败请联系售后')
                        sys.exit()
                    times1 += 1
                    continue
            else:
                print(f"设备：{host} 未获取到结果即将重新尝试")
                if times1 >= 10:
                    print(f'设备{host}多次切换失败请联系售后')
                    sys.exit()
                continue
        elif version == '2':
            tn.write(b"echo [local] > /software/local.ini \n")
            tn.write(b"echo local=2 >> /software/local.ini \n")
            tn.write(b'sync\n')
            tn.write(b'cat /software/local.ini | grep 2\n')
            result = get_latest_print(tn)
            if result:
                if b'local=2' in result:
                    print(f"设备：{host} 配置1已更改")
                    break
                else:
                    print(f"设备：{host} 配置1更改失败")
                    if times1 >= 10:
                        print(f'设备{host}多次切换失败请联系售后')
                        sys.exit()
                    times1 += 1
                    continue
            else:
                print(f"设备：{host} 未获取到结果即将重新尝试")
                if times1 >= 10:
                    print(f'设备{host}多次切换失败请联系售后')
                    sys.exit()
                continue

        else:
            input("选项错误")
            sys.exit()
    while True:
        if version == "1":
            tn.write(b"echo [local] > /upgrade/local.ini \n")
            tn.write(b"echo local=1 >> /upgrade/local.ini \n")
            tn.write(b'sync\n')
            tn.write(b'cat /upgrade/local.ini | grep 1\n')
            result = get_latest_print(tn)
            if result:
                if b'local=1' in result:
                    print(f"设备：{host} 配置2已更改")
                    break
                else:
                    print(f"设备：{host} 配置2更改失败")
                    if times2 >= 10:
                        print(f'设备{host}多次切换失败请联系售后')
                        sys.exit()
                    times2 += 1
                    continue
            else:
                print(f"设备：{host} 未获取到结果即将重新尝试")
                if times2 >= 10:
                    print(f'设备{host}多次切换失败请联系售后')
                    sys.exit()
                continue
        elif version == '2':
            tn.write(b"echo [local] > /upgrade/local.ini \n")
            tn.write(b"echo local=2 >> /upgrade/local.ini \n")
            tn.write(b'sync\n')
            tn.write(b'cat /upgrade/local.ini | grep 2\n')
            result = get_latest_print(tn)
            if result:
                if b'local=2' in result:
                    print(f"设备：{host} 配置2已更改")
                    break
                else:
                    print(f"设备：{host} 配置2更改失败")
                    if times2 >= 10:
                        print(f'设备{host}多次切换失败请联系售后')
                        sys.exit()
                    times2 += 1
                    continue
            else:
                print(f"设备：{host} 未获取到结果即将重新尝试")
                if times2 >= 10:
                    print(f'设备{host}多次切换失败请联系售后')
                    sys.exit()
                continue
        else:
            input("选项错误")
            sys.exit()
    print(f"设备：{host} 切换成功,建议重启屏幕")
    tn.write(b"kill $(pidof mymqtt) &\n")


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


def modify_server(screen: str, tn: telnetlib.Telnet, host: str, option: str):
    if option == "1":
        # tn.write(b"echo [mqtt] >  /software/mqtt.ini \n")
        # tn.write(b'echo cn_host=cloud-service.austinelec.com >>  /software/mqtt.ini \n')
        # tn.write(b'echo cn_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_host=cloud-service.austinelec.com >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'sync\n')
        cmd = ['echo [mqtt] >  /software/mqtt.ini ', 'echo cn_host=cloud-service.austinelec.com >>  /software/mqtt.ini',
               'echo cn_port=1883 >>  /software/mqtt.ini',
               'echo en_host=cloud-service.austinelec.com >>  /software/mqtt.ini',
               'echo en_port=1883 >>  /software/mqtt.ini', 'sync',
               'cat /software/mqtt.ini | grep cloud-service.austinelec.com']
        result = cmd_check(tn, cmd, "cloud-service.austinelec.com")
        if result:
            print(f"设备：{host} \t{screen}服务地址已更改")
        else:
            input(f"设备：{host} 服务地址更改失败，按回车退出程序")
            sys.exit()
    elif option == "2":
        # tn.write(b"echo [mqtt] >  /software/mqtt.ini \n")
        # tn.write(b'echo cn_host=cloud-service-us.austinelec.com >>  /software/mqtt.ini \n')
        # tn.write(b'echo cn_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_host=cloud-service-us.austinelec.com >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'sync\n')
        cmd = ['echo [mqtt] >  /software/mqtt.ini ',
               'echo cn_host=cloud-service-us.austinelec.com >>  /software/mqtt.ini',
               'echo cn_port=1883 >>  /software/mqtt.ini',
               'echo en_host=cloud-service-us.austinelec.com >>  /software/mqtt.ini',
               'echo en_port=1883 >>  /software/mqtt.ini', 'sync',
               'cat /software/mqtt.ini | grep cloud-service-us.austinelec.com']
        result = cmd_check(tn, cmd, "cloud-service-us.austinelec.com")
        if result:
            print(f"设备：{host} \t{screen}服务地址已更改")
        else:
            input(f"设备：{host} 服务地址更改失败，按回车退出程序")
            sys.exit()
    elif option == "3":
        # tn.write(b"echo [mqtt] >  /software/mqtt.ini \n")
        # tn.write(b'echo cn_host=139.224.192.36 >>  /software/mqtt.ini \n')
        # tn.write(b'echo cn_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_host=139.224.192.36 >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'sync\n')
        cmd = ['echo [mqtt] >  /software/mqtt.ini ', 'echo cn_host=139.224.192.36 >>  /software/mqtt.ini',
               'echo cn_port=1883 >>  /software/mqtt.ini', 'echo en_host=139.224.192.36 >>  /software/mqtt.ini',
               'echo en_port=1883 >>  /software/mqtt.ini', 'sync', 'cat /software/mqtt.ini | grep 139.224.192.36']
        result = cmd_check(tn, cmd, "139.224.192.36")
        if result:
            print(f"设备：{host} \t{screen}服务地址已更改")
        else:
            input(f"设备：{host} 服务地址更改失败，按回车退出程序")
            sys.exit()
    elif option == "4":
        # tn.write(b"echo [mqtt] >  /software/mqtt.ini \n")
        # tn.write(b'echo cn_host=18.215.241.226 >>  /software/mqtt.ini \n')
        # tn.write(b'echo cn_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_host=18.215.241.226 >>  /software/mqtt.ini \n')
        # tn.write(b'echo en_port=1883 >>  /software/mqtt.ini \n')
        # tn.write(b'sync\n')
        cmd = ['echo [mqtt] >  /software/mqtt.ini ', 'echo cn_host=18.215.241.226 >>  /software/mqtt.ini',
               'echo cn_port=1883 >>  /software/mqtt.ini', 'echo en_host=18.215.241.226 >>  /software/mqtt.ini',
               'echo en_port=1883 >>  /software/mqtt.ini', 'sync', 'cat /software/mqtt.ini | grep 18.215.241.226']
        result = cmd_check(tn, cmd, "18.215.241.226")
        if result:
            print(f"设备：{host} \t{screen}服务地址已更改")
        else:
            input(f"设备：{host} 服务地址更改失败，按回车退出程序")
            sys.exit()
    else:
        input("选项错误")
    print(f"设备：{host}\t{screen} 切换成功,建议重启屏幕")
    tn.write(b"kill $(pidof mymqtt) &\n")


addresses = lan_ip_detect()
port = 23
screen_list = []
tn_list = []
host_list = []
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
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
        print(f"\n发现以下屏幕：")
        for index, (item_a, item_b) in enumerate(zip(screen_list, host_list)):
            print(f"{index + 1}. {item_a}：\t{item_b}")
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

    while True:
        option = input('请选择操作：\n1. 切换服务地址\n2. 切换版本\n请选择: ')
        if option not in ["1", "2"]:
            print("选项错误，请重新输入")
            continue
        else:
            break

    if option == "1":
        while True:
            server = input(
                "\n请选择要切换的服务地址：\n1. 正式环境-国内\n2. 正式环境-美国\n3. 测试环境-国内\n4. 测试环境-国外2\n注意：工厂版本和预发布版本只需要切换到对应的服务器即可\n请选择: ")
            if server not in ["1", "2", "3", "4"]:
                print("选项错误，请重新输入")
                continue
            else:
                break
        modify_server(screen, tn, host, server)
        future = [executor.submit(modify_server, screen, tn, host, server) for screen, tn, host in
                  zip(operate_screen, operate_tn, operate_host)]
        concurrent.futures.wait(future)
        while True:
            continue_opterate = input('是否要进行版本切换？\n1. 是\n2. 否\n请选择: ')
            if continue_opterate not in ["1", "2"]:
                print("选项错误，请重新输入")
                continue
            else:
                if continue_opterate == "2":
                    sys.exit()
                else:
                    break

    while True:
        version = input("\n请选择要切换的版本：\n1. 中国\n2. 美国\n请选择: ")
        if version not in ["1", "2"]:
            print("选项错误，请重新输入")
            continue
        else:
            break
    future = [executor.submit(modify_location, screen, tn, host, version) for screen, tn, host in
              zip(operate_screen, operate_tn, operate_host)]
    concurrent.futures.wait(future)
    input("切换完成!!!按回车键退出程序")
