# minimal_steam_flat.py
import ctypes
import os
import time
from ctypes import c_bool, c_void_p, c_char_p, c_uint32, c_int32
from pathlib import Path

APP_ID = 480  # Spacewar 测试

here = Path(__file__).resolve().parent
os.add_dll_directory(str(here))                      # Py3.8+ 必需
lib = ctypes.WinDLL(str(here / "steam_api64.dll"))   # 同目录加载

# ---- 仅解析必需符号 ----
SteamAPI_Init         = lib.SteamAPI_InitSafe;  SteamAPI_Init.restype = c_bool
SteamAPI_RunCallbacks = lib.SteamAPI_RunCallbacks;   SteamAPI_RunCallbacks.restype = None
SteamAPI_Shutdown     = lib.SteamAPI_Shutdown;       SteamAPI_Shutdown.restype = None

SteamInternal_CreateInterface = lib.SteamInternal_CreateInterface
SteamInternal_CreateInterface.restype = c_void_p
SteamInternal_CreateInterface.argtypes = [c_char_p]

SteamAPI_GetHSteamUser = lib.SteamAPI_GetHSteamUser; SteamAPI_GetHSteamUser.restype = c_int32
SteamAPI_GetHSteamPipe = lib.SteamAPI_GetHSteamPipe; SteamAPI_GetHSteamPipe.restype = c_int32

GetISteamFriends = lib.SteamAPI_ISteamClient_GetISteamFriends
GetISteamFriends.restype = c_void_p
GetISteamFriends.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

GetISteamUtils = lib.SteamAPI_ISteamClient_GetISteamUtils
GetISteamUtils.restype = c_void_p
GetISteamUtils.argtypes = [c_void_p, c_int32, c_char_p]

ISteamFriends_GetPersonaName = lib.SteamAPI_ISteamFriends_GetPersonaName
ISteamFriends_GetPersonaName.restype = c_char_p
ISteamFriends_GetPersonaName.argtypes = [c_void_p]

ISteamUtils_GetAppID = lib.SteamAPI_ISteamUtils_GetAppID
ISteamUtils_GetAppID.restype = c_uint32
ISteamUtils_GetAppID.argtypes = [c_void_p]

# ---- 可选：若没有 steam_appid.txt 就创建（方便直接跑）----
appid_txt = here / "steam_appid.txt"
if not appid_txt.exists():
    appid_txt.write_text(str(APP_ID), encoding="utf-8")

def main():
    if not SteamAPI_Init():
        print("Init 失败：请确认 steam_appid.txt=480、steam_api64.dll 同目录且 Steam 客户端已登录")
        return

    try:
        # 1) 取 ISteamClient（你的 1.62 实测为 SteamClient023）
        client = SteamInternal_CreateInterface(b"SteamClient023")
        if not client:
            print("获取 ISteamClient 失败"); return

        # 2) 句柄
        huser, hpipe = SteamAPI_GetHSteamUser(), SteamAPI_GetHSteamPipe()

        # 3) 通过版本字符串获取 Friends/Utils（你的环境实测这两个可用）
        friends = GetISteamFriends(client, huser, hpipe, b"SteamFriends017")
        utils   = GetISteamUtils(client, hpipe, b"SteamUtils010")
        if not friends or not utils:
            print("获取 Friends/Utils 失败"); return

        # 4) 跑几个回调（实际项目放进 Pygame 主循环每帧一次）
        for _ in range(6):
            SteamAPI_RunCallbacks()
            time.sleep(0.01)

        # 5) 打印昵称 & AppID
        name = ISteamFriends_GetPersonaName(friends).decode("utf-8", "ignore")
        appid = ISteamUtils_GetAppID(utils)
        print("[PersonaName]", name)
        print("[AppID]", appid)

    finally:
        SteamAPI_Shutdown()

if __name__ == "__main__":
    main()
