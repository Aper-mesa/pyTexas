# steam_bootstrap.py —— 单例式 Steam 引导
import atexit, ctypes
from ctypes import c_bool, c_void_p, c_char_p, c_int32
from pathlib import Path

# ---- 全局对象 / 状态 ----
DLL = None  # 延迟到 init() 再加载

# 函数指针占位（延迟绑定）
SteamAPI_Init = None
SteamAPI_Shutdown = None
SteamAPI_RunCallbacks = None
SteamInternal_CreateInterface = None
SteamAPI_GetHSteamUser = None
SteamAPI_GetHSteamPipe = None
GetISteamUser = None
GetISteamFriends = None
GetISteamMatchmaking = None
GetISteamApps = None
GetISteamUtils = None

_initialized = False
_handles = None  # (user, friends, mm, apps, utils)
_client = None
_hUser = None
_hPipe = None


# ---- 内部：加载 DLL ----
def _load_dll():
    global DLL
    if DLL is not None:
        return
    here = Path(__file__).resolve().parent
    candidates = [
        here / "steam_api64.dll",  # 推荐放同目录
        Path.cwd() / "steam_api64.dll",  # 当前工作目录（你在 main 里 chdir 过）
    ]
    last_err = None
    for p in candidates:
        try:
            if p.exists():
                DLL = ctypes.WinDLL(str(p))
                return
        except Exception as e:
            last_err = e
    raise FileNotFoundError(
        f"找不到 steam_api64.dll; 尝试路径: {', '.join(str(p) for p in candidates)}; last_err={last_err}"
    )


# ---- 内部：绑定符号（在 DLL 加载后调用）----

def _bind_symbols():
    global SteamAPI_Init, SteamAPI_Shutdown, SteamAPI_RunCallbacks, SteamInternal_CreateInterface, SteamAPI_GetHSteamUser, SteamAPI_GetHSteamPipe, GetISteamUser, GetISteamFriends, GetISteamMatchmaking, GetISteamApps, GetISteamUtils

    # Core
    SteamAPI_Init = getattr(DLL, "SteamAPI_InitSafe", None)
    if SteamAPI_Init is None:
        SteamAPI_Init = DLL.SteamAPI_Init
    SteamAPI_Init.restype = c_bool

    SteamAPI_Shutdown = DLL.SteamAPI_Shutdown
    SteamAPI_RunCallbacks = DLL.SteamAPI_RunCallbacks

    SteamInternal_CreateInterface = DLL.SteamInternal_CreateInterface
    SteamInternal_CreateInterface.restype = c_void_p
    SteamInternal_CreateInterface.argtypes = [c_char_p]

    SteamAPI_GetHSteamUser = DLL.SteamAPI_GetHSteamUser
    SteamAPI_GetHSteamUser.restype = c_int32
    SteamAPI_GetHSteamPipe = DLL.SteamAPI_GetHSteamPipe
    SteamAPI_GetHSteamPipe.restype = c_int32

    # Sub-interfaces
    GetISteamUser = DLL.SteamAPI_ISteamClient_GetISteamUser
    GetISteamUser.restype = c_void_p
    GetISteamUser.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

    GetISteamFriends = DLL.SteamAPI_ISteamClient_GetISteamFriends
    GetISteamFriends.restype = c_void_p
    GetISteamFriends.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

    GetISteamMatchmaking = DLL.SteamAPI_ISteamClient_GetISteamMatchmaking
    GetISteamMatchmaking.restype = c_void_p
    GetISteamMatchmaking.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

    GetISteamApps = DLL.SteamAPI_ISteamClient_GetISteamApps
    GetISteamApps.restype = c_void_p
    GetISteamApps.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

    GetISteamUtils = DLL.SteamAPI_ISteamClient_GetISteamUtils
    GetISteamUtils.restype = c_void_p
    GetISteamUtils.argtypes = [c_void_p, c_int32, c_char_p]


# ---- 对外：初始化 / 句柄 / 回调 / 关闭 ----
def init():
    """进程全局只初始化一次。建议在创建窗口(set_mode)之前调用以确保 Overlay 注入。"""
    global _initialized, _handles, _client, _hUser, _hPipe
    if _initialized:
        return

    _load_dll()
    _bind_symbols()

    ok = SteamAPI_Init()
    if not ok:
        raise RuntimeError("SteamAPI_Init() 失败：请确认 Steam 客户端已登录、steam_appid.txt 存在且权限一致。")

    _client = c_void_p(SteamInternal_CreateInterface(b"SteamClient023"))
    _hUser = SteamAPI_GetHSteamUser()
    _hPipe = SteamAPI_GetHSteamPipe()

    user = c_void_p(GetISteamUser(_client, _hUser, _hPipe, b"SteamUser023"))
    friends = c_void_p(GetISteamFriends(_client, _hUser, _hPipe, b"SteamFriends018"))
    mm = c_void_p(GetISteamMatchmaking(_client, _hUser, _hPipe, b"SteamMatchMaking009"))
    apps = c_void_p(GetISteamApps(_client, _hUser, _hPipe, b"STEAMAPPS_INTERFACE_VERSION008"))
    utils = c_void_p(GetISteamUtils(_client, _hPipe, b"SteamUtils010"))

    if not (user.value and friends.value and mm.value and apps.value and utils.value):
        raise RuntimeError(
            f"Steam 接口获取失败: user={user.value} friends={friends.value} "
            f"mm={mm.value} apps={apps.value} utils={utils.value}"
        )

    _handles = (user, friends, mm, apps, utils)
    _initialized = True


def get_handles():
    """返回 (user, friends, mm, apps, utils)。在 main.py 调用 init() 之后使用。"""
    if not _initialized:
        raise RuntimeError("Steam 未初始化。先调用 steam_bootstrap.init()")
    return _handles


def run_callbacks():
    """每帧调用一次"""
    if _initialized and SteamAPI_RunCallbacks:
        SteamAPI_RunCallbacks()


def shutdown():
    """进程退出时调用一次（有 atexit 兜底）"""
    global _initialized, _handles, _client
    if _initialized and SteamAPI_Shutdown:
        SteamAPI_Shutdown()
    _initialized = False
    _handles = None
    _client = None


atexit.register(shutdown)
