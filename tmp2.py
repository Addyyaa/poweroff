a = ['deviceId=PStestScreenL0001']
with open("screenId.ini", "r", encoding='utf-8') as f:
    lines = [i.replace("\n", "") for i in (f.readlines())]
print(lines)
