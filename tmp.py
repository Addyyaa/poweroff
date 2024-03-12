import concurrent.futures
import logging
import os
import sys
import telnetlib
import time
from typing import Union
import re
from ftplib import FTP


def tel_print(str: bytes):
    content = str.rfind(b"\r\n")
    if content == -1:
        return None
    else:
        return content

def get_latest_print(tn: telnetlib.Telnet):
    time.sleep(0.5)
    content = tn.read_very_eager()
    index1 = content.rfind(b"\r\n")
    index = content.rfind(b"\r\n", 0, index1)
    if index != -1:
        content = content[index + 2:index1:1]
        return content
    else:
        return None
def scan_port(host, port) -> Union[list, bool, telnetlib.Telnet]:
    screen = []
    try:
        tn = telnetlib.Telnet(host, port, timeout=0.5)
        s = tn.read_until(b"login: ", timeout=0.5)
        index = tel_print(s)
        result = s[index::].decode("utf-8")
        if "login: " in result:
            tn.write(b"root\n")
            tn.read_until(b"Password: ", timeout=2)
            tn.write(b"ya!2dkwy7-934^\n")
            tn.read_until(b"login: can't chdir to home directory '/home/root'")
            tn.write(b"cat customer/screenId.ini\n")
            # 循环防止未来得及读取到屏幕id的情况
            while True:
                time.sleep(0.3)
                s = tn.read_very_eager()
                index = s.rfind(b"PS")
                if index != -1:
                    break
            result = s[index::].decode("utf-8")
            screen = [result.splitlines()[0]]
            return screen, tn, host
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


def upgrade(i: int, tn_list: list[telnetlib.Telnet], screens: list, host: list):
    # 对选择的屏幕进行操作
    tn_list[i].write(b"cat /customer/config.ini | grep lcd_type\n")
    start_time = time.time()
    display_type = None
    remote_file_path = '/upgrade/SStarOta.bin.gz'
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    resource_path = os.path.join(base_path, 'resource')
    while True:
        time.sleep(0.3)
        s = tn_list[i].read_very_eager()
        index = s.rfind(b"lcd_type=")
        if index != -1:
            break
        end_time = time.time()
        if end_time - start_time > 10:
            print(f"屏幕{screens[i]}获取配置超时")
            break
    result = s[index::].decode("utf-8")
    # todo 完成功能后删除打印
    index = result.rfind('=')
    if index != -1:
        display_type = result[index + 1:index + 2:1]
        if display_type == "3":
            print(f"屏幕{screens[i]}为10.1！")
        elif display_type == "4":
            print(f"屏幕{screens[i]}为13.3！")
        else:
            print(f"屏幕{screens[i]}未知类型")
    else:
        print(f"屏幕{screens[i]}未获取到配置信息")
    while True:
        version = input("请选择你要升级的版本：\n 1. 国内-Chinese\n 2. 国外-English\n请选择: ")
        if version == "1":
            if display_type == "3":
                file_path = os.path.join(resource_path, 'ota_packet/China/10.1/SStarOta.bin.gz')
            elif display_type == "4":
                file_path = os.path.join(resource_path, 'ota_packet/China/13.3/SStarOta.bin.gz')
            else:
                print(f"屏幕{screens[i]}未知类型, 未升级")
                return False
            break
        elif version == "2":
            if display_type == "3":
                file_path = os.path.join(resource_path, 'ota_packet/USA/10.1/SStarOta.bin.gz')
            elif display_type == "4":
                file_path = os.path.join(resource_path, 'ota_packet/USA/13.3/SStarOta.bin.gz')
            else:
                print(f"屏幕{screens[i]}未知类型, 未升级")
                return False
            break
        else:
            print("请输入正确的选项")
    # 升级内置固件
    while True:
        update_firmware = input("是否更新出厂内置固件：\n1.是\n2.否\n请选择: ")
        if update_firmware == '1':
            update_firmware = True
            break
        elif update_firmware == '2':
            update_firmware = False
            break
        else:
            print("输入有误，请重新输入")
            continue
    # 删除原有的固件
    tn_list[i].write(b"rm  /upgrade/SStarOta.bin.gz\n")
    tn_list[i].read_very_eager()
    tn_list[i].write(b"rm  /upgrade/SStarOta.bin.gz\n")
    content = get_latest_print(tn_list[i]).decode("utf-8")
    if "can't remove" in content:
        try:
            tn_list[i].write(b"kill -9 $(pidof tcpsvd)\n")
            tn_list[i].read_until(b'Killed', timeout=2)
            print(f'SStarOta.bin.gz 已成功删除！')
            tn_list[i].write(b"tcpsvd -vE 0.0.0.0 21 ftpd -w / &\n")
            content = get_latest_print(tn_list[i]).decode("utf-8")
        except Exception as e:
            logging.error(f"删除SStarOta.bin.gz时发生错误: {e}")
    else:
        print("未成功删除SStarOta.bin.gz")
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
                            print("上传文件成功！")
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
                        sys.exit()
            else:
                print("FTP登录失败！")
                input("按回车键退出程序")
                sys.exit()
    else:
        print(f"{screens[i]}未成功启动ftp服务，无法上传固件")
    # 关闭ftp
    tn_list[i].write(b"kill -9 $(pidof tcpsvd)\n")
    tn_list[i].write(b" pidof tcpsvd\n")
    content = get_latest_print(tn_list[i]).decode("utf-8")
    if "Killed" in content or "" in content:
        pass
    else:
        print(f"{screens[i]}未成功关闭ftp服务")
    tn_list[i].write(b"\n")
    # 检查文件是否成功传入
    tn_list[i].write(b"find /upgrade/ -maxdepth 1 -name SStarOta.bin.gz \n")
    content = get_latest_print(tn_list[i]).decode("utf-8")
    if "SStarOta.bin.gz" in content:
        if update_firmware:
            tn_list[i].write(b"rm /upgrade/restore/SStarOta.bin.gz\n")
            tn_list[i].read_very_eager()
            tn_list[i].write(b"rm /upgrade/restore/SStarOta.bin.gz\n")
            content = get_latest_print(tn_list[i]).decode("utf-8")
            if "can't remove" in content:
                print("已删除原工厂内置固件，开始更新固件...")
                tn_list[i].write(b"cp /upgrade/SStarOta.bin.gz /upgrade/restore/ && date\n ")
                tn_list[i].read_until(b"UTC", timeout=10)
                tn_list[i].write(b"ls\n")
                content = get_latest_print(tn_list[i]).decode("utf-8")
                if "SStarOta.bin.gz" in content:
                    print(f"{screens[i]}固件更新成功！")
                else:
                    print(f"{screens[i]}固件更新失败，请重试")
            else:
                print(f"{screens[i]}出厂固件删除失败，请重试")
        # 开始升级
        print(f"{screens[i]}开始升级")
        tn_list[i].write(b"/upgrade/upgrade.sh &\n")
        content = tn_list[i].read_until(b'ash: you need to specify whom to kill', timeout=20).decode("utf-8")
        if "ash: you need to specify whom to kill" in content:
            start_time = time.time()
            while True:
                if time.time() - start_time <= 60:
                    chars = "一\|/"
                    for char in chars:
                        sys.stdout.write('\r' + screens[i] + char)
                        sys.stdout.flush()
                        time.sleep(0.5)
                else:
                    break
            print(f"{screens[i]}升级成功")
            return True
        else:
            print(f"{screens[i]}升级失败，请重试")
    else:
        print(f"{screens[i]}固件上传失败，请重试")


def scan_ip_range(start_ip, end_ip, port):
    # 将起始IP地址和结束IP地址转换为整数形式
    start = ip_to_int(start_ip)
    end = ip_to_int(end_ip)
    screens = []
    tn_list = []
    available_selection = []
    upgrade_list = []
    host_list = []
    # 使用线程池
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = [executor.submit(scan_port, int_to_ip(ip_int), port) for ip_int in range(start, end + 1)]
        completed = 0
        # 等待线程执行完毕
        for f in concurrent.futures.as_completed(future):
            completed += 1
            dengyu = "=" * (int(completed / (end - start + 1) * 100))
            kong = " " * (100 - int(completed / (end - start + 1) * 100))
            total_jindu = f"\r正在检索设备：【{dengyu}{kong}】"
            print(total_jindu, end="", flush=True)
            if f.result():
                list_a, tn, host = f.result()
                # print(host)
                screens.extend(list_a)
                tn_list.append(tn)
                host_list.append(host)
    for index, screen in enumerate(screens):
        available_selection.append(str(index + 1))
        print(f"\n{index + 1}：{screen}")
    while True:
        selection = input(f"请选择你要升级的屏幕，输入0则全部进行升级,多选屏幕请使用空格、分号或逗号进行分隔：")
        if selection == "0":
            for i in range(len(tn_list)):
                upgrade_list.append(i)
            break
        elif selection in available_selection:
            upgrade_list.append(int(selection) - 1)
            break
        else:
            selection = re.split(r'[ ,;]', selection)
            # 根据用户输入的屏幕id找到对应的tn
            try:
                for screen in selection:
                    upgrade_list.append(screens.index(screen))
                break
            except ValueError:
                print("无效的屏幕id，请重新输入")

    # 使用线程池升级操作
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(upgrade, i, tn_list, screens, host_list) for i in upgrade_list]
        concurrent.futures.wait(futures)
        all_status = all(f.done() for f in futures)
        print("all_status：", all_status)
        if all_status:
            input("升级完成，请按回车键退出程序")
        else:
            input("存在设备升级失败，请检查")

def main():
    # 设置要扫描的IP地址范围和端口号
    start_ip = '192.168.0.2'
    end_ip = '192.168.0.254'
    port = 23  # Telnet端口号
    # 扫描指定范围内的IP地址的指定端口
    scan_ip_range(start_ip, end_ip, port)


if __name__ == "__main__":
    main()
