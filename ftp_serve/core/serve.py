#! /usr/bin/env python3
# -*-encoding:utf-8 -*-
# @Time 2017/8/21 11:11
# @Author pefami
import socketserver, json, os

from ftp_serve.conf import Settings


# 处理客户端连接请求
class PFMRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.__user = None
            self.auth_identity()
            # 认证成功，切换到该用户当前目录下
            self.handle_command()
        except Exception as e:
            print(e)

    def auth_identity(self):
        while True:
            user_data = self.request.recv(1024)
            user_data = user_data.decode("utf-8")
            user_data = json.loads(user_data)
            username = user_data["username"]
            password = user_data["password"]
            # 根据username去数据库中查找用户是否存在
            conf_path = os.path.dirname(os.path.abspath(__file__))
            serve_base_path = os.path.dirname(conf_path)
            self.__user_path = os.path.join(serve_base_path, "db", username)
            if os.path.isdir(self.__user_path):
                # 用户存在,验证用户的密码是否正确
                user_info_path = os.path.join(self.__user_path, "config")
                if os.path.isfile(user_info_path):
                    with open(user_info_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        self._user_info = info
                        if password == info["password"]:
                            # 密码正确，登录成功
                            self.__user = username
                            self.__show_path = "home"
                            self.__current_path = os.path.join(self.__user_path, self.__show_path)
                            self.request.sendall("success".encode("utf-8"))
                            break
                        else:
                            # 密码错误，登录失败
                            self.request.sendall("密码错误，登录失败！".encode("utf-8"))
                else:
                    # 用户信息文件丢失
                    self.request.sendall("用户信息丢失，请联系管理员！".encode("utf-8"))
            else:
                # 用户不存在
                self.request.sendall("该用户不存在！".encode("utf-8"))

    def handle_command(self):
        self.commands = {
            "ls": self._command_ls,
            "cd": self._command_cd,
            "push": self._command_push,
            "pull": self._command_pull
        }
        while True:
            data = self.request.recv(1024)
            command = data.decode("utf-8")
            items = command.split(" ")
            # 去掉多余的空格
            items = list(filter(lambda x: x, items))
            if len(items) > 0 and items[0] in self.commands:
                self.commands[items[0]](items)
            else:
                self._send_result("无效的命令")

    def _send_result(self, data):
        if isinstance(data, str):
            # 返回的为字符串
            data = data.encode("utf-8")
        data_len = len(data)
        self.request.sendall(str(data_len).encode("utf-8"))

        is_send = self.request.recv(1024).decode("utf-8")
        if is_send != "ok": return
        self.request.sendall(data)

    def _command_ls(self, *args):
        command = args[0]
        if len(command) == 1:
            # 没有指定路径
            self._send_result(json.dumps({"list": os.listdir(self.__current_path)}))
        else:
            path = command[1]
            msg, path, show_path = self.find_path(path)
            if msg:
                self._send_result(msg)
            else:
                self._send_result(json.dumps({"list": os.listdir(path)}))

    # C:\Users\Administrator\PycharmProjects\ftp_simple\ftp_serve\db\root
    def _command_cd(self, *args):
        command = args[0]
        if len(command) == 1:
            # 没有指定路径
            self._send_result(json.dumps({"path": self.__show_path}))
        else:
            path = command[1]
            msg, path, show_path = self.find_path(path)
            if msg:
                self._send_result(msg)
            else:
                self.__show_path = show_path
                self.__current_path = path
                self._send_result(json.dumps({"path": self.__show_path}))

    def _command_push(self, *args):
        command = args[0]
        file_name = command[1]
        file_size = int(command[2])
        file_path = self.__current_path
        if len(command) > 3:
            save_path = command[3]
            msg, path, show_path = self.find_path(save_path)
            if msg:
                # 远程路径保存失败
                self.request.sendall(msg.encode("utf-8"))
                return
            else:
                file_path = path

        # 如果文件存在，覆盖原文件
        file_all_path = os.path.join(file_path, file_name)
        old_file_size = 0
        if os.path.isfile(file_all_path):
            old_file_size = os.stat(file_all_path).st_size

        lave_size = self._user_info["lavesize"]
        lave_size = self.tranform_size(lave_size)
        if lave_size < file_size:
            msg_str = "您的可存储空间为%s ,已不足以上传该文件" % self._user_info["lavesize"]
            msg = json.dump({"msg": msg_str})
            self.request.sendall(msg.endcode("utf-8"))
            return

        # 文件可上传，通知前端上传
        self.request.sendall(json.dumps({"code": 200}).encode("utf-8"))

        # 等待前端上传文件
        recv_size = 0
        with open(os.path.join(file_path, file_name), "wb") as f:
            while file_size != recv_size:
                data = self.request.recv(1024)
                f.write(data)
                recv_size += len(data)

        lave_size = lave_size + old_file_size - recv_size
        self._user_info["lavesize"] = self.tranform_size(lave_size)
        user_info_path = os.path.join(self.__user_path, "config")
        # 保存用户最新信息
        json.dump(self._user_info, open(user_info_path, "w", encoding="utf-8"))

    def _command_pull(self, *args):
        command = args[0]
        file_path = command[2]
        # 转换文件路径为目录路径
        dir_path, file_name = os.path.split(file_path)
        # 转换为绝对路径
        msg, path, relative_path = self.find_path(dir_path)

        if msg:
            # 路径不正确，返回错误信息
            self.request.sendall(msg.encode("utf-8"))
            return

        # 路径正确，判断文件存不存在
        abs_path = os.path.join(path, file_name)
        if not os.path.isfile(abs_path):
            msg = json.dumps({"msg": "目标文件不存在"})
            self.request.sendall(msg.encode("utf-8"))
            return

        # 文件存在，发送正确代码，及文件大小
        file_size = os.stat(abs_path).st_size
        code = json.dumps({"code": 200, "file_size": file_size})
        self.request.sendall(code.encode("utf-8"))

        # 客户端是否接收文件
        result = self.request.recv(1024).decode("utf-8")
        result = json.loads(result)

        if "msg" in result:
            return

            # 开始发送文件
        send_size = 0
        with open(abs_path, "rb") as f:
            while file_size != send_size:
                data = f.read(1024)
                self.request.sendall(data)
                send_size += len(data)

    # 查找路径是否合法
    def find_path(self, path):
        msg = None
        if not path:
            return msg, self.__current_path, self.__show_path

        # 判断路径是否是绝对路径
        if os.path.isabs(path):
            # 绝对路径
            if path.startswith(self.__user_path, 0, len(path) - 2):
                last_path = path[len(self.__user_path) + 1:]
                # 判断路径是否存在
                if os.path.isdir(path):
                    # 存在，返回绝对路径和用户路径
                    return None, path, last_path
                else:
                    # 不存在，返回错误信息
                    msg = json.dumps({"msg": "访问目录不存在"})
                    return msg, None, None
            else:
                # 路径属于绝对路径，但不是在该用户目录下，无权访问
                msg = json.dumps({"msg": "无权访问该目录"})
                return msg, None, None
        else:
            # 相对路径，拼接全路径
            if path == ".." or path == '../':
                # 返回上一个路径
                abs_path = os.path.dirname(self.__current_path)
                if abs_path == self.__user_path:
                    msg = json.dumps({"msg": "已经到了能访问的最上层了"})
                    return msg, None, None
            elif path == "." or path == './':
                # 以点开头，表示当前目录
                return None, self.__current_path, self.__show_path
            else:
                abs_path = os.path.join(self.__current_path, path)

            if os.path.isdir(abs_path):
                last_path = abs_path[len(self.__user_path) + 1:]
                return None, abs_path, last_path
            else:
                msg = json.dumps({"msg": "访问目录不存在"})
                return msg, None, None

    def tranform_size(self, size):
        if isinstance(size, str):
            if size.endswith("G"):
                return int(size.replace("G", "")) * 1024 * 1024 * 1024
            elif size.endswith("M"):
                return int(size.replace("M", "")) * 1024 * 1024
            elif size.endswith("K"):
                return int(size.replace("K", "")) * 1024
        elif isinstance(size, int):
            if size > 1024 * 1024 * 1024:
                return str(int(size / (1024 * 1024 * 1024))) + "G"
            elif size > 1024 * 1024:
                return str(int(size / (1024 * 1024))) + "M"
            elif size > 1024:
                return str(int(size / 1024)) + "K"


# 开启FTP服务端
def startServer():
    address = (Settings.ServerIp, Settings.ServerPort)
    serve = socketserver.ThreadingTCPServer(address, PFMRequestHandler)
    serve.serve_forever()
