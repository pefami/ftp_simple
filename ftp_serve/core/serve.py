#! /usr/bin/env python3
# -*-encoding:utf-8 -*-
# @Time 2017/8/21 11:11
# @Author pefami
import socketserver, json, os

from ftp_serve.conf import Settings


# 处理客户端连接请求
class PFMRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.__user = None
        self.auth_identity()
        # 认证成功，切换到该用户当前目录下

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
            user_path = os.path.join(serve_base_path, "db", username)
            if os.path.isdir(user_path):
                # 用户存在,验证用户的密码是否正确
                user_info = os.path.join(user_path, "config")
                if os.path.isfile(user_info):
                    with open(user_info, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        if password == info["password"]:
                            # 密码正确，登录成功
                            self.__user = username
                            self.__current_path = os.path.join(user_path, "home")
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


# 开启FTP服务端
def startServer():
    address = (Settings.ServerIp, Settings.ServerPort)
    serve = socketserver.ThreadingTCPServer(address, PFMRequestHandler)
    serve.serve_forever()
