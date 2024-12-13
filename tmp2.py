import os
import platform
import subprocess


def generate_ota_package():
    current_directory = os.getcwd()
    ota_package_path = os.path.join(current_directory, 'ota_package')
    country = ['CN', "US"]
    screen_type = ['10.1', '13.3', '16', '800-1280', '800-1280-BOE']
    while True:
        if not os.path.exists(ota_package_path):
            print("未检测到OTA目录，开始生成OTA目录")
            for i in country:
                for j in screen_type:
                    os.makedirs(os.path.join(ota_package_path, i, j))
            print("OTA目录创建成功")
            return ota_package_path
        else:
            for i in country:
                for j in screen_type:
                    if not os.path.exists(os.path.join(ota_package_path, i, j)):
                        os.makedirs(os.path.join(ota_package_path, i, j))
            return ota_package_path


def detect_ota_package(ota_path: str):
    no_ota = []
    fine_name = 'SStarOta.bin.gz'
    for i in os.listdir(ota_path):
        print(i)
        for j in os.listdir(os.path.join(ota_path, i)):
            no_ota_path = os.path.join(ota_path, i, j)
            file_list = os.listdir(os.path.join(ota_path, i, j))
            print(file_list)
            # for f in file_list:
            #     file = os.listdir(f)
            #     print(file)

            if fine_name in file_list:
                # print(f"检测到 {j} 升级包：{fine_name}文件")
                pass
            else:
                print(f"未检测到 {j} 目录下有：{fine_name}文件")
                no_ota.append(no_ota_path)
    return no_ota


def open_dir(file_path):
    if platform.system() == "Windows":
        os.startfile(file_path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", file_path])
    else:
        try:
            subprocess.Popen(["xdg-open", file_path])
        except OSError:
            print("无法打开文件管理器，请手动打开目录：", file_path)


path = generate_ota_package()
no_ota_dir_list = detect_ota_package(path)

for i in no_ota_dir_list:
    open_dir(i)
