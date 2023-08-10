# required
import sys, yaml, time, traceback, random
from datetime import datetime as dt, timedelta
from steam import game_servers as gs
# project required
import colors as c, hll_game

# Don't launch the game, join servers, or check their player lists
# Otherwise, operates as if it did those things for testing
debug_no_game = True
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
priority_monitor = bool( seeding_yaml["priority_monitor"])
priority_monitor_endtime = try_parsing_time(seeding_yaml["priority_monitor_endtime"], "priority_monitor_endtime")
servers = list(seeding_yaml["priority_servers"])
seeded_player_limit = int(seeding_yaml["seeded_player_limit"])
seeded_player_variability = int(seeding_yaml["seeded_player_variability"])
server_query_rate = int(seeding_yaml["server_query_rate"])
server_query_timeout = int(seeding_yaml["server_query_timeout"])
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

print(f'{c.yellow}Summary{c.reset}')
print(f'Run method       : {c.lightblue}{seeding_method}{c.reset} or when done')
print(f'Start time       : {c.lightblue}{start_datetime}{c.reset}')
print(f'Plan end time    : {c.lightblue}{stop_datetime}{c.reset} or {c.darkgrey}{plan_runtime_str} from start{c.reset}')
print(f'Perpetual mode   : {c.green if perpetual_mode else c.darkgrey}{perpetual_mode}{c.reset}')
print(f'Priority monitor : {c.green if priority_monitor else c.darkgrey}{priority_monitor}{c.reset}')
print(f'Servers listed   : {c.lightblue}{len(servers)}{c.reset}')
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


# server_addr   - (ip, port)
# server_info   - {a2s_info}
def should_server_queue(server_addr, server_info, min_players=0, name_ignore=None, verify_name=None, check_playercount=True):
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

            already_priority = False
            # Already in priority list
            for server in priority_servers:
                if server["server_addr"] == server_addr:
                    already_priority = True

            if check["queue"] and not already_priority:
                potential_add.append((info["players"], server_addr, info))
            else:
                pass

        potential_add.sort(key=lambda a: a[0], reverse=True)

        if len(potential_add) > 0:
            server_addr = potential_add[0][1]
            info = potential_add[0][2]

            print(f'Priority server : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
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
                    print(f'Priority server : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
                    print(f'Priority seeding : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')

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

        status_str = f'[{c.green}{str(info["players"])}{c.reset}/{c.green}{str(info["max_players"])}{c.reset}]'.rjust(27)

        if check["queue"]:
            print(f'{c.green}Seeding{c.reset} {status_str} : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            server_queue.append(server_addr)
        elif info["players"] >= seeded_player_limit:
            print(f'{c.darkgrey}Seeded{c.reset} {status_str} : {c.lightgrey}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
        else:
            print(f'{c.darkgrey}Skip{c.reset}   {status_str} : {c.lightgrey}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
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
    return '\n' if printed_progress else ''

try:
    print(f'{c.yellow}Starting seeding process{c.reset}')

    next_server = True
    current_server = None
    latest_info = None
    seed_start = time.time()
    max_poll_count = 0
    player_threshold = seeded_player_limit
    server_type = None

    def server_check(current, threshold):
        global next_server, current_server
        debug(f'server_check({current}, {threshold})')

        priority_server = None
        if priority_monitor is True:
            start = time.time()
            priority_server = priority_server_check()
            debug(f'{nl()}{c.darkgrey}{time.time()-start}s priority check - {priority_server}{c.reset}')

            if priority_server is not None and priority_server is not current_server:
                server_queue.insert(0, priority_server)
                next_server = True

        if (current_server is None or current >= threshold) and perpetual_mode and priority_server is None:
            max = perpetual_max_servers
            if priority_monitor:
                max = 1

            perpetual_servers = perpetual_search(max_servers=max)
            debug(f'perpetual - {perpetual_servers}')

            if perpetual_servers is not None and len(perpetual_servers) > 0:
                for server in perpetual_servers:
                    server_queue.append(server)
                next_server = True

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
        print(f'{nl()}{c.yellow}Perpetual mode searching for more seeding servers...{c.reset}')
        print()

        potential_add = []
        for server_addr in steam_servers:
            early_check = should_server_queue(server_addr, steam_servers[server_addr], check_playercount=False)
            if not early_check:
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

        to_return = []
        i = 1
        for server in potential_add:
            if i > max_servers:
                break
            server_addr = server[1]
            info = steam_servers[server_addr]
            status_str = f'[{c.green}{str(info["players"])}{c.reset}/{c.green}{str(info["max_players"])}{c.reset}]'.rjust(27)
            print(f'{c.green}Queued{c.reset} {status_str} : {c.lightblue}{str(server_addr).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            to_return.append(server_addr)
            i += 1
        return to_return

    def seed_progress(current, total, max_poll_count=0, seed_start=time.time()):
        bar_length = 15
        fraction = min(1.0, current/total)
        arrow = int(fraction * bar_length - 1) * '-' + '>'
        padding = int(bar_length - len(arrow)) * ' '

        elapsed = (time.time() - seed_start)

        threshold = int(max_poll_count / 2)
        diff = max_poll_count - current
        thresh_diff = max_poll_count - threshold
        dead_fraction = min(1.0, diff / thresh_diff)

        progress_bar = f'[{c.green}{arrow}{c.reset}{padding}]'
        status = f'Status: {c.green}{current}{c.reset}/{c.green}{total}  {int(fraction * 100)}{c.reset}%'
        elapsed_str = f'Elapsed: {c.green}{time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))}{c.reset}'
        dying = f'Dying: {c.orange}{diff}{c.reset}/{c.orange}{thresh_diff}  {int(dead_fraction * 100)}{c.reset}%{c.reset}'

        value = f'Seed progress {progress_bar} : {status}  {elapsed_str}  {dying}'
        print("\r{0}".format(value), end='')
        global printed_progress
        printed_progress = True


    while True:
        time.sleep(1)
        if next_server and len(server_queue) == 0 and not priority_monitor and not perpetual_mode:
            print()
            print(f'Ran out of servers. No priority or perpetual modes enabled.')
            # no servers and no ongoing processes, script done
            break

        if hll_game.did_game_crash() and not debug_no_game:
            print(f'{c.orange}Game crashed{c.reset}')
            hll_game.wait_until_dead()
            hll_game.launch_and_wait()

            status_str = f'[{c.green}{str(info["players"])}{c.reset}/{c.green}{str(info["max_players"])}{c.reset}]'.rjust(27)
            print(f'Connecting {status_str} : {c.lightblue}{str(current_server).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')
            hll_game.join_server_addr(current_server)
            time.sleep(15)

        if latest_info is not None:
            server_check(latest_info["players"], player_threshold)
        else:
            server_check(1, 1)

        if len(server_queue) >= 1 and next_server:
            current_server = server_queue.pop(0)
            info = steam_servers[current_server]
            previously_joined.append(current_server)
            next_server = False
            max_poll_count = 0
            seed_start = time.time()
            player_threshold = seeded_player_limit + random.randrange(0, seeded_player_variability)
            print()
            print(f'{nl()}{c.yellow}Monitoring Server{c.reset}')
            printed_progress = False
            print(f'Connecting : {c.lightblue}{str(current_server).ljust(27)}{c.reset}{c.darkgrey}{info["name"]}{c.reset}')

            if not debug_no_game:
                hll_game.join_server_addr(current_server)
                time.sleep(15)

        if current_server is None:
            print(f'{c.darkgrey}current_server = None{c.reset}')
            continue

        try:
            latest_info = gs.a2s_info(current_server, timeout=server_query_timeout)

            players = latest_info["players"]
            if players > max_poll_count:
                max_poll_count = players

            seed_progress(players, player_threshold,
                          max_poll_count=max_poll_count,
                          seed_start=seed_start)

            # try:
            #     players = gs.a2s_players(current_server, timeout=server_query_timeout)
            # except Exception as err:
            #     players = None

            time.sleep(server_query_rate)
        except Exception as err:
            traceback.print_exc()
            print(f"{nl()}{c.red}Unexpected B {err=}, {type(err)=}{c.reset}")
            continue

    print()
    print(f"{c.yellow}Seeding done!{c.reset}")
except Exception as err:
    traceback.print_exc()
    print(f"{nl()}{c.red}Unexpected A {err=}, {type(err)=}{c.reset}")

print()
input("Press enter to exit")
