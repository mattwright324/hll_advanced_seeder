import subprocess, time
from steam import game_servers as gs
import win32gui, win32process

# steam processes
steam_exe = 'steam.exe'
steam_web_exe = 'steamwebhelper.exe'

# The EAC splash popup before the game is ready
launch_exe = 'HLL_Launch.exe'
# The game itself
hll_exe = 'HLL-Win64-Shipping.exe'
# Last couple processes running after game exit
bugreport_exe = 'HLL_BugReportUploader.exe'
overlay_exe = 'GameOverlayUI.exe'
crash_window_exe = 'CrashReportClient.exe'
# Game steam id for steam:// protocol calls
hll_steam_id = '686810'


def __process_exists(process_name):
    return process_name in str(subprocess.check_output('tasklist'))


def __process_kill(process_name):
    subprocess.run(f'taskkill /IM "{process_name}" /F', stdout=subprocess.DEVNULL)

def is_steam_fully_running():
    return __process_exists(steam_exe) and __process_exists(steam_web_exe)


def launch_steam():
    if not is_steam_fully_running():
        subprocess.run(f"cmd /c start steam://nav/games/details/{hll_steam_id}")


def wait_until_steam_running(wait=25):
    # start = time.time()
    while True:
        if not is_steam_fully_running():
            time.sleep(1)
        else:
            break
    # print(f"Running - {time.time() - start}s")
    time.sleep(wait)
    # print(f"Running (+{wait}s) - {time.time() - start}s")


def steam_launch_and_wait(wait=25):
    launch_steam()
    wait_until_steam_running(wait)


def did_game_crash():
    return not is_running() and __process_exists(crash_window_exe)


def is_running():
    return __process_exists(hll_exe)


def is_fully_running():
    return (is_running() and __process_exists(bugreport_exe)
            and __process_exists(overlay_exe) and __process_exists(crash_window_exe))


def is_fully_dead():
    return not (is_running() or __process_exists(bugreport_exe)
                or __process_exists(overlay_exe) or __process_exists(crash_window_exe))


def kill():
    if is_running():
        __process_kill(hll_exe)


def kill_crash_window():
    if __process_exists(crash_window_exe):
        __process_kill(crash_window_exe)


def kill_all():
    for process_name in [hll_exe, crash_window_exe, bugreport_exe, overlay_exe]:
        if __process_exists(process_name):
            __process_kill(process_name)

import os
def launch(options=''):
    if not is_running():
        os.system(f"start \"\" \"steam://run/{hll_steam_id}//{options}/\"")
        # subprocess.run(f"cmd /c start ")


def join_server(server_ip, query_port):
    subprocess.run(f"cmd /c start steam://connect/{server_ip}:{query_port}")


def join_server_addr(server_addr):
    if len(server_addr) != 2:
        return
    join_server(server_addr[0], server_addr[1])


# Checks for game running and EAC splash popup to go away and 15 sec extra
def wait_until_running(wait=25):
    # start = time.time()
    while True:
        if __process_exists(launch_exe) or not is_fully_running():
            time.sleep(1)
        else:
            break
    # print(f"Running - {time.time() - start}s")
    time.sleep(wait)
    # print(f"Running (+{wait}s) - {time.time() - start}s")


# Checks for multiple processes to quit and 15 sec extra
def wait_until_dead(wait=25):
    # start = time.time()
    while True:
        if (is_running() or __process_exists(bugreport_exe)
                or __process_exists(overlay_exe) or __process_exists(crash_window_exe)):
            time.sleep(1)
        else:
            break
    # print(f"Dead - {time.time() - start}s")
    time.sleep(wait)
    # print(f"Running (+{wait}s) - {time.time() - start}s")


def is_player_present(server_addr, player_name, timeout=3):
    try:
        players = gs.a2s_players(server_addr, timeout=timeout)

        names = []
        for player in players:
            names.append(player["name"])

        return player_name.lower() in (string.lower() for string in names)
    except:
        return None


def launch_and_wait(wait=25):
    launch()
    wait_until_running(wait)


def relaunch_and_wait(wait=25):
    kill()
    kill_crash_window()
    wait_until_dead(wait)
    launch_and_wait(wait)

import psutil
import pygetwindow as gw

def list_open_windows():
    windows = gw.getAllTitles()  # Get all window titles
    windows_info = []

    for process in psutil.process_iter(['pid', 'name']):
        try:
            for title in windows:
                if title:
                    # Check if the process has a window title associated with it
                    if process.info['name'] in title:
                        windows_info.append((title, process.info['pid'], process.info['name']))
        except psutil.Error:
            continue

    return windows_info

# result = list_open_windows()
# for title, pid, name in result:
#     print(f"Window: {title} | PID: {pid} | Process Name: {name}")
#
# subprocess.run(f"cmd /c start steam://open/servers")

import time
import clipboard
import pyautogui
import win32gui
from win32gui import GetWindowRect, GetForegroundWindow
import win32con
from python_imagesearch.imagesearch import imagesearch

def find(image):
    pos = imagesearch(image)
    if pos[0] != -1:
        print('found', image, pos)
        return True
    else:
        return False

def find_and_move(image):
    pos = imagesearch(image)
    if pos[0] != -1:
        print('found', image, pos)
        pyautogui.moveTo(pos[0] + 5, pos[1] + 5)
        return True
    else:
        return False


def join_server_complex(server_name):
    print('join_server_complex', server_name)
    # Click Enlist once it appears
    while True:
        time.sleep(1)

        if find_and_move('enlist_lg.png'):
            pyautogui.click()
            break

    # Wait for server list to populate
    time.sleep(3)
    while True:
        time.sleep(1)

        if find('servers_found.png'):
            find_and_move('filter.png')
            pyautogui.click()
            break

    while True:
        time.sleep(1)

        pos = imagesearch('filter_confirm.png')
        if pos[0] != -1:
            pyautogui.moveTo(pos[0] + 25, pos[1] - 30) # server name filter relative to confirm button
            pyautogui.click()
            time.sleep(1)

            clipboard.copy(server_name)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)

            pyautogui.moveTo(pos[0] + 25, pos[1] + 25)
            pyautogui.click()
            break

    while True:
        time.sleep(1)

        if find_and_move('server_100.png'):
            pyautogui.click()
            find_and_move('join_server.png')
            pyautogui.click()
            break

def to_main_menu_complex():
    print('to_main_menu_complex')
    while True:
        if find_and_move('leave_server.png'):
            pyautogui.click()
            time.sleep(1)
        if find_and_move('exit.png'):
            pyautogui.click()
            time.sleep(1)
        if find_and_move('leave_yes.png'):
            pyautogui.click()
            time.sleep(1)
        if find_and_move('back.png'):
            pyautogui.click()
            time.sleep(1)

        print('.')
        time.sleep(1)
        if find('enlist_lg.png'):
            break

import ctypes

launch('+connect 46.105.223.204:7788')
wait_until_running(5)
print('running')
time.sleep(3)


# while True:
#     print('center click')
#     center_res = ctypes.windll.user32.GetSystemMetrics(0) / 2, ctypes.windll.user32.GetSystemMetrics(1) / 2
#     pyautogui.moveTo(center_res)
#     pyautogui.click()
#     time.sleep(3)


# pyautogui.moveTo(100, 100)

# to_main_menu_complex()
# time.sleep(2)
# join_server_complex("HLL Official - US West #45")

# def maximize_window_by_title(title):
#     hwnd = win32gui.FindWindow(None, title)
#     if hwnd:
#         win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
#     else:
#         print(f"Window with title '{title}' not found.")
#
# def minimize_window_by_title(title):
#     hwnd = win32gui.FindWindow(None, title)
#     if hwnd:
#         win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
#     else:
#         print(f"Window with title '{title}' not found.")
#
# # Example usage
# maximize_window_by_title("Game Servers")  # Replace with the actual window title

