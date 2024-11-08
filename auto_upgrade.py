import concurrent.futures
import logging
import os
import sys
import telnetlib
import time
from typing import Union
import re
from ftplib import FTP
import subprocess
import ipaddress
import socket

def lan_ip_detect():
    try:
        # 先获取本机地址
        host_name = socket.gethostname()
        host = socket.gethostbyname(host_name)
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
                gateway_ip = input("请输入正确的网关地址：")
                ipaddress.IPv4Network(gateway_ip)
                break
            except ipaddress.AddressValueError:
                print("请输入正确的网关地址")
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


def ip_to_int(ip):
    # 将IP地址字符串转换为整数形式
    parts = [int(part) for part in ip.split('.')]
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]


def int_to_ip(ip_int):
    # 将整数形式的IP地址转换为字符串形式
    return '.'.join(str((ip_int >> (8 * i)) & 255) for i in range(3, -1, -1))



def upgrade(i: int, tn_list: list[telnetlib.Telnet], screens: list, host: list, version: str, update_firmware: str):
    """:return 201 表示获取屏幕配置超时
        :lcd_type 3表示没有sd卡的10.1 4表示没有有sd卡的13.3，5表示有sd卡的10.1 6表示有sd卡的13.3
    """
    # 对选择的屏幕进行操作
    tn_list[i].write(b"cat /customer/config.ini | grep lcd_type && echo ok\n")
    ok = tn_list[i].read_until(b"0", timeout=2).decode("utf-8")
    remote_file_path = '/upgrade/SStarOta.bin.gz'
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    resource_path = os.path.join(base_path, 'resource')
    start_time = time.time()
    while True:
        if "0" in ok:
            break
        else:
            tn_list[i].write(b"cat /customer/config.ini | grep lcd_type && echo $?\n")
            ok = tn_list[i].read_until(b"0", timeout=2).decode("utf-8")
        end_time = time.time()
        if end_time - start_time > 10:
            print(f'{end_time-start_time}s超时，无法获取屏幕配置')
            return i, 201
    result = ok.strip().replace(" ", "")
    index = result.rfind('=')
    if index != -1:
        display_type = result[index + 1:index + 2:1]
        logging.info(f"version:{version}")
        if version == "1":
            # if display_type == "5":.
            #     file_path = os.path.join(resource_path, 'ota_packet/64GB/China/10.1/SStarOta.bin.gz')
            # elif display_type == "6":
            #     file_path = os.path.join(resource_path, 'ota_packet/64GB/China/13.3/SStarOta.bin.g')
            # elif display_type == "1":
            #     file_path = os.path.join(resource_path, 'ota_packet/China/10.1/SStarOta.bin.gz')
            # elif display_type == "2":
            #     file_path = os.path.join(resource_path, 'ota_packet/China/13.3/SStarOta.bin.gz')
            # elif display_type == "3":
            #     file_path = os.path.join(resource_path, 'ota_packet/VideoVersion/China/10.1/SStarOta.bin.gz')
            # elif display_type == "4":
            #     file_path = os.path.join(resource_path, 'ota_packet/VideoVersion/China/13.3/SStarOta.bin.gz')
            if display_type == "1" or display_type == "3" or display_type == "5":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/China/10.1/SStarOta.bin.gz')
            elif display_type == "2" or display_type == "4" or display_type == "6":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/China/13.3/SStarOta.bin.gz')
            elif display_type == "7":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/China/800-1280/SStarOta.bin.gz')  # 7 群创屏 ，
                # 8为BOE屏
            elif display_type == "8":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/China/800-1280-BOE/SStarOta.bin.gz')
            elif display_type == "9":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/China/16/SStarOta.bin.gz')
            else:
                print(f"屏幕{screens[i]}未知类型, 未升级")
                return False
        elif version == "2":
            # if display_type == "5":
            #     file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/10.1/SStarOta.bin.gz')
            # elif display_type == "6":
            #     file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/13.3/SStarOta.bin.gz')
            # elif display_type == "1":
            #     file_path = os.path.join(resource_path, 'ota_packet/USA/10.1/SStarOta.bin.gz')
            # elif display_type == "2":
            #     file_path = os.path.join(resource_path, 'ota_packet/USA/13.3/SStarOta.bin.gz')
            # elif display_type == "3":
            #     file_path = os.path.join(resource_path, 'ota_packet/VideoVersion/USA/10.1/SStarOta.bin.gz')
            # elif display_type == "4":

            #     file_path = os.path.join(resource_path, 'ota_packet/VideoVersion/USA/13.3/SStarOta.bin.gz')
            if display_type == "1" or display_type == "3" or display_type == "5":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/10.1/SStarOta.bin.gz')
            elif display_type == "2" or display_type == "4" or display_type == "6":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/13.3/SStarOta.bin.gz')
            elif display_type == "7":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/800-1280/SStarOta.bin.gz')
            elif display_type == "8":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/800-1280-BOE/SStarOta.bin.gz')
            elif display_type == "9":
                file_path = os.path.join(resource_path, 'ota_packet/64GB/USA/16/SStarOta.bin.gz')
            else:
                print(f"屏幕{screens[i]}未知类型, 未升级")
                return False
        else:
            print(f"屏幕{screens[i]}未知版本, 未升级")
            return False
    else:
        print(f"屏幕{screens[i]}未获取到配置信息")
        return False

    # 删除原有的固件
    tn_list[i].write(b"rm  /upgrade/SStarOta.bin.gz\n")
    tn_list[i].read_very_eager()
    tn_list[i].write(b"rm  /upgrade/SStarOta.bin.gz\n")
    content = get_latest_print(tn_list[i])
    if not content:
        print(f"{screens[i]}原有固件删除失败")
        return False
    else:
        content = content.decode("utf-8")

    if "can't remove" in content:
        try:
            tn_list[i].write(b"kill -9 $(pidof tcpsvd)\n")
            tn_list[i].read_until(b'Killed', timeout=2)
            print(f'{screens[i]}：SStarOta.bin.gz 已成功删除！')
            tn_list[i].write(b"tcpsvd -vE 0.0.0.0 21 ftpd -w / &\n")
            content = get_latest_print(tn_list[i])
            if content:
                content=content.decode("utf-8")
            else:
                print(f"{screens[i]}：ftp服务开启失败，升级失败")
                return False
        except Exception as e:
            logging.error(f"删除SStarOta.bin.gz时发生错误: {e}")
    else:
        print(f"未成功删除SStarOta.bin.gz，{screens[i]}升级失败")
        return False
    # 上传固件
    if "tcpsvd: listening on 0.0.0.0:21" in content or "tcpsvd: bind: Address already in use" in content:
        with FTP(host=host[i]) as ftp:
            response = ftp.login(user="", passwd="")
            welcome_message = ftp.getwelcome()
            if "230" in response and "220" in welcome_message:
                n = 0
                while n < 4:
                    try:
                        n += 1
                        with open(file_path, 'rb') as file:
                            response1 = ftp.storbinary(f"STOR {remote_file_path}", file)
                        if response1.startswith('226'):
                            print(f"{screens[i]}升级包上传成功！")
                            break
                        else:
                            print(f"上传文件时发生错误: {response1}")
                            if n == 3:
                                print("累计三次上传失败，程序即将退出")
                                time.sleep(10)
                                sys.exit()
                    except Exception as ep:
                        print(f"上传文件时发生错误: {ep}")
                        time.sleep(10)
            else:
                print("FTP登录失败！")
    else:
        print(f"{screens[i]}未成功启动ftp服务，无法上传固件,{screens[i]}升级失败")
    # 关闭ftp
    tn_list[i].write(b"kill -9 $(pidof tcpsvd)\n")
    tn_list[i].write(b" pidof tcpsvd\n")
    try:
        content = get_latest_print(tn_list[i])
    except Exception as e:
        logging.error(e)
    if not content:
        print(f"{screens[i]}未成功关闭ftp服务")
        return False
    else:
        content = content.decode("utf-8")
    if "Killed" in content or "" in content:
        pass
    else:
        print(f"{screens[i]}未成功关闭ftp服务")

    tn_list[i].write(b"\n")
    # 检查文件是否成功传入
    tn_list[i].write(b"find /upgrade/ -maxdepth 1 -name SStarOta.bin.gz \n")
    try:
        content = get_latest_print(tn_list[i])
    except Exception as e:
        logging.error(e)
    if not content:
        print(f"{screens[i]}上传固件验证失败")
        return False
    else:
        content = content.decode("utf-8")


    if "SStarOta.bin.gz" in content:
        if update_firmware == '1':
            tn_list[i].write(b"rm /upgrade/restore/SStarOta.bin.gz\n")
            tn_list[i].read_very_eager()
            tn_list[i].write(b"rm /upgrade/restore/SStarOta.bin.gz\n")
            try:
                content = get_latest_print(tn_list[i])
            except Exception as e:
                logging.error(e)
            if not content:
                print(f"{screens[i]}未能删除原工厂内置固件")
                return False
            else:
                content = content.decode("utf-8")
            if "can't remove" in content:
                print(f"{screens[i]}已删除原工厂内置固件，开始更新固件...")
                while True:
                    tn_list[i].write(b"cp /upgrade/SStarOta.bin.gz /upgrade/restore/ && date\n ")
                    tn_list[i].read_until(b"UTC", timeout=10)
                    tn_list[i].write(b"cd /upgrade/restore/ && ls\n")
                    try:
                        content = get_latest_print(tn_list[i])
                    except Exception as e:
                        logging.error(e)
                    if content is not False:
                        content = content.decode('utf-8')
                        if "SStarOta.bin.gz" in content:
                            print(f"{screens[i]}固件更新成功！")
                            break
                        else:
                            print(f"{screens[i]}固件更新失败，请重试")
                            return False
                    else:
                        print(f"{screens[i]}未能获取固件信息，请重试")
                        logging.error(f"{screens[i]}：{content}")
                        return False
            else:
                print(f"{screens[i]}出厂固件删除失败，请重试")
                return False
        # 开始升级
        print(f"{screens[i]}开始升级")
        tn_list[i].write(b"/upgrade/upgrade.sh &\n")
        content = tn_list[i].read_until(b'ash: you need to specify whom to kill', timeout=20).decode("utf-8")
        if "ash: you need to specify whom to kill" in content:
            time.sleep(45)
            return screens[i]
        else:
            print(f"{screens[i]}升级失败，请重试")
            return False
    else:
        print(f"{screens[i]}固件上传失败，请重试")
        return False



def scan_ip_range(start_ip, end_ip, port, addresses):
    # 将起始IP地址和结束IP地址转换为整数形式
    start = ip_to_int(start_ip)
    end = ip_to_int(end_ip)
    screens = []
    tn_list = []
    available_selection = []
    upgrade_list = []
    host_list = []
    upgrade_screens = []
    # 使用线程池
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
                list_a, tn, host = f.result()
                screens.append(list_a)
                tn_list.append(tn)
                host_list.append(host)
    if not screens:
        input("\n未发现设备，按回车键退出程序")
        sys.exit()

    for index, screen in enumerate(screens):
        available_selection.append(str(index + 1))
        print(f"\n{index + 1}：{screen}\t{host_list[index]}")
    while True:
        selection = input(f"请选择你要升级的屏幕，输入0则全部进行升级,多选屏幕请使用空格、分号或逗号进行分隔：")
        if selection == "0":
            for i in range(len(tn_list)):
                upgrade_list.append(i)
                upgrade_screens.append(screens[i])
            break
        elif selection in available_selection:
            upgrade_list.append(int(selection) - 1)
            upgrade_screens.append(screens[int(selection) - 1])
            break
        else:
            selection = re.split(r'[ ,;]', selection)
            # 根据用户输入的屏幕id找到对应的tn
            try:
                for screen in selection:
                    upgrade_list.append(screens.index(screen))
                    upgrade_screens.append(screen)
                break
            except ValueError:
                print("无效的屏幕id，请重新输入")

    while True:
        version = input("请选择你要升级的版本：\n 1. 国内-Chinese\n 2. 国外-English\n请选择: ")
        if version in ["1", "2"]:
            break
        else:
            print("输入有误，请重新输入")

    while True:
        update_firmware = input("是否更新出厂内置固件：y/n: ")
        if update_firmware.upper() == "Y":
            update_firmware = "1"
            break
        elif update_firmware.upper() == "N":
            update_firmware = "0"
            break
        else:
            print("输入有误，请重新输入")

    # 对upgrade_list进行去重
    upgrade_list = list(set(upgrade_list))

    # 使用线程池升级操作
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(
            upgrade, i, tn_list, screens, host_list, version, update_firmware) for i in upgrade_list]
        # 获取升级的状态码0
        completed = 0
        for f in concurrent.futures.as_completed(futures):
            # 进度条动画
            completed += 1
            dengyu = "=" * (int(completed / len(futures) * 100))
            kong = " " * (100 - int(completed / len(futures) * 100))
            total_jindu = f"\r正在升级设备：【{dengyu}{kong}】"
            print(total_jindu, end="", flush=True)
            if isinstance(f.result(), tuple):
                indx, code = f.result()
                if code == 201:
                    print(f"{screens[indx]}未能获取配置，升级失败")
        success_list = []
        fail_list = []
        fail_list_screen = []
        for f in futures:
            screen = f.result()
            if screen:
                print(f"\n\033[92m{screen}\033[0m升级完成", end="")
                success_list.append(screen)
        for index, screen in enumerate(upgrade_screens):
            if screen not in success_list:
                print(f"\033[91m{screen}\033[0m升级失败")
                index = screens.index(screen)
                fail_list.append(index)
                fail_list_screen.append(screen)
        if fail_list:
            count = 1
            while True:
                count += 1
                futures = [executor.submit(upgrade, i, tn_list, screens, host_list, version, update_firmware) for i in fail_list]
                # 获取升级的状态码
                completed = 0
                for f in concurrent.futures.as_completed(futures):
                    # 进度条动画
                    completed += 1
                    dengyu = "=" * (int(completed / len(futures) * 100))
                    kong = " " * (100 - int(completed / len(futures) * 100))
                    total_jindu = f"\r正在升级设备：【{dengyu}{kong}】"
                    print(total_jindu, end="", flush=True)
                    if isinstance(f.result(), tuple):
                        indx, code = f.result()
                        if code == 201:
                            print(f"{screens[indx]}未能获取配置，升级失败")
                for f in futures:
                    screen = f.result()
                    if screen:
                        print(f"\n\033[92m{screen}\033[0m升级完成", end="")
                        success_list.append(screen)
                        fail_list_screen.remove(screen)
                for index, screen in enumerate(fail_list_screen):
                    if screen not in success_list:
                        print(f"\033[91m{screen}\033[0m第{count}次升级失败")
                if not fail_list_screen:
                    break
                else:
                    print(f"还有{len(fail_list_screen)}台设备未升级成功：{fail_list_screen}")
                if count >= 50:
                    ct = input("是否继续升级（y/n）")
                    if ct.upper() == "N":
                        break

        concurrent.futures.wait(futures)
        all_status = all(f.done() for f in futures)
        if all_status:
            input("\n升级完成，请按回车键退出程序")
        else:
            input("存在设备升级失败，请检查")


def main():
    # 设置要扫描的IP地址范围和端口号
    start_ip, end_ip, addresses = lan_ip_detect()
    port = 23  # Telnet端口号
    # 扫描指定范围内的IP地址的指定端口
    scan_ip_range(start_ip, end_ip, port, addresses)


if __name__ == "__main__":
    main()
