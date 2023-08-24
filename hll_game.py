import subprocess, time
from steam import game_servers as gs

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


def launch():
    if not is_running():
        subprocess.run(f"cmd /c start steam://run/{hll_steam_id}")


def join_server(server_ip, query_port):
    subprocess.run(f"cmd /c start steam://connect/{server_ip}:{query_port}")


def join_server_addr(server_addr):
    if len(server_addr) != 2:
        return
    join_server(server_addr[0], server_addr[1])


# Checks for game running and EAC splash popup to go away and 15 sec extra
def wait_until_running():
    # start = time.time()
    while True:
        if __process_exists(launch_exe) or not is_fully_running():
            time.sleep(1)
        else:
            break
    # print(f"Running - {time.time() - start}s")
    time.sleep(15)
    # print(f"Running (+15s) - {time.time() - start}s")


# Checks for multiple processes to quit and 15 sec extra
def wait_until_dead():
    # start = time.time()
    while True:
        if (is_running() or __process_exists(bugreport_exe)
                or __process_exists(overlay_exe) or __process_exists(crash_window_exe)):
            time.sleep(1)
        else:
            break
    # print(f"Dead - {time.time() - start}s")
    time.sleep(15)
    # print(f"Dead (+15s) - {time.time() - start}s")


def is_player_present(server_addr, player_name, timeout=3):
    try:
        players = gs.a2s_players(server_addr, timeout=timeout)

        names = []
        for player in players:
            names.append(player["name"])

        return player_name.lower() in (string.lower() for string in names)
    except:
        return None


def launch_and_wait():
    launch()
    wait_until_running()


def relaunch_and_wait():
    kill()
    kill_crash_window()
    wait_until_dead()
    launch_and_wait()
