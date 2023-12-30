import asyncio, telnetlib3

async def telnet_login(host, port, username, password):
    # 创建 Telnet 连接
    reader, writer = await telnetlib3.open_connection(host, port)

    try:
        # 读取服务器返回的欢迎信息
        welcome_message = await reader.readuntil(b"(none) login:")
        print(welcome_message.decode("ascii"))

        # 发送用户名
        await writer.write(username.encode("ascii"))

        # 读取服务器返回的密码提示
        password_prompt = await reader.readuntil(b"Password:")
        print(password_prompt.decode("ascii"))

        # # 发送密码
        # writer.write(password.encode("ascii") + b"\n")
        # await writer.drain()
        #
        # # 读取登录后的信息
        # login_result = await reader.readuntil(b"#")  # 这里假设登录后提示符是 "$"
        # print(login_result.decode("ascii"))
        #
        # # 在这里可以执行其他操作，如发送命令等

    finally:
        # 关闭连接
        writer.close()

# 使用示例
import asyncio

asyncio.run(telnet_login("192.168.0.105", 23, "root", "ya!2dkwy7-934^"))