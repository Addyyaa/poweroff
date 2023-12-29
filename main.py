import socket
import telnetlib
import threading
import logging
import time


def telnet_connect(host, port, user_name, password):
    try:
        tn = telnetlib.Telnet(host, port, timeout=30)
        tn.read_until(b"(none) login: ")
        tn.write(user_name.encode("ascii") + b"\n")
        tn.read_until(b"Password: ")
        tn.write(password.encode("ascii") + b"\n")
        tn.write(b"pidof demo\n")
        time.sleep(1)
        output = tn.read_very_eager().decode("ascii")
        tn.close()
        return tn, output
    except socket.timeout:
        print(f"Connection timeout: {host}:{port}")
        logging.error(f"Connection timeout: {host}:{port}")
        raise socket.timeout
    except socket.error:
        print(f"Connection error: {host}:{port}")
        logging.error(f"Connection error: {host}:{port}")


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s - %(exc_info)s')

# 设备信息
host1 = "192.168.2.225"
host2 = "192.168.2.182"
port = 23
user_name = "root"
password = "ya!2dkwy7-934^"

for _ in range(100):
    try:
        logging.info(f"Try to connect {host1}:{port} and {host2}:{port}")
        # 创建多个线程
        tn1_thread = threading.Thread(target=telnet_connect, args=(host1, port, user_name, password))
        tn2_thread = threading.Thread(target=telnet_connect, args=(host2, port, user_name, password))
        # 启动线程
        tn1 = tn1_thread.start()
        tn2 = tn2_thread.start()
        # 等待线程结束
        tn1_thread.join()
        tn2_thread.join()
    except socket.timeout:
        print(f"Connection timeout: {host1}:{port} and {host2}:{port}")
        logging.error(f"Connection timeout: {host1}:{port} and {host2}:{port}")
        break