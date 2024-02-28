import socket
import sys
import telnetlib
from ftplib import FTP
import logging
import time
import re
import os

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)


def format_output(directories_and_files, color_string):
    formatted_output = ""
    for item, color_code in zip(directories_and_files, color_string.decode("utf-8").split()):
        match = re.search(r'\x1b\[1;(\d+)m', color_code)
        color_code = match.group(1) if match else ''  # 如果匹配成功则使用颜色代码，否则使用空字符串
        formatted_output += f'\x1b[1;{color_code}m{item.decode("utf-8")}\x1b[0m  '  # 添加蓝色
    return formatted_output


def ip_check(ip):
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
        return True
    else:
        return False


def match(express, string):
    match = re.search(express, string)
    if match:
        return match
    else:
        return False


def ftp_upload(host, port=21, user_name="", password=''):
    remote_file_path = '/upgrade/SStarOta.bin.gz'
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    resource_path = os.path.join(base_path, 'resource')
    ch_101 = os.path.join(resource_path, 'ota_packet/China/10.1/SStarOta.bin.gz')
    ch_133 = os.path.join(resource_path, 'ota_packet/China/13.3/SStarOta.bin.gz')
    us_101 = os.path.join(resource_path, 'ota_packet/USA/10.1/SStarOta.bin.gz')
    us_133 = os.path.join(resource_path, 'ota_packet/USA/13.3/SStarOta.bin.gz')
    file_path = ""
    while True:
        choice = input("请指定产品类型：\n1.中国10.1\n2.中国13.3\n3.美国10.1\n4.美国-13.3\n请选择: ")
        if choice == '1':
            file_path = ch_101
            break
        elif choice == '2':
            file_path = ch_133
            break
        elif choice == '3':
            file_path = us_101
            break
        elif choice == '4':
            file_path = us_133
            break
        else:
            print("输入有误，请重新输入")
            continue
    with FTP(host) as ftp:
        response = ftp.login(user=user_name, passwd=password)
        welcome_message = ftp.getwelcome()
        if "230" in response and "220" in welcome_message:
            logging.info("FTP登录成功！")
            n = 0
            while n < 4:
                try:
                    n += 1
                    with open(file_path, 'rb') as file:
                        response1 = ftp.storbinary(f"STOR {remote_file_path}", file)
                    if response1.startswith('226'):
                        logging.info("上传文件成功！")
                        break
                    else:
                        logging.error(f"上传文件时发生错误: {response1}")
                        if n == 3:
                            logging.error("累计三次上传失败，程序即将退出")
                            time.sleep(10)
                            sys.exit()
                except Exception as ep:
                    print(f"上传文件时发生错误: {ep}")
                    time.sleep(10)
                    sys.exit()
        else:
            logging.error("FTP登录失败！")
    return choice


def telnet_connect(host, port=23, user_name="root", password='ya!2dkwy7-934^'):
    tn = telnetlib.Telnet(host, port, timeout=3)
    tn.read_until(b"(none) login: ")
    tn.write(user_name.encode("ascii") + b"\n")
    tn.read_until(b"Password: ")
    tn.write(password.encode("ascii") + b"\n")
    time.sleep(0.5)
    login_result = tn.read_until(b"login: can't chdir to home directory '/home/root'")
    if login_result:
        logging.info(f'已成功登录到设备：{host}')
        tn.write(b"rm  /upgrade/SStarOta.bin.gz\n")
        tn.write(b"find /upgrade/ -maxdepth 1 -name SStarOta.bin.gz\n")
        output = tn.read_until(b"/upgrade/SStarOta.bin.gz", timeout=2)
        directories_and_files = re.findall(b'\x1b\[\d+;\d+m(\S+?)\x1b\[0m', output)
        # 格式化输出
        content = format_output(directories_and_files, output)
        if content == "":
            tn.write(b"kill -9 $(pidof tcpsvd)\n")
            tn.read_until(b'Killed', timeout=2)
            logging.info(f'SStarOta.bin.gz 已成功删除！')
            tn.write(b"tcpsvd -vE 0.0.0.0 21 ftpd -w / &\n")
            tn.read_until(b'tcpsvd: listening on 0.0.0.0:21, starting', timeout=2)
            # 传入新的升级包文件
            ftp_upload(host)
            # 关闭ftp
            tn.write(b"kill -9 $(pidof tcpsvd)\n")
            tn.read_until(b'Killed', timeout=2)
            # 传入新的升级包文件
            # 检查文件是否成功传入
            tn.write(b"find /upgrade/ -maxdepth 1 -name SStarOta.bin.gz \n")
            output = tn.read_until(b"/upgrade/SStarOta.bin.gz", timeout=2)
            last_index = output.rfind(b'\r\n')  # 获取最后一个 \r\n 的索引位置
            if last_index != -1:  # 如果找到了 \r\n
                content = output[last_index + 2:]  # 获取最后一个 \r\n 后面的内容
                pattern = rb'/(\S+)'
                match = re.search(pattern, content)
                if match:
                    content = match.group(1).decode('utf-8')
                else:
                    logging.error("未找到匹配的内容")
                if content == "upgrade/SStarOta.bin.gz":
                    logging.info(f'检测到升级文件，即将开始升级！')
                    tn.write(b"/upgrade/upgrade.sh &\n")
                    c = tn.read_until(b'ash: you need to specify whom to kill', timeout=2)
                    if c:
                        start_time = time.time()
                        while True:
                            if time.time() - start_time <= 60:
                                chars = "一\|/"
                                for char in chars:
                                    sys.stdout.write('\r' + char)
                                    sys.stdout.flush()
                                    time.sleep(0.5)
                            else:
                                break
                        input("\n升级完成！按回车键退出程序。")
                else:
                    input("未找到升级文件，请重新尝试运行该文件，按Enter结束程序")
            else:
                input("未找到升级文件，请重新尝试运行该文件，按Enter结束程序")
        else:
            logging.error(f'SStarOta.bin.gz 删除失败！')
            sys.exit()
    else:
        logging.error(f'登录设备 {host} 失败')


if __name__ == '__main__':
    while True:
        host = input("请输入设备IP:")
        result = ip_check(host)
        if result:
            break
        else:
            print("请输入正确的IP地址!")
    try:
        telnet_connect(host)
    except socket.timeout:
        logging.error(f"连接超时，请检查设备是否异常,ip是否正确: {host}")
        input("按回车键退出程序")
    except Exception as e:
        logging.error(e)
        time.sleep(4)
        print("程序即将退出")
        sys.exit()
