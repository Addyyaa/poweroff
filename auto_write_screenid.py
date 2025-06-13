import ipaddress
import os
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
from http.server import HTTPServer, SimpleHTTPRequestHandler
import shutil
import threading

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)
current_host = None
network_ips = None 
mac_screen_id_dict = {}
first_detect_devices_result = {}
host_port = 9527
# 重新封装read和write
def indentify_tn(tn:telnetlib.Telnet):
    try:
        def read_until(match, timeout=None):
            try:
                # 确保 match 是字符串
                if not isinstance(match, str):
                    match = str(match)
                match = f"0-success-{match}".encode('utf-8')
                result = tn.read_until(match, timeout)
                if result:
                    result = result.decode("utf-8")
                return result
            except socket.error as e:
                # 不通的IP
                return False
    
        def write(command):
            try:
                # 执行命令前先发送回车检测是否需要登录
                tn.write(b'\n')
                result = tn.read_until(b'login:', 0.5)
                if b'login:' in result:
                    tn.write(b'root\n')
                    tn.read_until(b'password:', 1)
                    tn.write(b'ya!2dkwy7-934^\n')
                    tn.read_until(b'# ',1)
                # 确保 command 是字符串
                if not isinstance(command, str):
                    command = str(command)
                stamp = time.time()
                command = f"{command} && echo $?-success-{stamp}\n"
                tn.write(command.encode('utf-8'))
                time.sleep(1)
                return str(stamp)
            except socket.error as e:
                # 不通的IP
                return False
            except Exception as e:
                logging.error(f"写入命令时发生错误: {e}")
                return "其他问题"
        return read_until, write
    except Exception as e:
        logging.error(f"错误：{e}")
        return False

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

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        logging.error("获取本机IP失败")
        input("请按回车键退出程序")
        s.close()
        sys.exit()
    finally:
        s.close()
    return ip

current_host = get_local_ip()
logging.info(f"本机IP：{current_host}")

def lan_ip_detect():
    global current_host
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
        tn = telnetlib.Telnet(host, port, timeout=2)
        read_until, write = indentify_tn(tn)
        s = tn.read_until(b"login: ", timeout=2)
        index = tel_print(s)
        result = s[index::].decode("utf-8")
        if "login: " in result:
            tn.write(b"root\n")
            tn.read_until(b"password: ", timeout=2)
            tn.write(b"ya!2dkwy7-934^\n")
            tn.read_until(b"# ", timeout=2)
            wr = write("cat customer/screenId.ini")
            result1 = read_until(wr, 2)
            wr = write("cat /sys/class/net/wlan0/address")
            result2 = read_until(wr, 2)
            result = result1 + result2
            pattern = r'deviceId=([^\r\n]*)'
            pattern2 = r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'
            match = re.search(pattern, result)
            match2 = re.search(pattern2, result)
            if match is not None and match2 is not None:
                match_result1 = match.group(1)
                match_result2 = match2.group()
                return [match_result1, match_result2, host, tn]
        else:
            tn.close()
    except Exception as e:
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
                logging.info("已连接到小米路由器，请将电脑WiFi连接至 【NETGEAR12-5G】wifi")
                break
            if wifi not in ssid:
                logging.info("未连接到小米路由器，请将电脑WiFi连接至 【xiaomi】wifi")
                time.sleep(3)
                continue
            else:
                break
        logging.info("已连接WiFi：【xiaomi】")
    
    def check_is_new_version(tn: telnetlib.Telnet):
        read_until, write = indentify_tn(tn)
        rw = write("ls /tmp/app_versions && echo $?-app_versions")
        result = read_until(rw, 2)
        if "0-app_versions" in result:
            return True
        else:
            return False

    def ask_user_for_config():
        while True:
            try:
                device_num = input("请输入需要扫描的设备数量:")
                if device_num.isdigit():
                    device_num = int(device_num)
                else:
                    logging.error("输入有误，请重新输入")
                    continue
                break
            except Exception:
                logging.error("输入有误，请重新输入")
        return device_num
    mac = write_screen_id(check_wifi, ask_user_for_config)
    is_new_version = check_is_new_version(first_detect_devices_result[mac]['tn'])
    if mac and is_new_version:
        # id 烧录后开始绑定屏幕组
        retry_times = 3
        for i in range(retry_times):
            update_result = update_fw(first_detect_devices_result[mac]['tn'])  # 更新固件
            if update_result:
                logging.info("更新固件成功")
                break
            else:
                logging.error("更新固件失败")
                continue
        else:
            logging.error("更新固件失败，已重试三次")
        for i in range(retry_times):
            bind_result = bind_device(first_detect_devices_result[mac]['screen_id'])
            if bind_result:
                logging.info("绑定成功")
                break
            else:
                logging.error(f"绑定失败，正在重试（{i+1}/{retry_times}）")
                time.sleep(1)
        else:
            logging.error("绑定失败，已重试三次")
    elif not is_new_version:
        retry_times = 3
        for i in range(retry_times):
            bind_result = bind_device(first_detect_devices_result[mac]['screen_id'])
            if bind_result:
                logging.info("绑定成功")
                break
            else:
                logging.error(f"绑定失败，正在重试（{i+1}/{retry_times}）")
                time.sleep(1)
        else:
            logging.error("绑定失败，已重试三次")
        logging.info(f"{first_detect_devices_result[mac]["screen_id"]}\t已经烧录完成，请拔掉U盘")
    else:
        logging.error("烧录失败")

def write_screen_id(check_wifi, ask_user_for_config):
    device_num = False
    try: 
        check_wifi()
        while True:
            user_input = input("请输入屏幕的后六位数字（如需输入设备数量请输入 'num'）：").strip()
            if user_input.lower() == "num":
                device_num = ask_user_for_config()
                break
            else:
                try:
                    config_id = int(user_input)
                except Exception:
                    logging.error("输入有误，请重新输入")
                    continue
                break

        if not device_num:
            config_id = str(config_id)
            logging.info(f"强制检测的屏幕id：{config_id}")
            def scanner_config_device():
                try:
                    addresses = lan_ip_detect()
                    addresses = [str(ip) for ip in addresses]
                    while True:
                        first_detect_devices(addresses)
                        for mac_address in first_detect_devices_result:
                            if config_id in first_detect_devices_result[mac_address]["screen_id"]:
                                logging.info(f"已扫描到强制检测的屏幕id：{first_detect_devices_result[mac_address]['screen_id']}\t{first_detect_devices_result[mac_address]['ip']}")
                                return mac_address
                        logging.error("未扫描到强制检测的屏幕id，即将重试")
                except Exception as e:
                    logging.error(f"scanner_config_device错误：{e}")
                    return False
            
            mac = scanner_config_device()
            # 将屏幕信息保存下来防止程序意外关闭，找不到之前的屏幕id
            with open("resource/burnNote.txt", "w", encoding="utf-8") as f:
                device_info = first_detect_devices_result[mac]
                f.write(f"屏幕ID: {device_info['screen_id']}\n")
                f.write(f"IP地址: {device_info['ip']}\n")
                f.write(f"MAC地址: {mac}\n")
                f.write(f"保存时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            logging.info(f"设备信息已保存到 resource/burnNote.txt")
            
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
                try:
                    pre_ip = first_detect_devices_result[mac]['ip']
                    # 此时设备正在重启，还未连接WiFi，所以需要轮询连接
                    wait_index = 9
                    try_times = 3
                    while True:
                        try:
                            if try_times <= 0:
                                logging.warning("设备IP可能发生变更，重新扫描整个网络")
                                first_detect_devices(network_ips)
                                tn = first_detect_devices_result[mac]['tn']
                                break
                            tn = telnetlib.Telnet(pre_ip, 23, timeout=5)
                            try_times -= 1
                            first_detect_devices_result[mac]['tn'] = tn
                            break
                        except Exception as e:
                            wait_index = abs(wait_index - 2)
                            wait_time = wait_index ** 2
                            logging.warning(f"设备未上线，等待{wait_time}秒后重新尝试...")
                            time.sleep(wait_time)
                            continue
                    mac_address = get_device_mac_address(tn)
                    if mac_address == mac:
                        return tn
                    else:
                        logging.info(f"先前的设备ip：{pre_ip}，先前的mac：{mac}，当前的mac{mac_address}")
                        return False
                except Exception as e:
                    logging.error(f"juadge_the_current_is_the_dest_devices:{e}")
                    return False

            def write_screen_id(dest_tn):
                try:
                    read_until, write = indentify_tn(dest_tn)
                    cmd_list = ['echo "" > /customer/screenId.ini', 
                                f'echo [screen] > /customer/screenId.ini', 
                                f'echo deviceId={first_detect_devices_result[mac]['screen_id']} >> /customer/screenId.ini']
                    for cmd in (cmd_list):
                        rw = write(cmd)
                        result = read_until(rw, 60)
                        print_result = result.replace(" && echo $?-success-" + rw, "")
                        print_result = print_result.replace("0-success-" + rw, "")
                        logging.info(print_result)
                        if rw not in result:
                            return False
                    logging.info(f"屏幕id写入成功")
                    return True
                except Exception as e:
                    logging.error(f"write_screen_id{e}")
            def read_dest_mac_and_write_screenId():
                dest_tn = get_dest_tn(mac, juadge_the_current_is_the_dest_devices)
                read_until, write = indentify_tn(dest_tn)
                waitting_index = 7
                while True:
                    while True:
                        try:
                            rw = write("cat /sys/class/net/wlan0/address")
                            break
                        except Exception as e:
                            logging.info("设备系统未完全启动，等待启动重连")
                            time.sleep(abs(waitting_index) ** 2)
                            waitting_index -= 2

                    result = read_until(rw, 2)
                    logging.info(f"result: {result}")
                    if rw in result:
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
            

            if read_dest_mac_and_write_screenId():
                return mac
            else:
                return False

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
            logging.info(f"已扫描到{len(result)}\t{result}个设备")
    except Exception as e:
        logging.error(f"错误：{e}")

def update_fw(tn:telnetlib.Telnet):

    def start_http_server():
        server = HTTPServer(('0.0.0.0', host_port), SimpleHTTPRequestHandler)
        logging.info(f"Serving HTTP Enabled")
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        return server, thread

    def close_http_server(server, tmp_dir, original_dir):
        server.server_close()
        os.chdir(original_dir)
        os.remove(os.path.join(tmp_dir, "software_init.sh"))
        os.rmdir(tmp_dir)

    def create_tmp_dir():
        # 在程序所在位置创建临时目录
        current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        tmp_dir = os.path.join(current_dir, "tmp")
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        # 拷贝 software_init.sh 到 tmp 目录
        src_path = os.path.join(current_dir, "resource", "software_init.sh")
        dst_path = os.path.join(tmp_dir, "software_init.sh")
        shutil.copyfile(src_path, dst_path)
        os.chdir(tmp_dir)
        server, http_thread = start_http_server()
        # 返回原目录路径
        return server, http_thread, tmp_dir, current_dir

    def excuse_cmd(tn:telnetlib.Telnet):
        read_until, write = indentify_tn(tn)
        version_num = input("请输入版本号：")
        logging.info(f"开始更新固件")
        cmd_list = [
            "sed -i 's/FB_BUFFER_LEN[[:space:]]*=[[:space:]]*[0-9]*/FB_BUFFER_LEN = 9000/' /config/fbdev.ini",
            "mkdir -p /customer/tmp",
            "cd /customer/tmp",
            "tar -xvf /upgrade/restore/SStarOta.bin.gz",
            f"awk -F '=' '$2 !~ /^[[:space:]]*$/ {{gsub(/^[[:space:]]+|[[:space:]]+$/, \"\", $2); $2=\"{version_num}\"; print $1 \"=\" $2}} $2 ~ /^[[:space:]]*$/ {{print $0}}' /software/version.ini > temp.ini && mv temp.ini /software/version.ini",
            f"awk -F '=' '$2 !~ /^[[:space:]]*$/ {{gsub(/^[[:space:]]+|[[:space:]]+$/, \"\", $2); $2=\"{version_num}\"; print $1 \"=\" $2}} $2 ~ /^[[:space:]]*$/ {{print $0}}' ./version.ini > temp.ini && mv temp.ini ./version.ini",
            "cd ./script",
            "rm ./software_init.sh",
            f"wget http://{current_host}:{host_port}/software_init.sh",
            "chmod +x ./software_init.sh",
            "cd ..",
            "tar -czvf SStarOta.bin.gz ./*",
            "mv ./SStarOta.bin.gz /upgrade/restore/SStarOta.bin.gz",
            "rm -rf /customer/tmp",
            "md5sum /upgrade/restore/SStarOta.bin.gz | awk '{print $1}' > /upgrade/restore/rst_md5",
            "sync"
        ]

        for cmd in (cmd_list):
            rw = write(cmd)
            result = read_until(rw, 60)
            print_result = result.replace(" && echo $?-success-" + rw, "")
            print_result = print_result.replace("0-success-" + rw, "")
            logging.info(f"Addy: {print_result}")
            if rw in result:
                continue
            else:
                logging.error(f"命令未成功: {cmd.strip()}")
                return False
        return True

    # 开启httpd服务
    server, http_thread, tmp_dir, original_dir = create_tmp_dir()
    # 更新固件
    for i in range(3):
        exc_result = excuse_cmd(tn)
        if exc_result:
            time.sleep(10)
            tn.write(b"exit\n")
            # 关闭http服务
            server.shutdown()
            http_thread.join()
            close_http_server(server, tmp_dir, original_dir)
            return True
        else:
            time.sleep(1)
            continue
    else:
        logging.error("更新固件失败")
        # 关闭http服务
        server.shutdown()
        http_thread.join()
        close_http_server(server, tmp_dir, original_dir)
        return False
    

def get_dest_tn(mac, juadge_the_current_is_the_dest_devices):
    while True:
        dest_tn = juadge_the_current_is_the_dest_devices()
        if dest_tn:
            return dest_tn
        else:
           try:
             logging.info("设备IP发生改变")
             dest_tn = scan_device_which_need_write_screenid(mac)
           except Exception as e:
            logging.error(f"错误2{e}")

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
    read_until, write = indentify_tn(tn)
    try:
        rw = write("cat /sys/class/net/wlan0/address && echo $?-success")
    except Exception as e:
        logging.error(f"get_device_mac_address错误：{e}")
        return False
    result = read_until(rw, 2)
    if rw in result:
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
