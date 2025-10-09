import os
import config
import tools


class Player:
    def __init__(self, steam_id, username, money=config.INIT_MONEY):
        self.steam_id = str(steam_id)
        self.username = username
        self.money = money

    def storeData(self):
        tools.createPathIfNotExist(config.USER_DATA_PATH)
        data = {
            "steam_id": self.steam_id,
            "username": self.username,
            "money": self.money,
        }
        tools.setJsonData(os.path.join(config.USER_DATA_PATH, self.steam_id + ".json"), data)

    @classmethod
    def create(cls, steam_id, username):
        steam_id = str(steam_id)
        path = os.path.join(config.USER_DATA_PATH, steam_id + ".json")

        if not os.path.exists(path):
            p = cls(steam_id=steam_id, username=username)
            p.storeData()
            return p

        data = tools.getJsonData(path) or {}
        saved_money = data.get("money", config.INIT_MONEY)
        saved_username = data.get("username", username)

        p = cls(steam_id=steam_id, username=saved_username, money=saved_money)

        if p.username != username:
            p.username = username
            p.storeData()

        return p

    def getOnlineData(self):
        return ",".join([self.username, self.steam_id, str(self.money)])
