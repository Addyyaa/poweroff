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
    remote_file_path = '/software/mqtt/mymqtt'
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    resource_path = os.path.join(base_path, 'resource')
    file_path = os.path.join(resource_path, 'mymqtt')
    with FTP(host) as ftp:
        response = ftp.login(user=user_name, passwd=password)
        welcome_message = ftp.getwelcome()
        if "230" in response and "220" in welcome_message:
            logging.info("FTP登录成功！")
            try:
                with open(file_path, 'rb') as file:
                    ftp.storbinary(f"STOR {remote_file_path}", file)
            except Exception as e:
                print(f"上传文件时发生错误: {e}")
                time.sleep(10)
                sys.exit()
        else:
            logging.error("FTP登录失败！")


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
        tn.write(b"rm  /software/mqtt/mymqtt\n")
        tn.write(b"ls software/mqtt/mymqtt \n")
        output = tn.read_until(b"/software/mqtt/mymqtt", timeout=2)
        directories_and_files = re.findall(b'\x1b\[\d+;\d+m(\S+?)\x1b\[0m', output)
        # 格式化输出
        content = format_output(directories_and_files, output)
        if content == "":
            logging.info(f'mymqtt已成功删除！')
            tn.write(b"tcpsvd -vE 0.0.0.0 21 ftpd -w / &\n")
            # 传入新的mymqtt文件
            ftp_upload(host)
            # 检查文件是否成功传入
            tn.write(b"ls software/mqtt/mymqtt \n")
            output = tn.read_until(b"/software/mqtt/mymqtt", timeout=2)
            directories_and_files = re.findall(b'\x1b\[\d+;\d+m(\S+?)\x1b\[0m', output)
            # 格式化输出
            file = format_output(directories_and_files, output)
            if file:
                logging.info(f'mymqtt已成功传入！')
                # 授权
                tn.write(b"chmod +x /software/mqtt/mymqtt\n")
                # 检查文件是否拥有可执行权限
                tn.read_until(b"chmod +x /software/mqtt/mymqtt")
                tn.write(b"ls -l /software/mqtt/mymqtt\n")
                output = tn.read_until(b"ls -l /software/mqtt/mymqtt*", timeout=2)
                output_str = output.decode("utf-8")
                properties = match(r'/software/mqtt/mymqtt\r\n(.{4})', output_str)
                if properties:
                    is_x = properties.group(1)
                    is_x = list(is_x)
                    is_x = is_x[3]
                    print(is_x)
                    if is_x == "x":
                        logging.info(f'mymqtt拥有可执行权限！')
                    else:
                        logging.error(f'mymqtt没有拥有可执行权限！property：{properties.group(1)}')
                else:
                    logging.error("未匹配到权限信息，程序即将退出")
                    sys.exit()
                # 修改地区信息
                tn.write(b'echo "[local]" > /software/local.ini\n')
                tn.write(b'echo "local=1" >> /software/local.ini\n')
                # 验证修改结果
                tn.write(b'cat /software/local.ini\n')
                output = tn.read_until(b"cat local.ini", timeout=2)
                output_str = output.decode("utf-8")
                location = match(r'local=(\d+)', output_str)
                if location:
                    if location.group(1) == "1":
                        logging.info(f'地区信息修改成功！')
                    else:
                        logging.error(f'地区信息修改失败！location：{location.group(1)},程序即将退出！')
                        sys.exit()
                else:
                    logging.error("未匹配到地区信息，程序即将退出")
                    sys.exit()
                # 重启mqtt服务
                tn.write(b"kill -9 $(pidof mymqtt) && tail -f /software/mqtt/mymqtt.log | { if grep -q "
                         b"139.224.192.36; then kill -9 $(pidof tail) ; fi; }\n")
                output = tn.read_until(b"Killed", timeout=2)
                if "Killed" in output.decode("utf-8"):
                    logging.info(f'mymqtt重启成功,检测到测试服务器,程序即将退出！')
                    time.sleep(2)
                else:
                    logging.error(f'mymqtt重启失败！')
                    sys.exit()
        else:
            logging.error(f'mymqtt删除失败！')
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
        logging.error(f"连接超时，请检查设备是否异常: {host}")
