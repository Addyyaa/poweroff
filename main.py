import socket
import telnetlib
import threading
import logging
import time
import re
import subprocess


class TelnetThread(threading.Thread):
    def __init__(self, host, port, user_name, password, result, detect_time, pid_name):
        super().__init__()
        self.host = host
        self.port = port
        self.user_name = user_name
        self.password = password
        self.result = result
        self.detect_time = detect_time
        self.pid_name = pid_name

    def run(self):
        # 检查设备是否上线
        start_time = time.time()
        count = 0
        while True:
            try:
                ping_result = subprocess.run(["ping", "-n", "1", self.host], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, text=True, timeout=1)
                print(ping_result.stdout, ping_result.stderr)
                # 检测到设备上线，建立连接
                if ping_result.returncode == 0:
                    try:
                        tn = telnetlib.Telnet(self.host, self.port, timeout=3)
                        tn.read_until(b"(none) login: ", timeout=3)
                        tn.write(self.user_name.encode("ascii") + b"\n")
                        tn.read_until(b"Password: ")
                        tn.write(self.password.encode("ascii") + b"\n")
                        time.sleep(1)
                        tn.write(pid_name.encode("ascii") + b"\n")
                        time.sleep(1)
                        output = tn.read_very_eager().decode("ascii")
                        match = re.search(r"(?<!\[)\b\d+\b(?!])", output)
                        if match is not None:
                            output = int(match.group())
                        else:
                            output = False
                        # 直接修改result变量
                        self.result = output
                        tn.close()
                    except socket.timeout:
                        print(f"连接超时！请检查设备是否异常: {self.host}:{self.port}")
                        logging.error(f"连接超时！请检查设备是否异常: {self.host}:{self.port}")
                        raise socket.timeout
                    except socket.error:
                        print(f"Connection error: {self.host}:{self.port}")
                        logging.error(f"Connection error: {self.host}:{self.port}")
                        raise socket.error
                break
            except subprocess.TimeoutExpired:
                count += 1
                print(f"等待设备上线,已检测{count}s")
            wait_time = (time.time() - start_time)
            if wait_time >= self.detect_time:
                print("检测超时，设备长时间未上线")
                logging.warning(f"已检测{detect_time}s，设备长时间未上线")
                break


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s - %(exc_info)s')

# 设备信息
host1 = "192.168.0.105"
host2 = "192.168.0.103"
port = 23
user_name = "root"
password = "ya!2dkwy7-934^"
detect_time = 500
pid_name = "pidof demo"

# result1和result2直接设为变量
result1 = None
result2 = None
for _ in range(2):
    try:
        # 创建线程对象
        tn1_thread = TelnetThread(host1, port, user_name, password, result1, detect_time, pid_name)
        # tn2_thread = TelnetThread(host2, port, user_name, password, result2, detect_time, pid_name)

        # 启动线程
        tn1_thread.start()
        # tn2_thread.start()

        # 等待线程结束
        tn1_thread.join()
        # tn2_thread.join()

        # 获取线程的result属性
        result1 = tn1_thread.result
        # result2 = tn2_thread.result

        if not result1:
            print(f"设备-{host1}：{pid_name}：{result1},进程不存在，请检查是否画面异常！！！！")
            logging.warning(f"设备-{host1}：{pid_name}：{result1},进程不存在，请检查是否画面异常！！！！")
            break
        else:
            print(f"{host1}:{port} :{pid_name}的pid为{result1}")
            logging.info(f"{host1}:{port} :demo的pid为{result1}")

        # if not result2:
        #     print(f"设备-{host2}：{pid_name}：{result2},进程不存在，请检查是否画面异常！！！！")
        #     logging.warning(f"设备-{host2}：{pid_name}：{result2},进程不存在，请检查是否画面异常！！！！")
        #     break
        # else:
        #     print(f"{host2}:{port} :{pid_name}的pid为{result2}")
        #     logging.info(f"{host1}:{port} :demo的pid为{result2}")
    except socket.timeout:
        break
    except socket.error as e:
        print(f"未知异常：{e}")
        logging.error(f"{e}")
