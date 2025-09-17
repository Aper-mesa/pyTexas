import hashlib
import json
import os

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
