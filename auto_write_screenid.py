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
from login import Login
import requests
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

def netmask_to_int(netmask):
    # 利用 ipaddress 模块将子网掩码转为整数
    return int(ipaddress.IPv4Address(netmask))

def lan_ip_detect():
    gateways = netifaces.gateways()
    gateway = gateways['default'][2][0]
    addresses = []
    # 获取网络接口状态
    stats = psutil.net_if_stats()
    # 获取所有网络接口地址信息
    for interface, addrs in psutil.net_if_addrs().items():
        # 检查接口是否是活动的
        if interface in stats:
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    addresses.append({f'{interface}': addr.address, 'netmask': addr.netmask})
    ipv4 = addresses
    netmast = max(ipv4, key=lambda x: netmask_to_int(x['netmask']))['netmask']
    network = list(ipaddress.IPv4Network(f"{gateway}/{netmast}", strict=False).hosts())
    return network


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
    # wifi = input("请输入烧录环境的WiFi名：")
    wifi = "xiaomi"
    wifi_sec = "NETGEAR12-5G"
    try:
        config = False
        while True:
            ssid = get_current_wifi_ssid()
            if wifi_sec in ssid:
                print("已连接到小米路由器，请将电脑WiFi连接至 【NETGEAR12-5G】wifi")
                break
            if wifi not in ssid:
                print("未连接到小米路由器，请将电脑WiFi连接至 【xiaomi】wifi")
                time.sleep(3)
                continue
            else:
                break
        print("已连接WiFi：【xiaomi】")
        while True:
            try:
                device_num = input("请输入需要扫描的设备数量:")
                if device_num == "config":
                    config = True
                    break
                device_num = int(device_num)
                break
            except Exception:
                print("输入有误，请重新输入")
        if config:
            while True:
                try:
                    config_id = input("请输入强制检测的屏幕id， 以空格进行分割（注：强制检测会一直检测直到扫描到屏幕）：")
                    # int(config_id)   # 开启数字校验
                    break
                except Exception:
                    print("输入有误，请重新输入屏幕的后六位数字")
                    continue
            config_id = str(config_id).split()
            device_num = len(config_id)
        addresses = lan_ip_detect()
        addresses = [str(ip) for ip in addresses]
        while True:
            tns_ids = []
            screens = []
            scaned_conifg_id = []
            screen_info = []
            result = detect_devices_thread(addresses, screen_info, screens, device_num)
            if result:
                if config:
                    for i in config_id:
                        for j in screens:
                            if i == j[-(len(i)):]:
                                scaned_conifg_id.append(j)
                    if len(config_id) != len(scaned_conifg_id):
                        continue
                    print(f"强制检测模式，正在扫描屏幕：{config_id}，已扫描={scaned_conifg_id}")
                    print(f"已扫描到的强制检测屏幕id：{scaned_conifg_id}，以及准备用来烧录的id：{screens}")
                with open("screenId.ini", "w") as f:
                    print("写入屏幕id：" + str(screens))
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
        with open("screenId.ini", "r", encoding='utf-8') as f:
            lines = [i.replace("\n", "") for i in (f.readlines())]
        # 遍历 screens 将其中的id 写入到空id屏幕中
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
                for i in lines:
                    if screen_id in i:
                        lines.remove(i)
        with open("screenId.ini", "w") as f:
            for i in lines:
                f.write(i + "\n")
        try_times = 0
        while True:
            if try_times >= 3:
                logging.error("绑定失败，手动配网创建屏幕组后注册设备")
                break
            regist_result = bind_device(screen_id)
            try_times += 1
            if regist_result:
                break
            else:
                time.sleep(10)
        

        input("所有屏幕id均已写入完成，按回车键退出")
    except KeyboardInterrupt:
        with open("screenId.ini", "w") as f:
            for i in lines:
                f.write(i + "\n")

def bind_device(screen_id: str):
    token = Login("15250996938", "sf123123").login()
    logging.info(f"获取到token：{token}")
    domain = "cloud-service-us.austinelec.com"
    port = "8080"
    headers = {
        "Content-Type": "application/json",
        "X-TOKEN": token
    }
    screen_group_id = None
    def add_screen_group():
        # 绑定屏幕组
        api = f"http://{domain}:{port}/api/v1/host/screen/group/add"
        bind_data = {
            "screenGroupName": "burnTmp",
            "screenIdList": [screen_id],
            "type": 2
        }
        response = requests.post(api, json=bind_data, headers=headers)
        if response.status_code == 200 and response.json()["code"] == 20:
            screen_group_id = response.json()["data"]
            return screen_group_id
        else:
            logging.error(f"绑定屏幕组失败：{response.json()}")
            return False
    
    def delete_screen_group():
        api = f"http://{domain}:{port}/api/v1/host/screen/group/del"
        delete_data = {
            "screenGroupId": screen_group_id,
            "screenIdList": [],
            "isDelGroup": 1
        }
        response = requests.post(api, json=delete_data, headers=headers)
        if response.status_code == 200 and response.json()["code"] == 20:
            return True
        else:
            logging.error(f"删除屏幕组失败：{response.json()}")
            return False
        
    def init_device_info():
        api = f"http://{domain}:{port}/api/v1/screenVideo/extend/{screen_id}"
        response = requests.get(api, headers=headers)
        if response.status_code == 200 and response.json()["code"] == 20:
            data = response.json()["data"]
            if "totalStorage" in data and data["totalStorage"] > 0:
                logging.info(f"{screen_id}设备注册成功")
                return True
            else:
                logging.error(f"非64GB设备，请检查：{data}")
                return False
        else:
            logging.error(f"获取设备信息失败：{response.json()["data"]}")
            return False
    screen_group_id = add_screen_group()
    if screen_group_id:
        if init_device_info():
            if not delete_screen_group():
                logging.info(f"{screen_id}设备注册成功，但删除屏幕组失败")
            return True
        else:
            delete_screen_group()
            return False
    else:
        return False

    
    

if __name__ == '__main__':
    main()
    # screenId = "PS91d7ecLtest20"
    # if bind_device(screenId):
    #     print("绑定成功")
    # else:
    #     print("绑定失败")
