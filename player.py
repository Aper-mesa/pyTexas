# player.py
import os
import config
import tools


class Player:
    """
    玩家档案（切换到 Steam 身份体系，不再需要账号/密码/IP）。
    以 steam_id 作为唯一主键，persona_name 作为显示名。
    """

    def __init__(self, steam_id, persona_name, money=config.INIT_MONEY):
        self.steam_id = str(steam_id)
        self.persona_name = persona_name
        self.money = money

    # 兼容旧代码：persona_name 暴露为 username（只读别名）
    @property
    def username(self):
        return self.persona_name

    def __str__(self):
        return self.persona_name

    # --------- 持久化 ---------
    def _data_path(self):
        # 用 steam_id 的哈希作为文件名，避免过长或非法字符
        sid_hash = tools.nameToHash(self.steam_id)
        return os.path.join(config.USER_DATA_PATH, sid_hash + ".json")

    def storeData(self):
        """保存玩家数据"""
        tools.createPathIfNotExist(config.USER_DATA_PATH)
        data = {
            "steam_id": self.steam_id,
            "persona_name": self.persona_name,
            "money": self.money,
        }
        tools.setJsonData(self._data_path(), data)

    @classmethod
    def create_from_steam(cls, steam_id, persona_name):
        """
        以 Steam 身份创建/载入玩家：
          - 如无存档：新建并返回
          - 如有存档：读取历史 money，并在昵称变更时同步 persona_name
        """
        steam_id = str(steam_id)
        sid_hash = tools.nameToHash(steam_id)
        path = os.path.join(config.USER_DATA_PATH, sid_hash + ".json")

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

    # 用于大厅广播/调试：保持“三段式”，但第2段改为 steam_id（过去是 IP）
    # 旧："username,ip,money" -> 新："persona_name,steam_id,money"
    def getOnlineData(self):
        return ",".join([self.persona_name, self.steam_id, str(self.money)])

    def getJSONData(self):
        return tools.getJsonData(self._data_path())


class PlayerInGame:
    """
    对局内轻量对象；不再包含 IP。
    """
    def __init__(self, persona_name, money, steam_id=None):
        self.persona_name = persona_name
        self.username = persona_name  # 兼容旧字段名
        self.steam_id = str(steam_id) if steam_id is not None else None

        self.money = money
        self.handCards = []
