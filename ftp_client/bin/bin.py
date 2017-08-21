#! /usr/bin/env python3
# -*-encoding:utf-8 -*-
#@Time 2017/8/21 15:56
#@Author pefami
import sys,os

from ftp_client.core.main import run

f_bin=os.path.dirname(os.path.abspath(__file__))
f_ftp_serve=os.path.dirname(f_bin)
f_ftp_simple=os.path.dirname(f_ftp_serve)
sys.path.append(f_ftp_simple)

if __name__ == "__main__" :
    run()