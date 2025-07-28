import ipaddress
import socket
import sys
import io
import telnetlib
import logging
import time
import re
from typing import Union
import concurrent.futures
import netifaces
import psutil

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)
# 强制设置 stdout 使用 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
cn_server_release = "cloud-service.austinelec.com"
cn_server_test = "139.224.192.36"
en_server_release = "cloud-service-us.austinelec.com"
en_server_test = "18.215.241.226"
mqtt_port = 1883
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


# 将 netmask 转换为整数
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

def is_new_firmware(tn: telnetlib.Telnet) -> bool:
    tn.write(b"ls /tmp/app_versions && echo $?\n")
    time.sleep(1)
    result = tn.read_very_eager().decode('utf-8')
    if '0' in result:
        return True
    else:
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
            tn.read_until(b"login: can't chdir to home directory '/home/root'", timeout=2)
            tn.write(b"cat customer/screenId.ini\n")
            # 循环防止未来得及读取到屏幕id的情况
            max_attempts = 3  # 最大尝试次数
            attempts = 0
            while attempts < max_attempts:
                time.sleep(0.3)
                s = tn.read_very_eager().decode("utf-8")
                pattern = r"deviceId=\s*(\w+)"
                match = re.search(pattern, s)
                if match:
                    screen = match.group(1)
                    break
                attempts += 1
            else:
                # 如果超过最大尝试次数仍未找到deviceId，关闭连接并返回False
                logging.warning(f"主机 {host} 未能获取到deviceId，跳过此设备")
                tn.close()
                return False
            return [screen, tn, host]
        else:
            tn.close()
        
    except Exception:
        return False


def modify_location(screen: str, tn: telnetlib.Telnet, host: str, option: str):
    times1 = 0
    times2 = 0
    
    # 检查是否是新的版本固件
    is_new_fw, mqtt_ini, mqtt_log, local_ini = set_config(tn)
    local_value = "1"
    mqtt_prefix = "echo [mqtt]"
    cn_mqtt_value_prefix = "echo cn_host="
    en_mqtt_value_prefix = "echo en_host="
    port_section = "echo [http]"
    cn_port_prefix = "echo cn_port="
    en_port_prefix = "echo en_port="
    cn_port_value = "8080" 
    en_port_value = "8080"
    local_prefix = "echo [local]"
    local_value_prefix = "echo local="
    old_local_ini_path = "/upgrade/local.ini"
    selected_server = ""
    while True:
        if times1 >= 10:
            logging.error(f"版本切换失败，请重新尝试或者联系售后")
            break
        if option == "1":
            selected_server = cn_server_release
            tn.write(f"{mqtt_prefix} > {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{cn_mqtt_value_prefix}{cn_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{en_mqtt_value_prefix}{en_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{local_prefix} > {local_ini}\n".encode('utf-8'))
            tn.write(f"{local_value_prefix}{local_value} >> {local_ini}\n".encode('utf-8'))
            if not is_new_fw: 
                tn.write(f"{local_prefix} > {old_local_ini_path}\n".encode('utf-8'))
                tn.write(f"{local_value_prefix}{local_value} >> {old_local_ini_path}\n".encode('utf-8'))
        elif option == "2":
            selected_server = en_server_release
            local_value = "2"
            tn.write(f"{mqtt_prefix} > {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{cn_mqtt_value_prefix}{cn_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{en_mqtt_value_prefix}{en_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{local_prefix} > {local_ini}\n".encode('utf-8'))
            tn.write(f"{local_value_prefix}{local_value} >> {local_ini}\n".encode('utf-8'))
            if not is_new_fw:
                tn.write(f"{local_prefix} > {old_local_ini_path}\n".encode('utf-8'))
                tn.write(f"{local_value_prefix}{local_value} >> {old_local_ini_path}\n".encode('utf-8'))
        elif option == "3":  # 大陆版，但是要是英语 
            selected_server = cn_server_release
            tn.write(f"{mqtt_prefix} > {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{cn_mqtt_value_prefix}{en_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{en_mqtt_value_prefix}{cn_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            # 将location改为2
            local_value = "2"
            tn.write(f"{local_prefix} > {local_ini}\n".encode('utf-8'))
            tn.write(f"{local_value_prefix}{local_value} >> {local_ini}\n".encode('utf-8'))
            if not is_new_fw:
                tn.write(f"{local_prefix} > {old_local_ini_path}\n".encode('utf-8'))
                tn.write(f"{local_value_prefix}{local_value} >> {old_local_ini_path}\n".encode('utf-8'))
        elif option == "4":  # 海外版，但是要是中文
            selected_server = en_server_release
            tn.write(f"{mqtt_prefix} > {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{cn_mqtt_value_prefix}{en_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{en_mqtt_value_prefix}{cn_server_release} >> {mqtt_ini}\n".encode('utf-8'))
            # 将location改为1
            local_value = "1"
            tn.write(f"{local_prefix} > {local_ini}\n".encode('utf-8'))
            tn.write(f"{local_value_prefix}{local_value} >> {local_ini}\n".encode('utf-8'))
            if not is_new_fw:
                tn.write(f"{local_prefix} > {old_local_ini_path}\n".encode('utf-8'))
                tn.write(f"{local_value_prefix}{local_value} >> {old_local_ini_path}\n".encode('utf-8'))
        elif option == "5":  # 国内测试环境
            selected_server = cn_server_test
            tn.write(f"{mqtt_prefix} > {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{cn_mqtt_value_prefix}{cn_server_test} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{en_mqtt_value_prefix}{en_server_test} >> {mqtt_ini}\n".encode('utf-8'))
            # 将location改为1
            local_value = "1"
            tn.write(f"{local_prefix} > {local_ini}\n".encode('utf-8'))
            tn.write(f"{local_value_prefix}{local_value} >> {local_ini}\n".encode('utf-8'))
            if not is_new_fw:
                tn.write(f"{local_prefix} > {old_local_ini_path}\n".encode('utf-8'))
                tn.write(f"{local_value_prefix}{local_value} >> {old_local_ini_path}\n".encode('utf-8'))
        else: # 海外测试环境
            selected_server = en_server_test
            tn.write(f"{mqtt_prefix} > {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{cn_mqtt_value_prefix}{cn_server_test} >> {mqtt_ini}\n".encode('utf-8'))
            tn.write(f"{en_mqtt_value_prefix}{en_server_test} >> {mqtt_ini}\n".encode('utf-8'))
            # 将location改为2
            local_value = "2"
            tn.write(f"{local_prefix} > {local_ini}\n".encode('utf-8'))
            tn.write(f"{local_value_prefix}{local_value} >> {local_ini}\n".encode('utf-8'))
            if not is_new_fw:
                tn.write(f"{local_prefix} > {old_local_ini_path}\n".encode('utf-8'))
                tn.write(f"{local_value_prefix}{local_value} >> {old_local_ini_path}\n".encode('utf-8'))
        
        # 兼容云同步版本增加了http端口
        if is_new_fw:
            if option not in ["1", "2", "3", "4"]:
                cn_port_value = "8082"
                tn.write(f"{port_section} >> {mqtt_ini}\n".encode('utf-8'))
                tn.write(f"{cn_port_prefix}{cn_port_value} >> {mqtt_ini}\n".encode('utf-8'))
                tn.write(f"{en_port_prefix}{en_port_value} >> {mqtt_ini}\n".encode('utf-8'))
            else:
                tn.write(f"{port_section} >> {mqtt_ini}\n".encode('utf-8'))
                tn.write(f"{cn_port_prefix}{cn_port_value} >> {mqtt_ini}\n".encode('utf-8'))
                tn.write(f"{en_port_prefix}{en_port_value} >> {mqtt_ini}\n".encode('utf-8'))
        
        # 校验是否切换成功
        def check_switch_success(tn: telnetlib.Telnet):
            ck_cmd = [f'killall -9 mymqtt\n', f'cat {mqtt_log} | grep {selected_server} && echo $?-success\n']
            try:
                # 先清空日志
                tn.write(f'echo "" > {mqtt_log}\n'.encode('utf-8'))
                tn.write(ck_cmd[0].encode('utf-8'))
                for _ in range(10):
                    tn.write(ck_cmd[1].encode('utf-8'))
                    result = tn.read_very_eager()
                    if '0-success' in result.decode('utf-8', errors='ignore'):
                        return True
                    time.sleep(1)
            except Exception as e:
                print(f"check_switch_success 异常: {e}")
                import traceback
                traceback.print_exc()
                return False
        try:
            if check_switch_success(tn):
                print(f"{screen}-{host}\t版本切换成功")
                return True
            else:
                times1 += 1
                continue
        except Exception as e:
            logging.error(f"{host-screen}发生错误：{e}")
        
        
        
    

def set_config(tn):
    mqtt_ini = None
    mqtt_log = None
    local_ini = "/software/local.ini"
    try:
        is_new_fw = is_new_firmware(tn)
        logging.info(f"{screen}\t是否为新的固件：{is_new_fw}")
        if is_new_fw:
            mqtt_ini = "/software/mqtt.ini"
            mqtt_log = "/customer/logs/mqtt/mqtt.log"
        else:
            mqtt_ini = "/software/mqtt.ini"
            mqtt_log = "/software/mqtt/mymqtt.log"
        return is_new_fw, mqtt_ini, mqtt_log, local_ini
    except Exception as e:
        print(f"---->{e}")


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
        option = input('\n请选择要操作的屏幕，直接输入序号，可以以英文"，"、";"和空格分割，0则为全部：\n')
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
        is_inner_tool = True  # TODO 如果给外部使用需要变为False
        if is_inner_tool:
            option3 = "3. 测试环境-国内\n"
            option4 = "4. 测试环境-国外\n"
        else:
            option3 = "3. 大陆版本-英文\n"
            option4 = "4. 海外版本-中文\n"
        server = input(
            f"\n请选择要切换的服务地址：\n1. 正式环境-大陆版\n2. 正式环境-海外版\n{option3}{option4}请选择: ")
        if is_inner_tool:
            if server == "3":
                server = "5"
            elif server == "4":
                server = "6"
            if server not in ["1", "2", "5", "6"]:
                print("选项错误，请重新输入")
                continue
            else:
                break
        else:
            if server not in ["1", "2", "3", "4"]:
                print("选项错误，请重新输入")
                continue
            else:
                break
    future = [executor.submit(modify_location, screen, tn, host, server) for screen, tn, host in
                zip(operate_screen, operate_tn, operate_host)]
    concurrent.futures.wait(future)

    input("切换完成!!!按回车键退出程序")
