import asyncio
import re
import telnetlib3
import logging

# 嘗試導入 telnetlib3 的特定類型，如果失敗也沒關係，後面有檢查
try:
    from telnetlib3.stream_writers import TelnetWriterUnicode
except ImportError:
    TelnetWriterUnicode = None  # 定義一個佔位符


def ip_address_validator(ip: str) -> bool:
    """驗證給定的字符串是否為有效的 IPv4 或 IPv6 地址。

    Args:
        ip: 需要驗證的 IP 地址字符串。

    Returns:
        如果 IP 地址有效則返回 True，否則返回 False。

    Raises:
        TypeError: 如果輸入的 ip 不是字符串類型。
    """
    ipv4_pattern = re.compile(
        r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )

    ipv6_pattern = re.compile(
        r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
        r'^::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,6}::([0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,5}:([0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}$|'
        r'^([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}$|'
        r'^[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})$|'
        r'^:((:[0-9a-fA-F]{1,4}){1,7}|:)$'
    )
    if not isinstance(ip, str):
        raise TypeError("IP 地址必須為字符串類型")

    ip_str = ip.strip()
    if '.' in ip_str:
        return bool(ipv4_pattern.match(ip_str))
    elif ':' in ip_str:
        return bool(ipv6_pattern.match(ip_str))
    else:
        return False


class Telnet_connector:
    """提供非同步 Telnet 連接和命令執行功能的類。

    通過此類，可以連接到 Telnet 服務器，發送命令，並獲取響應。
    支持異步上下文管理器 (`async with`) 自動管理連接。

    Attributes:
        host (str): 目標 Telnet 服務器的主機名或 IP 地址。
        reader (asyncio.StreamReader | None): 用於讀取數據的異步流讀取器。
        writer (asyncio.StreamWriter | None): 用於寫入數據的異步流寫入器。
        is_unicode_mode (bool): 標識當前連接是否處於 Unicode 模式（由 telnetlib3 協商）。
    """

    def __init__(self, host: str, port=23, username=None, password=None):
        """初始化 Telnet_connector。

        Args:
            host: 目標 Telnet 服務器的主機名或 IP 地址。
            port: 目標 Telnet 服務器的端口號，默認為 23。
            username: 登錄用戶名，如果需要。
            password: 登錄密碼，如果需要。

        Raises:
            ValueError: 如果提供的 host 不是有效的 IP 地址或主機名。
        """
        if not ip_address_validator(host):
            raise ValueError("Invalid host")
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.is_unicode_mode = False  # 添加標誌
        self.shell = None  # 如果需要的话
        self.username = username if username else 'root'
        self.password = password if password else 'ya!2dkwy7-934^'
        print(f"username: {self.username}, password: {self.password}")
        print(f"Telnet_connector initialized for host: {self.host}")

    async def connect(self, timeout=30):
        """建立到目標主機的 Telnet 連接。

        如果已存在連接，則此方法不執行任何操作。
        連接成功後，會設置 self.reader 和 self.writer。
        會檢測並設置 self.is_unicode_mode 標誌。

        Raises:
            ConnectionError: 如果連接超時、被拒絕或發生其他連接錯誤。
            Exception: 其他底層異常。
        """
        if self.writer:
            print("Already connected.")
            return
        print(f"Connecting to {self.host}...")
        try:
            self.reader, self.writer = await asyncio.wait_for(
                telnetlib3.open_connection(self.host, self.port, shell=self.shell),
                timeout=timeout
            )
            print(f"Successfully connected to {self.host}.")
            # 檢查 writer 類型以確定是否為 Unicode 模式
            # 首先確保 TelnetWriterUnicode 已成功導入且 self.writer 不是 None
            if TelnetWriterUnicode is not None and self.writer is not None:
                if isinstance(self.writer, TelnetWriterUnicode):  # type: ignore[arg-type]
                    logging.debug("Connection is using Unicode mode.")
                    self.is_unicode_mode = True
                else:
                    # writer 存在但不是 TelnetWriterUnicode，假定為 Bytes 模式
                    logging.debug("Connection is using Bytes mode (standard writer detected).")
                    self.is_unicode_mode = False
            elif self.writer is not None:
                # TelnetWriterUnicode 導入失敗，但 writer 存在，假定為 Bytes 模式
                logging.debug("Connection is using Bytes mode (TelnetWriterUnicode import failed).")
                self.is_unicode_mode = False
            else:
                # writer 為 None，連接失敗
                logging.debug("Writer is None, connection likely failed earlier.")
                self.is_unicode_mode = False  # 設置為 False 以防萬一

            # 自动登录
            await self._auto_login()
            # 可選：如果需要，讀取初始橫幅/提示
            # initial_output = await self.read_until_timeout()
            # print(f"Initial output:\n{initial_output}")
        except asyncio.TimeoutError:
            logging.debug(f"Connection to {self.host} timed out.")
            self.reader = None
            self.writer = None
            raise ConnectionError(f"Connection timed out to {self.host}")
        except ConnectionRefusedError:
            logging.debug(f"Connection to {self.host} refused.")
            self.reader = None
            self.writer = None
            raise ConnectionError(f"Connection refused by {self.host}")
        except Exception as e:
            logging.debug(f"Failed to connect to {self.host}: {e}")
            self.reader = None
            self.writer = None
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def _auto_login(self):
        """自动检测登录提示并输入用户名和密码"""
        if not self.username or not self.password:
            return  # 未设置用户名密码则跳过
        # 读取初始输出，查找 login/username/password 提示
        output = await self.read_until_timeout(2)
        if any(x in output.lower() for x in ["login:", "username:"]):
            self.writer.write(self.username + "\r\n")
            await self.writer.drain()
            output = await self.read_until_timeout(2)
        if "password:" in output.lower():
            self.writer.write(self.password + "\r\n")
            await self.writer.drain()
            await asyncio.sleep(1)  # 等待登录完成

    async def disconnect(self):
        """關閉當前的 Telnet 連接。

        如果沒有活動連接，則此方法不執行任何操作。
        會嘗試優雅地關閉寫入器並等待其關閉。
        """
        if self.writer:
            print(f"Disconnecting from {self.host}...")
            try:
                # 動態檢查 writer 類型 (確保 writer 和 TelnetWriterUnicode 都非 None)
                is_unicode_writer = False
                # --- Start nested check ---
                if self.writer is not None:
                    if TelnetWriterUnicode is not None:
                        # Both self.writer and TelnetWriterUnicode are known to be non-None here
                        is_unicode_writer = isinstance(self.writer, TelnetWriterUnicode)  # type: ignore[arg-type]
                # --- End nested check ---

                if self.writer is not None and not self.writer.is_closing():   # Also ensure writer is not None
                    # before is_closing()
                    self.writer.close()
                    # 根據當前 writer 類型決定如何等待關閉
                    if not is_unicode_writer and hasattr(self.writer, 'wait_closed'):
                        # 標準 StreamWriter
                        logging.debug("Waiting for standard writer closure...")
                        await self.writer.wait_closed()
                    elif is_unicode_writer:
                        # TelnetWriterUnicode 可能沒有 wait_closed 或類似方法
                        # close() 可能已經足夠，或者需要短暫等待
                        logging.debug("Closing Unicode writer, assuming close() is sufficient or using fallback sleep.")
                        await asyncio.sleep(0.1)  # 短暫等待以允許關閉操作完成
                    else:
                        logging.debug("Unknown writer type or mode, using fallback sleep after close().")
                        await asyncio.sleep(0.1)  # Fallback
                print("Connection closed.")
            except Exception as e:
                logging.debug(f"Error during disconnect: {e}")
            finally:
                self.writer = None
                self.reader = None
        else:
            print("Already disconnected.")

    async def read_until_timeout(self, read_timeout: float = 1) -> str:
        """從連接讀取數據，直到指定的超時時間內沒有更多數據到達。

        此方法會持續讀取數據塊，直到 `reader.read()` 在 `read_timeout` 秒內
        沒有返回任何數據，這通常表示服務器已停止發送響應。
        無論底層接收到的是字節串還是字符串，最終都返回統一的字符串。

        Args:
            read_timeout: 在認為讀取完成之前，等待新數據的最長時間（秒）。

        Returns:
            從連接讀取到的所有數據，組合成的單個字符串。

        Raises:
            ConnectionError: 如果在讀取時連接未建立或已斷開。
        """
        if not self.reader:
            raise ConnectionError("Not connected.")

        output = ""  # 初始化為空字符串
        while True:
            try:
                # print(f"DEBUG: Waiting for data (timeout={read_timeout}s)...")
                chunk = await asyncio.wait_for(self.reader.read(4096), timeout=read_timeout)
                # print(f"DEBUG: Received chunk raw: {chunk!r} (type: {type(chunk)})")

                if not chunk:
                    logging.debug("Connection closed by remote host while reading.")
                    self.reader = None
                    self.writer = None
                    break

                if isinstance(chunk, bytes):
                    # print("DEBUG: Decoding received bytes chunk.")
                    chunk_str = chunk.decode('utf-8', errors='ignore')
                elif isinstance(chunk, str):
                    # print("DEBUG: Received string chunk directly.")
                    chunk_str = chunk
                else:
                    logging.debug(f"!!! WARNING: Received chunk of unexpected type: {type(chunk)}. Skipping.")
                    continue

                # 累加字符串
                output += chunk_str

            except asyncio.TimeoutError:
                # logging.debug("DEBUG: Read timeout occurred. Finishing read.")
                if not output:  # 检查 output 是否为空
                    logging.debug("Read timeout occurred before receiving any data.")
                else:
                    logging.debug(f"Read timeout occurred after receiving partial "
                                  f"data (length={len(output)}).Finishing read.")
                break
            except ConnectionAbortedError:
                logging.debug("Connection aborted while reading.")
                self.reader = None
                self.writer = None
                break
            except Exception as e:
                logging.debug(f"Error reading stream: {e} (Type: {type(e)})")
                self.reader = None
                self.writer = None
                break
        # logging.debug(f"DEBUG: Returning final string output (length={len(output)})")
        return output  # 直接返回累加的字符串

    async def send_command(self, command: str, read_timeout: float = 1.0) -> str:
        """向 Telnet 服務器發送命令並讀取響應。

        會自動在命令末尾添加 '\r\n'。
        增加了重連機制，在發生特定類型的 ConnectionError 時最多重試 2 次。
        該方法會嘗試智能地處理 telnetlib3 的 Unicode 模式和 Bytes 模式：
        1. 首先嘗試以字符串形式發送命令。
        2. 如果失敗並收到 "bytes-like object is required" 錯誤，則回退到
           以 UTF-8 編碼的字節串形式發送。
        發送成功後，調用 `read_until_timeout` 讀取服務器響應。

        Args:
            command: 要發送的命令字符串（不含結尾的換行符）。
            read_timeout: 發送命令後，等待響應數據的超時時間（秒），
                          傳遞給 `read_until_timeout`。

        Returns:
            服務器對命令的響應字符串。

        Raises:
            ConnectionError: 如果連接未建立、已關閉，或在發送/讀取過程中發生連接錯誤（包括重試失敗後）。
            TypeError: 如果底層 writer 的行為異常，無法處理字符串或字節串。
        """
        max_retries = 2
        last_exception: Exception | None = None  # 保存最后一次异常
        base_retry_delay = 1.0  # 基础重试延迟（秒）
        retry_delay_multiplier = 2.0  # 指数退避倍数

        for attempt in range(max_retries + 1):
            try:
                # --- 每次尝试前检查连接状态 ---
                if not self.writer or not self.reader or self.writer.is_closing():
                    # 如果没有 writer 或 reader，或者 writer 正在关闭，尝试连接（或重连）
                    logging.warning(f"[Attempt {attempt+1}/{max_retries+1}] Connection not established or closing. "
                                    f"Attempting to connect... (writer: {bool(self.writer)}, reader: {bool(self.reader)}, "
                                    f"closing: {self.writer.is_closing() if self.writer else 'N/A'})")
                    # 只有在 writer 存在且未关闭时才尝试优雅断开
                    if self.writer and not self.writer.is_closing():
                        await self.disconnect()  # 清理现有连接
                    await self.connect()  # connect() raises ConnectionError on failure
                    # 再次检查，如果 connect 成功但 writer/reader 仍是 None (理论上不应发生)
                    if not self.writer or not self.reader:
                        raise ConnectionError("Failed to establish connection components after connect().")
                    # 连接成功后，尝试读取初始数据以验证连接有效性
                    logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Connection established, validating with initial read...")
                    initial_response = await self.read_until_timeout(read_timeout=0.5)
                    logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Initial read result (length={len(initial_response)}): {initial_response[:50]!r}...")
                    
                    # 检查是否需要登录
                    if initial_response and ("login:" in initial_response.lower() or "username:" in initial_response.lower()):
                        if self.username:
                            logging.info(f"检测到登录提示，发送用户名: {self.username}")
                            login_response = await self._send_raw_command(self.username)
                            # 等待密码提示
                            await asyncio.sleep(0.5)
                        else:
                            error_msg = "检测到登录提示，但未设置用户名，无法继续"
                            logging.error(error_msg)
                            raise ConnectionError(error_msg)
                    
                    # 检查是否需要输入密码
                    if initial_response and "password:" in initial_response.lower():
                        if self.password:
                            logging.info("检测到密码提示，发送密码")
                            pwd_response = await self._send_raw_command(self.password)
                            # 等待登录完成
                            await asyncio.sleep(1)
                        else:
                            error_msg = "检测到密码提示，但未设置密码，无法继续"
                            logging.error(error_msg)
                            raise ConnectionError(error_msg)

                # --- 准备命令 ---
                command_str = command + '\r\n'
                command_bytes = command_str.encode('utf-8', errors='ignore')
                write_attempted_type = "string"  # 重置尝试类型

                # --- 发送命令 (包含原有 str/bytes 尝试逻辑) ---
                try:
                    logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] "
                                  f"Attempting to send command as string: {command_str!r}")
                    self.writer.write(command_str)  # type: ignore

                except TypeError as te:
                    error_msg = str(te).lower()
                    logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] TypeError sending string: {te}")
                    if "bytes-like object is required" in error_msg:
                        logging.debug(f"[Attempt {attempt+1}/{max_retries+1}]"
                                      f" String write failed, retrying with bytes: {command_bytes!r}")
                        try:
                            write_attempted_type = "bytes (retry)"
                            self.writer.write(command_bytes)
                        except Exception as retry_e:
                            logging.debug(f"[Attempt {attempt+1}/{max_retries+1}]"
                                          f" Error during byte retry write: {retry_e}")
                            last_exception = ConnectionError(f"Failed to send command on byte retry: {retry_e}")
                            raise last_exception  # 触发外层 ConnectionError 处理
                    # Keep other TypeError handling as before, re-raising them
                    elif "encoding without a string argument" in error_msg:
                        logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Unexpected 'encoding' error when "
                                      f"sending string.")
                        # Raise the original TypeError, do not retry connection for this
                        raise ConnectionError(f"Unexpected encoding error sending string: {te}") from te
                    else:
                        logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Unknown TypeError during string write.")
                        raise ConnectionError(f"Unknown TypeError sending command: {te}") from te

                # --- Drain and Read ---
                logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Write ({write_attempted_type}) successful, "
                              f"draining buffer...")
                await self.writer.drain()  # May raise ConnectionError
                logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Command sent, reading response...")
                response = await self.read_until_timeout(read_timeout)  # May raise ConnectionError

                # --- 检查响应是否为空且连接已断开 ---
                if not response and (not self.reader or not self.writer or self.writer.is_closing()):
                    logging.warning(f"[Attempt {attempt+1}/{max_retries+1}] Empty response received and connection appears broken. Treating as connection error.")
                    raise ConnectionError("Empty response with broken connection detected.")
                
                # --- 检查响应中是否含有登录提示 ---
                # 添加一个标志来限制登录检测次数，防止无限循环
                login_retry_count = getattr(self, '_login_retry_count', 0)
                max_login_retries = 2  # 最大登录重试次数
                
                if response and ("login:" in response.lower() or "username:" in response.lower() or "password:" in response.lower()) and login_retry_count < max_login_retries:
                    # 递增登录重试计数
                    self._login_retry_count = login_retry_count + 1
                    logging.warning(f"[Attempt {attempt+1}/{max_retries+1}] Login prompt detected in response. Attempting to login.")
                    # 尝试登录
                    if "login:" in response.lower() or "username:" in response.lower():
                        if self.username:
                            await self._send_raw_command(self.username)
                            await asyncio.sleep(0.5)
                        else:
                            error_msg = "响应中检测到登录提示，但未设置用户名，无法继续"
                            logging.error(error_msg)
                            raise ConnectionError(error_msg)
                    if "password:" in response.lower():
                        if self.password:
                            await self._send_raw_command(self.password)
                            await asyncio.sleep(1)
                        else:
                            error_msg = "响应中检测到密码提示，但未设置密码，无法继续"
                            logging.error(error_msg)
                            raise ConnectionError(error_msg)
                    # 重新发送原命令
                    logging.info(f"[Attempt {attempt+1}/{max_retries+1}] Re-sending command after login")
                    self.writer.write(command_str)
                    await self.writer.drain()
                    response = await self.read_until_timeout(read_timeout)
                elif response and ("login:" in response.lower() or "username:" in response.lower() or "password:" in response.lower()):
                    # 超过最大登录重试次数
                    error_msg = f"达到最大登录重试次数({max_login_retries})，但仍检测到登录提示"
                    logging.error(error_msg)
                    raise ConnectionError(error_msg)
                elif response and 'notfount' in response.lower():
                    # 重新发送指令
                    logging.info(f"[Attempt {attempt+1}/{max_retries+1}] Re-sending command after notfount")
                    # 执行指令前先发送回车
                    await self._send_raw_command('\n')
                    self.writer.write(command_str)
                    await self.writer.drain()
                    response = await self.read_until_timeout(read_timeout)
                else:
                    # 重置登录重试计数
                    self._login_retry_count = 0

                # --- Success ---
                logging.debug(f"[Attempt {attempt+1}/{max_retries+1}] Command executed successfully. Response length: {len(response)}")
                return response  # 成功，退出循环并返回结果

            except ConnectionError as ce:
                last_exception = ce  # 保存当前异常
                logging.warning(f"[Attempt {attempt+1}/{max_retries+1}] ConnectionError occurred: {ce}")
                if attempt < max_retries:
                    # 检查是否为可重试的错误类型
                    error_str = str(ce).lower()
                    is_retryable = any(keyword in error_str for keyword in ["timeout", "aborted", "broken", "closing", "not connected"])
                    if not is_retryable:
                        logging.error(f"[Attempt {attempt+1}/{max_retries+1}] Non-retryable ConnectionError: {ce}. Aborting retries.")
                        raise ce  # 非可重试错误，直接抛出
                    logging.info(f"Retrying command send ({max_retries - attempt}/{max_retries} retries left)...")
                    # 指数退避延迟
                    retry_delay = base_retry_delay * (retry_delay_multiplier ** attempt)
                    logging.info(f"Waiting {retry_delay:.1f} seconds before retry...")
                    await asyncio.sleep(retry_delay)
                    # connect() is called at the start of the next loop iteration
                    continue  # 继续下一次循环尝试
                else:
                    logging.error(f"Command send failed after {max_retries} retries due to ConnectionError: {ce}")
                    raise last_exception  # 重试次数用尽，抛出最后一次的 ConnectionError
            except Exception as e:
                logging.error(f"[Attempt {attempt+1}/{max_retries+1}] "
                              f"Unexpected error during send_command: {e}", exc_info=True)
                # For unexpected errors, don't retry, just raise
                raise ConnectionError(f"Unexpected error during command send: {e}") from e

        # 这部分理论上不应该执行到，因为要么成功返回，要么抛出异常
        # 但为了代码完整性，如果循环结束还没有返回或抛出异常，则抛出错误
        raise ConnectionError(f"Command send failed unexpectedly after {max_retries + 1} attempts. Last known error: "
                              f"{last_exception}")

    async def _send_raw_command(self, command: str) -> str:
        """发送原始命令，不包含重试逻辑，仅用于内部调用

        Args:
            command: 要发送的命令

        Returns:
            命令响应
        """
        if not self.writer or not self.reader:
            raise ConnectionError("Not connected")
        
        command_str = command + '\r\n'
        try:
            self.writer.write(command_str)
            await self.writer.drain()
            return await self.read_until_timeout(0.5)
        except Exception as e:
            logging.error(f"Error in _send_raw_command: {e}")
            raise ConnectionError(f"Failed to send raw command: {e}")

    # 上下文管理器支持自動連接/斷開
    async def __aenter__(self):
        """异步上下文管理器的进入方法，建立连接。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器的退出方法，断开连接。"""
        await self.disconnect()
