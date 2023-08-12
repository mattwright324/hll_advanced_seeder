# required
import sys, yaml, time, traceback, random
from datetime import datetime as dt, timedelta
from steam import game_servers as gs
# project required
import colors as c, hll_game, stopwatches as sw

# Don't launch the game, join servers, or check their player lists
# Otherwise, operates as if it did those things for testing
debug_no_game = False
# Print extra logs in a few places
debug_extra_logs = False


def debug(log):
    if debug_extra_logs:
        print(f'{c.darkgrey}DEBUG : {log}{c.reset}')


def try_parsing_time(possible_date, field):
    for fmt in ('%I:%M %p', '%I:%M%p'):
        try:
            return dt.strptime(possible_date, fmt)
        except ValueError:
            pass
    raise ValueError(f"Non-valid date format for field {field}: '{possible_date}'")


def split_whitespace(string):
    keywords = []

    for split in string.split(' '):
        split = split.strip()
        if split and split not in keywords:
            keywords.append(split)

    return keywords


print(f'{c.yellow}   ###############################   {c.reset}')
print(f'{c.yellow}   ###   HLL Advanced Seeder   ###   {c.reset}')
print(f'{c.yellow}   ###############################   {c.reset}')
print()

debug('Loading YAML')
with open('seeding_new.yaml', 'r') as file:
    seeding_yaml = yaml.safe_load(file)
debug(f'{c.darkgrey}{seeding_yaml}{c.reset}\n')

seeding_method = str(seeding_yaml["seeding_method"]).lower()
seeding_endtime = try_parsing_time(seeding_yaml["seeding_endtime"], "seeding_endtime")
seeding_minutes = int(seeding_yaml["seeding_minutes"])
priority_monitor = bool(seeding_yaml["priority_monitor"])
priority_monitor_endtime = try_parsing_time(seeding_yaml["priority_monitor_endtime"], "priority_monitor_endtime")
servers = list(seeding_yaml["priority_servers"])
seeded_player_limit = int(seeding_yaml["seeded_player_limit"])
seeded_player_variability = int(seeding_yaml["seeded_player_variability"])
server_query_rate = int(seeding_yaml["server_query_rate"])
server_query_timeout = int(seeding_yaml["server_query_timeout"])
query_timeout_limit = int(seeding_yaml["query_timeout_limit"])
check_idle_kick = bool(seeding_yaml["check_idle_kick"])
player_name = seeding_yaml["player_name"]
perpetual_mode = bool(seeding_yaml["perpetual_mode"])
perpetual_max_servers = int(seeding_yaml["perpetual_max_servers"])
perpetual_min_players = int(seeding_yaml["perpetual_min_players"])
ignore_name_contains = list(seeding_yaml["ignore_name_contains"])

start_datetime = dt.today()
stop_datetime = start_datetime
if seeding_method == "endtime":
    stop_datetime = start_datetime.replace(hour=seeding_endtime.hour, minute=seeding_endtime.minute, second=0,
                                           microsecond=0)
    if stop_datetime < start_datetime:
        stop_datetime += timedelta(days=1)
elif seeding_method == "minutes":
    stop_datetime += timedelta(minutes=seeding_minutes)
else:
    print(f'{c.red}Invalid seeding_method. Check yaml and try again.{c.reset}')
    input("Press enter to exit")
    sys.exit()

plan_runtime = (stop_datetime - start_datetime).total_seconds()
plan_runtime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(plan_runtime))

stop_priority_datetime = start_datetime.replace(hour=seeding_endtime.hour, minute=seeding_endtime.minute, second=0,
                                           microsecond=0)
if stop_priority_datetime < start_datetime:
    stop_priority_datetime += timedelta(days=1)

plan_prioritytime = (stop_priority_datetime - start_datetime).total_seconds()
plan_prioritytime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(plan_prioritytime))

print(f'{c.yellow}Summary{c.reset}')
print(f'Run method        : {c.lightblue}{seeding_method}{c.reset} or when done')
print(f'Start time        : {c.lightblue}{start_datetime}{c.reset}')
print(f'Plan end time     : {c.lightblue}{stop_datetime}{c.reset} or {c.darkgrey}{plan_runtime_str} from start{c.reset}')
print(f'Perpetual mode    : {c.green if perpetual_mode else c.darkgrey}{perpetual_mode}{c.reset}')
print(f'Priority monitor  : {c.green if priority_monitor else c.darkgrey}{priority_monitor}{c.reset}')
if priority_monitor:
    print(f'Priority end time : {c.lightblue}{stop_priority_datetime}{c.reset} or {c.darkgrey}{plan_prioritytime_str} from start{c.reset}')
print(f'Servers listed    : {c.lightblue}{len(servers)}{c.reset}')
print()

do_steam_search = perpetual_mode
for server in servers:
    if "steam_search" in server.keys():
        do_steam_search = True
        break

steam_servers = {}
if do_steam_search:
    print(f'{c.yellow}Searching steam server list{c.reset}')
    for server_addr in gs.query_master(r'\appid\686810', max_servers=1000):
        value = f'{c.lightgrey}{len(steam_servers)} servers{c.reset}'
        print("\r{0}".format(value), end='')
        try:
            info = gs.a2s_info(server_addr, timeout=2)

            steam_servers[server_addr] = info
        except Exception as err:
            debug(f"\n{c.red}Unexpected A {err=}, {type(err)=}{c.reset}")
    value = f'{c.lightgrey}{len(steam_servers)} servers{c.reset}'
    print("\r{0}".format(value), end='\n')
    print()

# [ {"server_addr": (ip, port), "info": {a2s_info}}, ... ]
priority_servers = []
# [ (ip, port), ... ]
server_queue = []
# [ (ip, port), ... ]
previously_joined = []


def is_priority_server(server_addr):
    for server in priority_servers:
        if server_addr == server["server_addr"]:
            return True
    return False


def get_priority_config(server_addr):
    for server in priority_servers:
        if server_addr == server["server_addr"]:
            return server["config"]


# server_addr   - (ip, port)
# server_info   - {a2s_info}
def should_server_queue(server_addr, server_info, min_players=0, name_ignore=None, verify_name=None,
                        check_playercount=True):
    if verify_name is None:
        verify_name = []
    if name_ignore is None:
        name_ignore = []
    queue = True
    reasons = []
    # Shouldn't happen but doesn't hurt to check
    if server_info["game"] != "Hell Let Loose" or server_info["game_id"] != 686810:
        queue = False
        reasons.append("Server not HLL")
    # Already queued
    if server_addr in server_queue:
        queue = False
        reasons.append("Already queued")
    # Previously joined
    if server_addr in previously_joined:
        queue = False
        reasons.append("Previously joined")
    # Only real 100 player servers. Not 64 player Bob the Builder
    if server_info["max_players"] != 100:
        queue = False
        reasons.append("Not 100 max")
    # Servers with no password
    if server_info["visibility"] != 0:
        queue = False
        reasons.append("Passworded")
    # Server name doesn't contain specified keywords
    for word in name_ignore:
        if str(word).lower() in str(server_info["name"]).lower():
            queue = False
            reasons.append(f"Name has [{word}]")
    # Verify name does contain a specific word
    for word in verify_name:
        if str(word).lower() not in str(server_info["name"]).lower():
            queue = False
            reasons.append(f"Name missing [{word}]")
    # Player count is within desired range
    if check_playercount and (server_info["players"] < min_players or server_info["players"] >= seeded_player_limit):
        queue = False
        reasons.append(f"Not in range [{min_players},{seeded_player_limit}]")

    return {"queue": queue, "reasons": reasons}


print(f'{c.yellow}Checking/queueing priority servers{c.reset}')
for try_server in servers:
    if "steam_search" in try_server.keys():
        potential_add = []
        for server_addr in steam_servers:
            info = steam_servers[server_addr]

            check = should_server_queue(server_addr, info, verify_name=split_whitespace(try_server["steam_search"]),
                                        check_playercount=False)

            already_priority = is_priority_server(server_addr)

            if check["queue"] and not already_priority:
                potential_add.append((info["players"], server_addr, info))
            else:
                pass

        potential_add.sort(key=lambda a: a[0], reverse=True)

        if len(potential_add) > 0:
            server_addr = potential_add[0][1]
            info = potential_add[0][2]

            print(
                f'Priority server : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            priority_servers.append({"server_addr": server_addr, "info": info, "config": try_server})

    elif "address" in try_server.keys():
        server_ip = str(try_server["address"].split(':')[0])
        server_port = int(try_server["address"].split(':')[1])

        query_port_offset = [15, 17890, 19238, 17670, 18238, 20127]
        potential_query_port = [server_port]  # incase already using query port (battlemetrics copied)
        for offset in query_port_offset:
            potential_query_port.append(server_port + offset)

        valid_port = False
        for port in potential_query_port:
            try:
                server_addr = (server_ip, port)

                info = gs.a2s_info(server_addr, timeout=1)
                valid_port = True

                check = should_server_queue(server_addr, info, verify_name=split_whitespace(try_server["verify"]),
                                            check_playercount=False)

                if server_addr not in steam_servers:
                    steam_servers[server_addr] = info

                if check["queue"]:
                    print(
                        f'Priority server : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
                    print(
                        f'Priority seeding : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')

                else:
                    pass

                break
            except:
                continue
        if valid_port:
            # print(f'Could not find valid query port')
            pass
    else:
        continue
print()

# If not monitoring priority servers, queue seeding ones at runtime and go into perpetual after
if not priority_monitor:
    for server in priority_servers:
        server_addr = server["server_addr"]
        info = server["info"]
        config = server["config"]

        min_players = 0
        if "min_players" in config:
            min_players = int(config["min_players"])

        check = should_server_queue(server_addr, info, min_players=min_players, check_playercount=True)

        status_str = f'[{c.green}{str(info["players"])}{c.reset}/{c.green}{str(info["max_players"])}{c.reset}]'.rjust(
            27)

        if check["queue"]:
            print(
                f'{c.green}Seeding{c.reset} {status_str} : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            server_queue.append(server_addr)
        elif info["players"] >= seeded_player_limit:
            print(
                f'{c.darkgrey}Seeded{c.reset} {status_str} : {c.lightgrey}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
        else:
            print(
                f'{c.darkgrey}Skip{c.reset}   {status_str} : {c.lightgrey}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            print(f'  {c.darkgrey}Skip reason(s){c.reset} : {c.darkgrey}{check["reasons"]}{c.reset}')
    print()

if not hll_game.is_running():
    print(f'{c.lightgrey}Launching game...{c.reset}')

    if not debug_no_game:
        hll_game.launch_and_wait()
else:
    print(f'{c.lightgrey}Game already running{c.reset}')
print()

printed_progress = False


# Prefix for print() statements
def nl():
    global printed_progress
    prefix = '\n' if printed_progress else ''
    printed_progress = False
    return prefix


try:
    print(f'{c.yellow}Starting seeding process{c.reset}')
    print()

    search_for_next = False
    next_server = True
    current_server = None
    latest_info = None
    sw.start("seeding")
    server_type = None
    timeouts = 0

    player_threshold = seeded_player_limit
    player_minimum = 0

    players_max_count = 0
    players_join_count = 0
    players_done_count = 0


    def server_check():
        global next_server, current_server

        priority_server = None
        if priority_monitor is True and not is_priority_server(current_server):
            # typically less than a second for ~10 servers
            priority_server = priority_server_check()

            if priority_server is not None and priority_server is not current_server:
                print()
                print(f'{c.lightcyan}Priority server now seeding{c.reset}')
                server_queue.insert(0, priority_server)
                next_server = True

        if current_server is None and len(server_queue) == 0 and perpetual_mode and priority_server is None:
            max = perpetual_max_servers
            if priority_monitor:
                max = 1

            # typically ~30 seconds for ~250 servers assuming early disqualify
            sw.start("perpetual")
            perpetual_servers = perpetual_search(max_servers=max)
            debug(f'{nl()}{c.darkgrey}{sw.seconds("perpetual")}s perpetual search - {perpetual_servers}{c.reset}')

            if perpetual_servers is not None and len(perpetual_servers) > 0:
                for server in perpetual_servers:
                    server_queue.append(server)
                next_server = True
            print()


    # Keep checking priority server states and switch to them when needed
    def priority_server_check():
        for server in priority_servers:
            server_addr = server["server_addr"]
            config = server["config"]

            try:
                global latest_info
                latest_info = gs.a2s_info(server_addr, timeout=server_query_timeout)
                server["info"] = latest_info
                steam_servers[server_addr] = latest_info

                min_players = 0
                if "min_players" in config:
                    min_players = int(config["min_players"])

                check = should_server_queue(server_addr, latest_info, min_players=min_players, check_playercount=True)

                global current_server
                if check["queue"] and server_addr not in server_queue and server_addr != current_server:
                    return server_addr
            except:
                continue
        pass


    # Perpetual mode query server list again for seeding servers and queue up
    def perpetual_search(max_servers=perpetual_max_servers):
        print()
        print(f'{c.lightcyan}Perpetual mode searching for more seeding servers...{c.reset}')

        early_ignored = 0
        potential_add = []
        for server_addr in steam_servers:
            early_check = should_server_queue(server_addr, steam_servers[server_addr],
                                              name_ignore=ignore_name_contains,
                                              check_playercount=False)
            if not early_check["queue"]:
                early_ignored += 1
                # debug(f'{c.darkgrey}Early disqualify {server_addr} {early_check["reasons"]} {steam_servers[server_addr]["name"]}{c.reset}')
                continue

            try:
                info = gs.a2s_info(server_addr, timeout=1)
                steam_servers[server_addr] = info
                check = should_server_queue(server_addr, info, min_players=perpetual_min_players,
                                            name_ignore=ignore_name_contains)
                if check["queue"]:
                    potential_add.append((info["players"], server_addr))
            except:
                continue
        potential_add.sort(key=lambda a: a[0], reverse=True)

        debug(f'{c.darkgrey}{early_ignored} servers early ignored{c.reset}')

        to_return = []
        i = 1
        for server in potential_add:
            if i > max_servers:
                break
            server_addr = server[1]
            info = steam_servers[server_addr]
            status_str = f'[{c.green}{str(info["players"])}{c.reset}/{c.green}{str(info["max_players"])}{c.reset}]'.rjust(
                27)
            print(
                f'{c.green}Queued{c.reset} {status_str} : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            to_return.append(server_addr)
            i += 1
        return to_return


    def seed_progress(current, total, players_max_count=0, timeouts=0):
        bar_length = 15
        fraction = min(1.0, current / total)
        arrow = int(fraction * bar_length - 1) * '-' + '>'
        padding = int(bar_length - len(arrow)) * ' '

        threshold = int(players_max_count / 2)
        diff = players_max_count - current
        thresh_diff = players_max_count - threshold
        dead_fraction = min(1.0, diff / thresh_diff)

        progress_bar = f'[{c.green}{arrow}{c.reset}{padding}]'
        status_str = f'Status: {c.green}{current}{c.reset}/{c.green}{total}  {int(fraction * 100)}{c.reset}%'
        elapsed_str = f'Elapsed: {c.green}{time.strftime("%Hh %Mm %Ss", time.gmtime(sw.seconds("seeding")))}{c.reset}'
        dying_str = f'Dying: {c.orange}{diff}{c.reset}/{c.orange}{thresh_diff}  {int(dead_fraction * 100)}{c.reset}%{c.reset}'
        timeout_str = "" if timeouts == 0 else f'Timeout: {c.red}{timeouts}{c.reset}/{c.red}{query_timeout_limit}{c.reset}'

        value = f'Seed progress {progress_bar}  {status_str}  {elapsed_str}  {dying_str}  {timeout_str}  '
        print("\r{0}".format(value), end='')
        global printed_progress
        printed_progress = True


    while True:
        time.sleep(1)
        if next_server and len(server_queue) == 0 and not priority_monitor and not perpetual_mode:
            print()
            print(f'Ran out of servers.')
            # no servers and no ongoing processes, script done
            break

        server_check()

        if len(server_queue) >= 1 and next_server:
            current_server = server_queue.pop(0)
            info = steam_servers[current_server]
            previously_joined.append(current_server)
            next_server = False
            players_max_count = 0
            timeouts = 0
            sw.start("seeding")
            player_threshold = seeded_player_limit + random.randrange(0, seeded_player_variability)
            player_threshold = min(player_threshold, info["max_players"])
            server_type = "Priority" if is_priority_server(current_server) else "Perpetual"
            print()
            print(f'{nl()}{c.yellow}Monitoring Server ({server_type}){c.reset}')
            printed_progress = False
            print(f'{c.darkgrey}{info["name"]}{c.reset}')
            print(f'Connecting {c.lightblue}{str(current_server).ljust(27)}{c.reset}')

            player_minimum = 0
            config = get_priority_config(current_server)
            if "min_players" in config:
                player_minimum = int(config["min_players"])

            if not debug_no_game:
                sw.start("idle_check")
                hll_game.join_server_addr(current_server)
                time.sleep(15)

        if dt.today() >= stop_datetime:
            print()
            print(f'{nl()}{c.yellow}Seeding stop time reached{c.reset}')
            hll_game.kill()
            hll_game.wait_until_dead()
            break
        elif priority_monitor and dt.today() >= stop_priority_datetime:
            print(f'{nl()}{c.orange}Priority monitor stop time reached.{c.reset}')
            priority_monitor = False

            if is_priority_server(current_server):
                current_server = None
            continue
        if current_server is None and len(server_queue) == 0:
            debug(f'{nl()}{c.darkgrey}current_server is None and len(server_queue) == 0{c.reset}')
            continue
        elif current_server is None and len(server_queue) >= 1:
            debug(f'{nl()}{c.darkgrey}current_server is None and len(server_queue) >= 1{c.reset}')
            next_server = True
            continue

        try:
            latest_info = gs.a2s_info(current_server, timeout=server_query_timeout)

            players = latest_info["players"]
            if players > players_max_count:
                players_max_count = players

            seed_progress(players, player_threshold,
                          players_max_count=players_max_count,
                          timeouts=timeouts)

            if players >= player_threshold:
                print(f'{nl()}{c.lightgreen}Seeded!{c.reset}')
                current_server = None
            elif is_priority_server(current_server) and players < min_players:
                print(f'{nl()}{c.orange}Priority server below configured {min_players} players{c.reset}')
                current_server = None
            elif players < perpetual_min_players and not is_priority_server(current_server):
                print(f'{nl()}{c.orange}Perpetual server below {perpetual_min_players} players{c.reset}')
                current_server = None
            elif players_max_count > perpetual_min_players and players <= players_max_count / 2:
                print(f'{nl()}{c.orange}Player count halved, server likely dying{c.reset}')
                current_server = None

            if not debug_no_game:
                if hll_game.did_game_crash():
                    print(f'{nl()}{c.orange}Game crashed{c.reset}')
                    print(f'{nl()}{c.darkgrey}Relaunching game...{c.reset}')
                    hll_game.wait_until_dead()
                    hll_game.launch_and_wait()

                    print(f'{nl()}Reconnecting {c.lightblue}{str(current_server).ljust(27)}{c.reset}')
                    hll_game.join_server_addr(current_server)
                    time.sleep(15)

                elif check_idle_kick and sw.seconds("idle_check") > 60:
                    try:
                        players = gs.a2s_players(current_server, timeout=server_query_timeout)

                        names = []
                        for player in players:
                            names.append(player["name"])

                        name_present = player_name.lower() in (string.lower() for string in names)

                        if not name_present:
                            print(f'{nl()}{c.red}{player_name} is no longer in the player list. Idle kick?{c.reset}')
                            hll_game.relaunch_and_wait()
                            current_server = None

                    except Exception as err:
                        pass

            time.sleep(server_query_rate)
        except Exception as err:
            timeouts += 1  # not a timeout but still quit if it errors N times

            if timeouts >= query_timeout_limit:
                print(f'{nl()}{c.red}Reached timeout limit{c.reset}')
                current_server = None

            debug(f"{nl()}{c.red}Unexpected B {err=}, {type(err)=}{c.reset}")
            continue

    print()
    print(f"{c.lightgreen}Seeding done!{c.reset}")
except Exception as err:
    traceback.print_exc()
    print(f"{nl()}{c.red}Unexpected A {err=}, {type(err)=}{c.reset}")

print()
input("Press enter to exit")
