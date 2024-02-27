import re

# 读取文件内容
file_path = 'resource/enn.js'
with open(file_path, 'r') as file:
    data = file.read()

# pattern = r'".*?":\s*"(.*?)"'
# matches = re.findall(pattern, data)
# for match in matches:
#     print(match)

# pattern1 = r":'(.*?)'"
# pattern2 = r':"(.*?)"'
# match1 = re.findall(pattern1, data)
# match2 = re.findall(pattern2, data)
pattern = r":\s*[\"'](.*?)\s*[\"']"
match = re.findall(pattern, data)
# 打印匹配结果
# print("使用单引号模式匹配到的结果：", match1)
# print("使用双引号模式匹配到的结果：", match2)
print("使用正则表达式模式匹配到的结果：", match)
with open('resource/output.txt', 'w') as output_file:
    for match in match:
        output_file.write(match + '\n')
