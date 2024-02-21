import sys
import os
remote_file_path = '/software/mqtt/mymqtt'
base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
resource_path = os.path.join(base_path, 'resource')
Chinese_file_path = os.path.join(resource_path, 'China/mymqtt')
American_file_path = os.path.join(resource_path, 'USA/mymqtt')
print(f"上传文件路径：{Chinese_file_path}")
print(f"上传文件路径：{American_file_path}")