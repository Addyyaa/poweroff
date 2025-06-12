import ipaddress
import socket
import subprocess
import sys
import telnetlib
import logging
import time
import re
from typing import Union
import netifaces
import concurrent.futures
from login import Login
import requests
import psutil

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)
network_ips = None 
mac_screen_id_dict = {}
first_detect_devices_result = {}

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
    global network_ips
    network_ips = network
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
            tn.write(b"cat /sys/class/net/wlan0/address && echo $?-success\n")
            start_time = time.time()
            # 循环防止未来得及读取到屏幕id的情况
            while True:
                if time.time() - start_time > 10:
                    break
                time.sleep(0.3)
                s = tn.read_very_eager().decode("utf-8")
                pattern = r'deviceId=([^\r\n]*)'
                pattern2 = r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'
                match = re.search(pattern, s)
                match2 = re.search(pattern2, s)
                if match is not None and match2 is not None:
                    match_result1 = match.group(1)
                    match_result2 = match2.group()
                    return [match_result1, match_result2, host, tn]
        else:
            tn.close()
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

def scan_device_which_need_write_screenid(dest_mac_address:str):
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(scan_port, ip, 23) for ip in network_ips]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                screen_id, mac_address, ip, tn = result
                if mac_address == dest_mac_address:
                    return [screen_id, ip, tn]
    return False

def first_detect_devices(addresses:list) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(scan_port, ip, 23) for ip in addresses]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                global first_detect_devices_result
                screen_id, mac_address, ip, tn = result
                first_detect_devices_result[mac_address] = {"screen_id": screen_id, "ip": ip, "tn": tn}
                mac_screen_id_dict[mac_address] = {"screen_id": screen_id, "ip": ip, "tn": tn}
    return first_detect_devices_result
    

def main():
    # wifi = input("请输入烧录环境的WiFi名：")
    config = False
    def check_wifi():
        wifi = "xiaomi"
        wifi_sec = "NETGEAR12-5G"
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
    
    def ask_user_for_config():
        while True:
            try:
                device_num = input("请输入需要扫描的设备数量:")
                if device_num == "config":
                    return False
                elif device_num.isdigit():
                    device_num = int(device_num)
                else:
                    print("输入有误，请重新输入")
                    continue
                break
            except Exception:
                print("输入有误，请重新输入")
        return device_num
    mac = write_screen_id(check_wifi, ask_user_for_config)
    if mac:
        # id 烧录后开始绑定屏幕组
        retry_times = 3
        for i in range(retry_times):
            bind_result = bind_device(first_detect_devices_result[mac]['screen_id'])
            if bind_result:
                logging.error("绑定成功")
                break
            else:
                logging.error(f"绑定失败，正在重试（{i+1}/{retry_times}）")
                time.sleep(1)
        else:
            logging.error("绑定失败，已重试三次")
    else:
        print("烧录失败")

def write_screen_id(check_wifi, ask_user_for_config):
    try: 
        check_wifi()
        device_num = ask_user_for_config()
        if not device_num:
            config = True
        else:
            config = False

        if config:
            while True:
                try:
                    config_id = input("请输入强制检测的屏幕id， 以空格进行分割（注：强制检测会一直检测直到扫描到屏幕）：")
                    # int(config_id)   # 开启数字校验 
                    break
                except Exception:
                    print("输入有误，请重新输入屏幕的后六位数字")
                    continue
            config_id = str(config_id)
            def scanner_config_device():
                addresses = lan_ip_detect()
                addresses = [str(ip) for ip in addresses]
                while True:
                    first_detect_devices(addresses)
                    for mac_address in first_detect_devices_result:
                        if config_id in first_detect_devices_result[mac_address]["screen_id"]:
                            print(f"已扫描到强制检测的屏幕id：{first_detect_devices_result[mac_address]['screen_id']}\t{first_detect_devices_result[mac_address]['ip']}")
                            return mac_address
                    print("未扫描到强制检测的屏幕id，即将重试")
            
            mac = scanner_config_device()
            def ask_for_start():
                while True:
                    start_burn = str(input("是否开始烧录：(y/n)"))
                    if start_burn.upper() in ['Y', 'N']:
                        if start_burn.upper() == 'Y':
                            break 
                        else:
                            continue
                    else:
                        logging.error("输入有误请重新输入")
            ask_for_start()

            def juadge_the_current_is_the_dest_devices():
                tn = first_detect_devices_result[mac]['tn']
                mac_address = get_device_mac_address(tn)
                if mac_address == mac:
                    return tn
                else:
                    return False

            def write_screen_id(dest_tn):
                cmd_list = ['echo "" > /customer/screenId.ini && echo $?-success-clear\n', f'echo [screen] > /customer/screenId.ini && echo $?-success-echo[screen]\n', f'echo deviceId={first_detect_devices_result[mac]['screen_id']} >> /customer/screenId.ini && echo $?-success-echo-screenID\n']
                cmd_check_keyword = ['0-success-clear', '0-success-echo[screen]', '0-success-echo-screenID']
                for index, cmd in enumerate(cmd_list):
                    dest_tn.write(cmd.encode('utf-8'))
                    result = dest_tn.read_until(cmd_check_keyword[index].encode('utf-8'), timeout=5).decode("utf-8")
                    if cmd_check_keyword[index] not in result:
                        return False
                return True
            def read_dest_mac_and_write_screenId():
                dest_tn = get_dest_tn(mac, juadge_the_current_is_the_dest_devices)
                while True:
                    dest_tn.write(b"cat /sys/class/net/wlan0/address && echo $?-success-read-mac\n")
                    result = dest_tn.read_until(b"0-success-read-mac", timeout=1).decode("utf-8")
                    if "0-success-read-mac" in result:
                        try_times = 3
                        while True:
                            if write_screen_id(dest_tn):
                                break
                            else:
                                try_times -= 1
                                if try_times <= 0:
                                    logging.error("屏幕id写入失败，请检查设备是否正常")
                                    input("请按回车键退出程序")
                                    sys.exit()
                        return True
                    else:
                        time.sleep(3)
                        continue
            
            try:
                if read_dest_mac_and_write_screenId():
                    return mac
                else:
                    return False
            except Exception as e:
                logging.error(f"错误：{e}")
        else:
            # 执行扫描指定数量的设备
            addresses = lan_ip_detect()
            addresses = [str(ip) for ip in addresses]
            
            while True:
                result = first_detect_devices(addresses)
                if len(result.keys()) >= device_num:
                    return
                else:
                    time.sleep(1)
                    continue
            print(f"已扫描到{len(result)}\t{result}个设备")
    except Exception as e:
        logging.error(f"错误：{e}")



def get_dest_tn(mac, juadge_the_current_is_the_dest_devices):
    while True:
        dest_tn = juadge_the_current_is_the_dest_devices()
        if dest_tn:
            return dest_tn
        else:
            dest_tn = scan_device_which_need_write_screenid(mac)
            if dest_tn:
                return dest_tn
            else:
                time.sleep(1)
                continue

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
                input("请按回车键退出程序")
                sys.exit()
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

def get_device_mac_address(tn:telnetlib.Telnet):
    tn.write(b"cat /sys/class/net/wlan0/address && echo $?-success\n")
    result = tn.read_until(b"0-success", timeout=1).decode("utf-8")
    if "0-success" in result:
        pattern = r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'
        match = re.search(pattern, result)
        if match:
            return match.group()
        else:
            return False
    else:
        return False

    

if __name__ == '__main__':
    main()
