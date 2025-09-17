import os
import config
import tools

class Player:
    def __init__(self, userName, password, money=config.INIT_MONEY):
        self.userName = userName
        self.password = password
        self.money = money

    def storeData(self):
        nameHash = tools.nameToHash(self.userName)
        pwdHash = tools.pwdToHash(self.password)
        path = os.path.join(config.USER_DATA_PATH, nameHash + ".json")
        tools.createPathIfNotExist(config.USER_DATA_PATH)
        data = {
            "userName": nameHash,
            "password": pwdHash,
            "money": self.money
        }
        tools.setJsonData(path, data)

    @classmethod
    def create(cls, userName, password):
        nameHash = tools.nameToHash(userName)
        path = os.path.join(config.USER_DATA_PATH, nameHash + ".json")
        if not os.path.exists(path):
            return cls(userName, password)
        else:
            data = tools.getJsonData(path)
            pwd = tools.pwdToHash(password)
            storedPwd = data["password"]
            if storedPwd != pwd:
                raise RuntimeError("Invalid password")
            return cls(userName, password)
