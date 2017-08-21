#! /usr/bin/env python3
# -*-encoding:utf-8 -*-
#@Time 2017/8/21 15:56
#@Author pefami
import socket,json

from ftp_client.conf import Settings


class FtpClient:
    ServerAddress=(Settings.ServerIp,Settings.ServerPort)
    def __init__(self):
        commands = {
            "h": self._help,
            "help":self._help
        }
        self.client=socket.socket()

    def connet_serve(self):
        self.client.connect(FtpClient.ServerAddress)
        #连接以后进行用户认证
        self.auth_identity()
        #连接成功后进行操作
        self.local_shell()

    def local_shell(self):
        while True :
            #进行命令操作
            command=input(self.__current_path+" >>>")


    def auth_identity(self):
        while True :
            username=input("Username:")
            password=input("Password:")
            #发送给服务端进行验证
            auth_data=json.dumps({"username":username,"password":password})
            self.client.sendall(auth_data.encode("utf-8"))

            #等待服务端结果返回
            auth_result=self.client.recv(1024)
            auth_result=auth_result.decode("utf-8")
            if auth_result == "success" :
                #认证成功
                print("认证成功")
                self.__current_path="home"
                break
            else :
                #认证失败，显示失败信息
                print(auth_result)

    def _help(self):
        #显示帮助信息
        pass

def run():
    #创建ftp客户端
    ftp=FtpClient()
    #连接服务端
    ftp.connet_serve()