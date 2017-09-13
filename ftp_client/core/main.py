#! /usr/bin/env python3
# -*-encoding:utf-8 -*-
# @Time 2017/8/21 15:56
# @Author pefami
import socket, json, os, sys

from ftp_client.conf import Settings


class FtpClient:
    ServerAddress = (Settings.ServerIp, Settings.ServerPort)

    def __init__(self):
        self.local_commands = {
            "h": self._help,
            "help": self._help,
            "ls": self._command_ls,
            "cd": self._command_cd,
            "push": self._command_push,
            "pull": self._command_pull

        }
        self.client = socket.socket()
        core_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(core_path)
        self._root_path = os.path.join(base_path, "db")

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
            "ls 'path'": "显示指定路径目录信息，无参时显示当前目录",
            "cd 'path'": "切换到指定路径，无参时切换到当前路径",
            "push -f 'filepath' -d 'targetpath'":
                "上传指定文件，filepath为文件的绝对路径,targetpath为服务器保存路径，默认保存在当前目录",
            "pull -f 'filepath'": "下载服务器端文件，保存在 db 目录下"
        }
        for key, value in desc.items():
            print(key, value, end="   \n")

    def _command_push(self, *args):
        command = args[0]
        try:
            index = command.index('-f')
            local_path = command[index + 1]
            # 判断文件是否存在
            if not os.path.isfile(local_path):
                print("上传的文件不存在")
                return

        except IndexError as e:
            print("push指令使用错误，输入h查看帮助")
        except ValueError as e:
            print("push指令使用错误，输入h查看帮助")

        origin_path = None
        try:
            # 判断是否有定义服务器目录
            origin_index = command.index("-d")
            origin_path = command[origin_index + 1]
        except Exception as e:
            pass

        file_name = os.path.split(local_path)[1]
        # file_size = sys.getsizeof(local_path)
        file_size = os.stat(local_path).st_size
        origin_command = ["push", file_name, str(file_size)]

        # 如果有定义服务器目录，则加入远程命令中
        if origin_path:
            origin_command.append(origin_path)

        # 发送文件头信息，命令,文件名,文件大小,保存路径
        self.client.send(" ".join(origin_command).encode("utf-8"))
        # 接收服务器返回的结果
        header_result = self.client.recv(1024).decode("utf-8");
        header_result = json.loads(header_result)
        if "msg" in header_result:
            print(header_result["msg"])
            return

            # 开始上传文件
        send_size = 0
        print("file_size:", file_size)
        with open(local_path, "rb") as f:
            while send_size != file_size:
                data = f.read(1024)
                self.client.sendall(data)
                send_size += len(data)
                # print("send_size:",send_size)
            else:
                print("文件上传成功")

    def _command_pull(self, *args):
        command = args[0]
        file_name=None
        try:
            index = command.index('-f')
            file_path = command[index + 1]
            path,file_name=os.path.split(file_path)
        except IndexError as e:
            print("push指令使用错误，输入h查看帮助")
            return
        except ValueError as e:
            print("push指令使用错误，输入h查看帮助")
            return

        #命令正确，发送命令给服务器
        origin_command=" ".join(command)
        self.client.sendall(origin_command.encode("utf-8"))

        #等待服务器返馈
        result=self.client.recv(1024).decode("utf-8")
        result=json.loads(result)
        if "msg" in result:
            print(result["msg"])
            return

        #请求下载文件成功
        file_size=result["file_size"]

        #发送等待接收请求
        code=json.dumps({"code":200})
        self.client.sendall(code.encode("utf-8"))

        recv_size=0
        file_path=os.path.join(self._root_path,file_name)
        with open(file_path,"wb") as f :
            while recv_size!=file_size:
                data=self.client.recv(1024)
                f.write(data)
                recv_size+=len(data)
            else:
                print("下载完成")


    def _command_ls(self, *args):
        command = args[0]
        result = self._sendCommand(" ".join(command))
        result = result.decode("utf-8")
        result_dict = json.loads(result)
        if "list" in result_dict:
            print(result_dict["list"])
        elif "msg" in result_dict:
            print(result_dict["msg"])

    def _command_cd(self, *args):
        # 切换到指定目录
        command = args[0]
        result = self._sendCommand(" ".join(command))
        result = result.decode("utf-8")
        result_dict = json.loads(result)
        if "path" in result_dict:
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


# push -f C:\Users\Administrator\Desktop\时间.xml

def run():
    # 创建ftp客户端
    ftp = FtpClient()
    # 连接服务端
    ftp.connet_serve()
