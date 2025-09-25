import hashlib
import json
import os
import sys

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
        # PyInstaller 会创建一个临时文件夹 _MEIPASS 并把资源放在那里
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)