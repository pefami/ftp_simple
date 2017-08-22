#! /usr/bin/env python3
# -*-encoding:utf-8 -*-
# @Time 2017/8/21 15:56
# @Author pefami
import socket, json

from ftp_client.conf import Settings


class FtpClient:
    ServerAddress = (Settings.ServerIp, Settings.ServerPort)

    def __init__(self):
        self.local_commands = {
            "h": self._help,
            "help": self._help,
            "ls": self._command_ls,
            "cd": self._command_cd
        }
        self.client = socket.socket()

    def connet_serve(self):
        self.client.connect(FtpClient.ServerAddress)
        # 连接以后进行用户认证
        self.auth_identity()
        # 连接成功后进行操作
        self.local_shell()

    def local_shell(self):
        while True:
            # 进行命令操作
            command = input("\n" + self.__current_path + " >>:")
            items = command.split(" ")
            # 去掉多余的空格
            items = list(filter(lambda x: x, items))
            if len(items) > 0 and items[0] in self.local_commands:
                self.local_commands[items[0]](items)
            else:
                print("无效的命令")

    def auth_identity(self):
        while True:
            username = input("Username:")
            password = input("Password:")
            # 发送给服务端进行验证
            auth_data = json.dumps({"username": username, "password": password})
            self.client.sendall(auth_data.encode("utf-8"))

            # 等待服务端结果返回
            auth_result = self.client.recv(1024)
            auth_result = auth_result.decode("utf-8")
            if auth_result == "success":
                # 认证成功
                print("认证成功")
                # 查询一次当前路径
                self._command_cd("cd".split(" "))
                break
            else:
                # 认证失败，显示失败信息
                print(auth_result)

    def _help(self, *args):
        # 显示帮助信息
        desc = {
            "h,help": "显示帮助信息",
            "ls ‘path’": "显示指定路径目录信息，无参时显示当前目录",
            "cd 'path'": "切换到指定路径，无参时切换到当前路径"
        }
        for key, value in desc.items():
            print(key, value, end="   \n")

    def _command_ls(self):
        pass

    def _command_cd(self, *args):
        # 切换到指定目录
        command = args[0]
        result = self._sendCommand(" ".join(command))
        result=result.decode("utf-8")
        result_dict=json.loads(result)
        if "path" in result_dict :
            self.__current_path = result_dict["path"]
        elif "msg" in result_dict:
            print(result_dict["msg"])

    def _sendCommand(self, command):
        # 远程的命令，发送给服务端处理
        self.client.sendall(command.encode("utf-8"))
        result_len = int(self.client.recv(1024).decode("utf-8"))
        recv_len = 0
        result_data = bytes()
        # 准备就绪，通知后台发送结果
        # print(result_len,recv_len)
        self.client.sendall("ok".encode("utf-8"))
        while recv_len != result_len:
            data = self.client.recv(1024)
            recv_len += len(data)
            result_data += data
        return result_data


def run():
    # 创建ftp客户端
    ftp = FtpClient()
    # 连接服务端
    ftp.connet_serve()
