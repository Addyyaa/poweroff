import ipaddress
import socket

import netifaces
import psutil

def get_network_info():
    gateways = netifaces.gateways()
    gateway = gateways['default'][2][0]
    addresses = []
    # 获取网络接口状态
    stats = psutil.net_if_stats()
    # 获取所有网络接口地址信息
    for interface, addrs in psutil.net_if_addrs().items():
        # 检查接口是否是活动的
        if interface in stats and stats[interface].isup:
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    addresses.append({f'{interface}': addr.address, 'netmask': addr.netmask})
    ipv4 = addresses
    address = ''
    for i in ipv4:
        if "wlan" in str(i.keys()) .lower() or 'eth' in str(i.keys()) .lower() or '本地连接' in i.keys() or 'lan' in str(
                i.keys()) .lower():
            address = i
            break
        else:
            address = ipv4[0]
            break
    address = dict(address)
    network = ipaddress.IPv4Network(f"{gateway}/{address['netmask']}", strict=False).hosts()
    print(list(network))



get_network_info()
