import re
import subprocess
import ipaddress

def lan_ip_detect():
    # 执行命令并获取输出
    result = subprocess.run(["ipconfig"], capture_output=True, text=True).stdout
    index = result.rfind("WLAN")
    lan_content = result[index::]
    ipv4_str = lan_content[lan_content.lower().find("IPv4".lower())::].splitlines()[0]
    subnet_mask = lan_content[lan_content.lower().find("Mask".lower())::].splitlines()[0]
    gate_way = lan_content[lan_content.lower().find("Gateway".lower())::].splitlines()[0]
    gateway_ip = ip_match(gate_way)
    subnet_mask = ip_match(subnet_mask)
    network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
    # 获取可用主机范围
    start_ip = list(network.hosts())[0]
    end_ip = list(network.hosts())[-1]
    start_ip =str(start_ip)
    end_ip = str(end_ip)
    return start_ip, end_ip

def ip_match(str):
    pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    match = re.search(pattern, str)
    if match:
        return match.group()
    else:
        return False


lan_ip_detect()