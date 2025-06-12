from login import Login
import requests
import logging
def bind_device(screen_id: str):
    token = Login("15250996938", "sf123123").login()
    logging.info(f"获取到token：{token}")
    domain = "139.224.192.36"
    port = "8082"
    headers = {
        "Content-Type": "application/json",
        "X-TOKEN": token,
        "user-agent": "Mozilla/5.0 (Linux; Android 15; SM-S9380 Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/136.0.7103.125 Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/30.133333)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    screen_group_id = None
    def add_screen_group():
        # 绑定屏幕组
        api = f"http://{domain}:{port}/api/v1/host/screen/group/add"
        bind_data = {
            "screenGroupName": "i",
            "screenIdList": [screen_id],
            "type": 2
        }
        response = requests.post(api, json=bind_data, headers=headers)
        if response.status_code == 200 and response.json()["code"] == 20:
            screen_group_id = response.json()["data"]
            return screen_group_id
        else:
            logging.error(f"绑定屏幕组失败：{response.json()}")
            logging.error(f"headers：{headers}")
            return False
    
    def delete_screen_group():
        api = f"http://{domain}:{port}/api/v1/host/screen/group/del"
        delete_data = {
            "screenGroupId": screen_group_id,
            "screenIdList": [],
            "isDelGroup": 1
        }
        response = requests.post(api, json=delete_data, headers=headers)
        if response.status_code == 200 and response.json()["code"] == 20:
            return True
        else:
            logging.error(f"删除屏幕组失败：{response.json()}")
            return False
    
    def init_device_info():
        api = f"http://{domain}:{port}/api/v1/screenVideo/extend/{screen_id}"
        response = requests.get(api, headers=headers)
        if response.status_code == 200 and response.json()["code"] == 20:
            data = response.json()["data"]
            if "totalStorage" in data and data["totalStorage"] > 0:
                logging.info(f"{screen_id}设备注册成功")
                return True
            else:
                logging.error(f"非64GB设备，请检查：{data}")
                return False
        else:
            logging.error(f"获取设备信息失败：{response.json()["data"]}")
            return False
    screen_group_id = add_screen_group()
    # if screen_group_id:
    #     if init_device_info():
    #         if not delete_screen_group():
    #             logging.info(f"{screen_id}设备注册成功，但删除屏幕组失败")
    #         return True
    #     else:
    #         delete_screen_group()
    #         return False
    # else:
    #     return False

if __name__ == "__main__":
    bind_device("PS91d7ecLtest111")