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
                user_info = os.path.join(self.__user_path, "config")
                if os.path.isfile(user_info):
                    with open(user_info, "r", encoding="utf-8") as f:
                        info = json.load(f)
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
            "cd": self._command_cd
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
        command=args[0]
        if len(command) == 1:
            # 没有指定路径
            self._send_result(json.dumps({"list": os.listdir(self.__current_path)}))
        else:
            path = command[1]
            # 判断路径是否是绝对路径
            if os.path.isabs(path):
                # 绝对路径
                if path.startswith(self.__user_path, 0, len(path) - 2):
                    last_path = path[len(self.__user_path) + 1:]
                    # 判断路径是否存在
                    if os.path.isdir(path):
                        # 存在，显示目录
                        self._send_result(json.dumps({"list": os.listdir(path)}))
                    else:
                        # 不存在，返回错误信息
                        self._send_result(json.dumps({"msg": "访问目录不存在"}))
                else:
                    # 路径属于绝对路径，但不是在该用户目录下，无权访问
                    self._send_result(json.dumps({"msg": "无权访问该目录"}))
            else:
                # 相对路径，拼接全路径
                if path == "..":
                    # 返回上一个路径
                    abs_path = os.path.dirname(self.__current_path)
                    if abs_path == self.__user_path:
                        self._send_result(json.dumps({"msg": "无权访问该目录"}))
                        return
                elif path=="." or path.startswith(".") :
                    #以点开头，表示当前目录
                    self._send_result(json.dumps({"list": os.listdir(self.__current_path)}))
                    return
                else:
                    abs_path = os.path.join(self.__current_path, path)

                if os.path.isdir(abs_path):
                    self._send_result(json.dumps({"list": os.listdir(abs_path)}))
                else:
                    self._send_result(json.dumps({"msg": "访问目录不存在"}))


    # C:\Users\Administrator\PycharmProjects\ftp_simple\ftp_serve\db\root
    def _command_cd(self, *args):
        command = args[0]
        if len(command) == 1:
            # 没有指定路径
            self._send_result(json.dumps({"path": self.__show_path}))
        else:
            path = command[1]
            # 判断路径是否是绝对路径
            if os.path.isabs(path):
                # 绝对路径
                if path.startswith(self.__user_path, 0, len(path) - 2):
                    last_path = path[len(self.__user_path) + 1:]
                    # 判断路径是否存在
                    if os.path.isdir(path):
                        # 存在，切换到指定目录下
                        self.__show_path = last_path
                        self.__current_path = path
                        self._send_result(json.dumps({"path": self.__show_path}))
                    else:
                        # 不存在，返回错误信息
                        self._send_result(json.dumps({"msg": "访问目录不存在"}))
                else:
                    # 路径属于绝对路径，但不是在该用户目录下，无权访问
                    self._send_result(json.dumps({"msg": "无权访问该目录"}))
            else:
                # 相对路径，拼接全路径
                if path == "..":
                    # 返回上一个路径
                    abs_path = os.path.dirname(self.__current_path)
                    if abs_path == self.__user_path:
                        self._send_result(json.dumps({"msg": "已经到了能访问的最上层了"}))
                        return
                elif path=="." or path.startswith(".") :
                    #以点开头，表示当前目录
                    self._send_result(json.dumps({"path": self.__show_path}))
                    return
                else:
                    abs_path = os.path.join(self.__current_path, path)

                if os.path.isdir(abs_path):
                    self.__show_path = abs_path[len(self.__user_path) + 1:]
                    self.__current_path=abs_path
                    self._send_result(json.dumps({"path": self.__show_path}))
                else:
                    self._send_result(json.dumps({"msg": "访问目录不存在"}))


# 开启FTP服务端
def startServer():
    address = (Settings.ServerIp, Settings.ServerPort)
    serve = socketserver.ThreadingTCPServer(address, PFMRequestHandler)
    serve.serve_forever()
