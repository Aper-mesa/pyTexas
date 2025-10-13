# -*- coding: utf-8 -*-

import ctypes
import pickle
from ctypes import c_void_p, c_uint64, c_int32, c_uint32, c_char_p, POINTER, Structure


# ======== Steam Networking 结构体 ========
class SteamNetworkingIdentity(Structure):
    """Steam 网络身份标识"""
    _fields_ = [
        ("m_eType", c_int32),
        ("m_cbSize", c_int32),
        ("m_steamID64", c_uint64),
        ("m_szUnknownRawString", ctypes.c_char * 128),
    ]

    @classmethod
    def from_steam_id(cls, steam_id: int):
        """从 Steam ID 创建网络身份"""
        identity = cls()
        identity.m_eType = 16  # k_ESteamNetworkingIdentityType_SteamID
        identity.m_steamID64 = steam_id
        return identity


class SteamNetworkingMessage_t(Structure):
    """Steam 网络消息结构"""
    _fields_ = [
        ("m_pData", c_void_p),
        ("m_cbSize", c_int32),
        ("m_conn", c_uint32),
        ("m_identityPeer", SteamNetworkingIdentity),
        ("m_nConnUserData", c_int32),
        ("m_usecTimeReceived", ctypes.c_int64),
        ("m_nMessageNumber", ctypes.c_int64),
        ("m_pfnFreeData", c_void_p),
        ("m_pfnRelease", c_void_p),
        ("m_nChannel", c_int32),
        ("m_nFlags", c_int32),
        ("m_nUserData", ctypes.c_int64),
    ]


# ======== 全局函数指针（延迟绑定）========
ISteamNetworkingMessages_SendMessageToUser = None
ISteamNetworkingMessages_ReceiveMessagesOnChannel = None
ISteamNetworkingMessages_AcceptSessionWithUser = None
SteamNetworkingMessage_Release = None

_initialized = False
_networking_messages_handle = None


def _bind_networking_functions(DLL, client_handle):
    """绑定 Steam 网络消息相关函数"""
    global ISteamNetworkingMessages_SendMessageToUser
    global ISteamNetworkingMessages_ReceiveMessagesOnChannel
    global ISteamNetworkingMessages_AcceptSessionWithUser
    global SteamNetworkingMessage_Release
    global _networking_messages_handle
    global _initialized

    if _initialized:
        return True

    try:
        # 获取 ISteamNetworkingMessages 接口
        fn = DLL.SteamAPI_ISteamClient_GetISteamNetworkingMessages
        fn.restype = c_void_p
        fn.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

        # HSteamUser 和 HSteamPipe 通常是 0 和 0 或从 GetHSteamUser/GetHSteamPipe 获取
        # 这里简化处理，使用 SteamAPI_GetHSteamUser 和 SteamAPI_GetHSteamPipe
        get_user_fn = DLL.SteamAPI_GetHSteamUser
        get_user_fn.restype = c_int32
        get_user_fn.argtypes = []
        h_user = get_user_fn()

        get_pipe_fn = DLL.SteamAPI_GetHSteamPipe
        get_pipe_fn.restype = c_int32
        get_pipe_fn.argtypes = []
        h_pipe = get_pipe_fn()

        _networking_messages_handle = fn(
            client_handle,
            h_user,
            h_pipe,
            b"SteamNetworkingMessages002"
        )

        if not _networking_messages_handle:
            print("[SteamTools] 无法获取 ISteamNetworkingMessages 接口")
            return False

        # SendMessageToUser
        fn = DLL.SteamAPI_ISteamNetworkingMessages_SendMessageToUser
        fn.restype = c_int32  # EResult
        fn.argtypes = [
            c_void_p,  # handle
            POINTER(SteamNetworkingIdentity),  # identityRemote
            c_void_p,  # pubData
            c_uint32,  # cubData
            c_int32,  # nSendFlags
            c_int32  # nRemoteChannel
        ]
        ISteamNetworkingMessages_SendMessageToUser = fn

        # ReceiveMessagesOnChannel
        fn = DLL.SteamAPI_ISteamNetworkingMessages_ReceiveMessagesOnChannel
        fn.restype = c_int32  # 返回收到的消息数量
        fn.argtypes = [
            c_void_p,  # handle
            c_int32,  # nLocalChannel
            POINTER(POINTER(SteamNetworkingMessage_t)),  # ppOutMessages
            c_int32  # nMaxMessages
        ]
        ISteamNetworkingMessages_ReceiveMessagesOnChannel = fn

        # AcceptSessionWithUser
        fn = DLL.SteamAPI_ISteamNetworkingMessages_AcceptSessionWithUser
        fn.restype = c_int32
        fn.argtypes = [c_void_p, POINTER(SteamNetworkingIdentity)]
        ISteamNetworkingMessages_AcceptSessionWithUser = fn

        # Release message
        # 注意：这个函数在消息结构体内，需要通过虚函数表调用
        # 简化起见，我们直接使用 SteamAPI 提供的释放函数
        fn = DLL.SteamAPI_SteamNetworkingMessage_t_Release
        fn.restype = None
        fn.argtypes = [POINTER(SteamNetworkingMessage_t)]
        SteamNetworkingMessage_Release = fn

        _initialized = True
        print("[SteamTools] Steam 网络消息接口初始化成功")
        return True

    except Exception as e:
        print(f"[SteamTools] 初始化失败: {e}")
        return False


# ======== 高级封装：简化的发送/接收接口 ========

class SteamNetworkMessenger:
    """Steam 网络消息收发器 - 简化复杂对象传输"""

    # 消息通道定义
    CHANNEL_ROOM_DATA = 0  # Room 对象传输
    CHANNEL_GAME_STATE = 1  # 游戏状态更新
    CHANNEL_PLAYER_ACTION = 2  # 玩家操作
    CHANNEL_CHAT = 3  # 聊天消息

    # 发送标志
    k_nSteamNetworkingSend_Reliable = 8  # 可靠传输
    k_nSteamNetworkingSend_NoNagle = 1  # 立即发送
    k_nSteamNetworkingSend_UnreliableNoDelay = 0  # 不可靠但快速

    def __init__(self, steam_dll, client_handle):
        """
        初始化消息收发器

        Args:
            steam_dll: Steam DLL 对象
            client_handle: Steam Client 句柄
        """
        self.initialized = _bind_networking_functions(steam_dll, client_handle)
        if not self.initialized:
            raise RuntimeError("Steam 网络消息接口初始化失败")

        self._message_handlers = {}  # 消息处理器

    def send_object(self, target_steam_id: int, obj, channel: int = 0, reliable: bool = True):
        """
        发送 Python 对象到指定玩家

        Args:
            target_steam_id: 目标玩家的 Steam ID
            obj: 要发送的 Python 对象（必须可 pickle）
            channel: 消息通道（0-255）
            reliable: 是否使用可靠传输

        Returns:
            bool: 发送是否成功
        """
        try:
            # 序列化对象
            data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

            # 创建目标身份
            identity = SteamNetworkingIdentity.from_steam_id(target_steam_id)

            # 选择发送标志
            if reliable:
                flags = self.k_nSteamNetworkingSend_Reliable | self.k_nSteamNetworkingSend_NoNagle
            else:
                flags = self.k_nSteamNetworkingSend_UnreliableNoDelay

            # 发送消息
            result = ISteamNetworkingMessages_SendMessageToUser(
                _networking_messages_handle,
                ctypes.byref(identity),
                data,
                len(data),
                flags,
                channel
            )

            # EResult: 1 = k_EResultOK
            if result == 1:
                print(f"[SteamTools] 成功发送 {len(data)} 字节到 {target_steam_id} (channel {channel})")
                return True
            else:
                print(f"[SteamTools] 发送失败，EResult={result}")
                return False

        except Exception as e:
            print(f"[SteamTools] 发送对象时出错: {e}")
            return False

    def receive_objects(self, channel: int = 0, max_messages: int = 32):
        """
        从指定通道接收消息

        Args:
            channel: 消息通道
            max_messages: 最多接收的消息数

        Returns:
            list: [(sender_steam_id, obj), ...] 发送者ID和对象的列表
        """
        try:
            # 准备消息数组
            messages_array_type = POINTER(SteamNetworkingMessage_t) * max_messages
            messages = messages_array_type()

            # 接收消息
            count = ISteamNetworkingMessages_ReceiveMessagesOnChannel(
                _networking_messages_handle,
                channel,
                ctypes.cast(messages, POINTER(POINTER(SteamNetworkingMessage_t))),
                max_messages
            )

            if count <= 0:
                return []

            results = []
            for i in range(count):
                msg = messages[i].contents

                # 提取发送者 Steam ID
                sender_id = msg.m_identityPeer.m_steamID64

                # 提取数据
                data_size = msg.m_cbSize
                data_ptr = msg.m_pData
                data_bytes = ctypes.string_at(data_ptr, data_size)

                # 反序列化对象
                try:
                    obj = pickle.loads(data_bytes)
                    results.append((sender_id, obj))
                    print(f"[SteamTools] 从 {sender_id} 接收到对象 (channel {channel})")
                except Exception as e:
                    print(f"[SteamTools] 反序列化失败: {e}")

                # 释放消息
                SteamNetworkingMessage_Release(messages[i])

            return results

        except Exception as e:
            print(f"[SteamTools] 接收对象时出错: {e}")
            return []

    def broadcast_to_lobby(self, lobby_members, obj, channel: int = 0, reliable: bool = True):
        """
        向大厅所有成员广播对象

        Args:
            lobby_members: 成员 Steam ID 列表
            obj: 要广播的对象
            channel: 消息通道
            reliable: 是否可靠传输

        Returns:
            int: 成功发送的数量
        """
        success_count = 0
        for member_id in lobby_members:
            if self.send_object(member_id, obj, channel, reliable):
                success_count += 1
        return success_count

    def register_handler(self, channel: int, handler_func):
        """
        注册消息处理器（自动处理接收到的消息）

        Args:
            channel: 消息通道
            handler_func: 处理函数 func(sender_steam_id, obj)
        """
        self._message_handlers[channel] = handler_func

    def process_messages(self):
        """
        处理所有已注册通道的消息（在主循环中调用）
        """
        for channel, handler in self._message_handlers.items():
            messages = self.receive_objects(channel)
            for sender_id, obj in messages:
                try:
                    handler(sender_id, obj)
                except Exception as e:
                    print(f"[SteamTools] 处理消息时出错: {e}")


# ======== 便捷函数 ========

def create_messenger(steam_bootstrap_module):
    """
    从 steam_bootstrap 模块创建消息收发器

    Args:
        steam_bootstrap_module: 已初始化的 steam_bootstrap 模块

    Returns:
        SteamNetworkMessenger 实例
    """
    if not hasattr(steam_bootstrap_module, 'DLL') or steam_bootstrap_module.DLL is None:
        raise RuntimeError("Steam 未初始化，请先调用 steam_bootstrap.init()")

    if not hasattr(steam_bootstrap_module, 'CLIENT') or steam_bootstrap_module.CLIENT is None:
        raise RuntimeError("Steam Client 句柄未找到")

    return SteamNetworkMessenger(
        steam_bootstrap_module.DLL,
        steam_bootstrap_module.CLIENT
    )


# ======== 使用示例 ========
"""
# 在 Lobby.py 或 main.py 中使用：

import steam_bootstrap as steam
import tools

# 初始化（在 steam.init() 之后）
messenger = tools.create_messenger(steam)

# 房主：创建 Room 并广播
room = Room([players, minBet, initBet])
member_ids = [member.steam_id for member in lobby_members]
messenger.broadcast_to_lobby(member_ids, room, channel=tools.SteamNetworkMessenger.CHANNEL_ROOM_DATA)

# 非房主：接收 Room
def on_room_received(sender_id, room_obj):
    print(f"收到来自 {sender_id} 的 Room 对象")
    # 启动游戏
    start_game(room_obj)

messenger.register_handler(tools.SteamNetworkMessenger.CHANNEL_ROOM_DATA, on_room_received)

# 主循环中
while running:
    steam.run_callbacks()
    messenger.process_messages()  # 处理网络消息
    # ... 其他逻辑
"""