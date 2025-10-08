import os
import config
import tools


class Player:
    def __init__(self, steam_id, persona_name, money=config.INIT_MONEY):
        self.steam_id = str(steam_id)
        self.persona_name = persona_name
        self.money = money

    @property
    def username(self):
        return self.persona_name

    def storeData(self):
        tools.createPathIfNotExist(config.USER_DATA_PATH)
        data = {
            "steam_id": self.steam_id,
            "persona_name": self.persona_name,
            "money": self.money,
        }
        tools.setJsonData(os.path.join(config.USER_DATA_PATH, self.steam_id + ".json"), data)

    @classmethod
    def create(cls, steam_id, persona_name):
        steam_id = str(steam_id)
        path = os.path.join(config.USER_DATA_PATH, steam_id + ".json")

        if not os.path.exists(path):
            p = cls(steam_id=steam_id, persona_name=persona_name)
            p.storeData()
            return p

        data = tools.getJsonData(path) or {}
        saved_money = data.get("money", config.INIT_MONEY)
        saved_persona = data.get("persona_name", persona_name)

        p = cls(steam_id=steam_id, persona_name=saved_persona, money=saved_money)

        if p.persona_name != persona_name:
            p.persona_name = persona_name
            p.storeData()

        return p

    def getOnlineData(self):
        return ",".join([self.persona_name, self.steam_id, str(self.money)])

class PlayerInGame:
    def __init__(self, persona_name, money, steam_id=None):
        self.persona_name = persona_name
        self.steam_id = str(steam_id) if steam_id is not None else None

        self.money = money
        self.handCards = []
