import concurrent.futures
import telnetlib
import time
from typing import Union
import re


def tel_print(str: bytes):
    content = str.rfind(b"\r\n")
    if content == -1:
        return None
    else:
        return content


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
            return screen, tn
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


def scan_ip_range(start_ip, end_ip, port):
    # 将起始IP地址和结束IP地址转换为整数形式
    start = ip_to_int(start_ip)
    end = ip_to_int(end_ip)
    screens = []
    tn_list = []
    available_selection = []
    upgrade_list = []
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
                list_a, tn = f.result()
                screens.extend(list_a)
                tn_list.append(tn)
    for index, screen in enumerate(screens):
        available_selection.append(str(index+1))
        print(f"\n{index+1}：{screen}")
    while True:
        selection = input(f"请选择你要升级的屏幕，输入0则全部进行升级\n：")
        if selection == "0":
            #TODO 需要完成所有设备升级操作
            for i in range(len(tn_list)):
                upgrade_list.append(i)
            print(upgrade_list)
            break
        elif selection in available_selection:
            #TODO 需要完成指定设备升级操作
            upgrade_list.append(int(selection) - 1)
            print(upgrade_list)
            break
        else:
            selection = re.split(r'[ ,;]', selection)
            #TODO 需要完成指定设备升级操作
            # 根据用户输入的屏幕id找到对应的tn
            try:
                for screen in selection:
                    upgrade_list.append(screens.index(screen))
                print(upgrade_list)
                break
            except ValueError:
                print("无效的屏幕id，请重新输入")

    # 对选择的屏幕进行操作
    for i in upgrade_list:
        tn_list[i].write(b"cat /customer/config.ini | grep display_type\n")
        while True:
            time.sleep(0.3)
            s = tn.read_very_eager()
            index = s.rfind(b"PS")
            if index != -1:
                break
        result = s[index::].decode("utf-8")
        print(result)


def main():
    # 设置要扫描的IP地址范围和端口号
    start_ip = '192.168.1.2'
    end_ip = '192.168.1.254'
    port = 23  # Telnet端口号
    # 扫描指定范围内的IP地址的指定端口
    scan_ip_range(start_ip, end_ip, port)


if __name__ == "__main__":
    main()
