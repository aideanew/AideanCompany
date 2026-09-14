# -*- coding: utf-8 -*-
"""用 faulthandler 抓 console.py 启动卡点"""
import faulthandler
import sys

faulthandler.dump_traceback_later(10, exit=True)
sys.argv = ['console.py']
exec(open(r'E:\Code\AideanCompany\fleet\console\console.py', encoding='utf-8').read())
