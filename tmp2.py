import re
import subprocess
import ipaddress

def lan_ip_detect():
    # 执行命令并获取输出
    result = subprocess.run(["ipconfig"], capture_output=True, text=True).stdout
    index = result.rfind("WLAN")
    lan_contents = result[index::].splitlines()
    lan_contents.pop(0)
    lan_contents.pop(0)
    lan_content = []
    for i in lan_contents:
        if i != "":
            lan_content.append(i)
            lan_content.append("\n")
        else:
            break
    lan_content = "".join(lan_content)
    ipv4_str = lan_content[lan_content.lower().find("IPv4".lower())::].splitlines()[0]
    mask_index = lan_content.lower().find("Mask".lower())
    if mask_index == -1:
        mask_index = lan_content.lower().find("子网掩码".lower())
    subnet_mask_str = lan_content[mask_index::].splitlines()[0]
    gateway_index = lan_content.lower().find("Gateway".lower())
    if gateway_index == -1:
        gateway_index = lan_content.lower().find("默认网关".lower())
    gateway_str = lan_content[gateway_index::]
    gateway_ip = ip_match(gateway_str)
    subnet_mask = ip_match(subnet_mask_str)
    network = ipaddress.IPv4Network(f"{gateway_ip}/{subnet_mask}", strict=False)
    # 获取可用主机范围
    start_ip = list(network.hosts())[0]
    end_ip = list(network.hosts())[-1]
    start_ip = str(start_ip)
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