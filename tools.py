import hashlib
import json
import os
import sys

import i18n


def createPathIfNotExist(path):
    if not os.path.exists(path):
        os.makedirs(path)


def nameToHash(name):
    return hashlib.sha1(name.encode("utf8")).hexdigest()


def pwdToHash(password):
    return hashlib.sha1(password.encode("utf8")).hexdigest()


def getJsonData(path):
    try:
        with open(path, "r", encoding="utf8") as f:
            return json.loads(f.read())
    except:
        return {}


def setJsonData(path, data):
    with open(path, "w", encoding="utf8") as f:
        f.write(json.dumps(data, ensure_ascii=False))

def resource_path(relative_path):
    """ 获取资源的绝对路径，无论是从源码运行还是从打包后的exe运行 """
    try:
        # PyInstaller 会创建一个临时文件夹 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是在打包后运行，就用脚本所在的目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)