import a2s, yaml, time, subprocess
from steam import game_servers as gs

class Server:
    def __init__(self):
        self.desc = ""
        self.server_ip = ""
        self.connect_port = 0
        self.query_port = 0
        self.valid = False

class colors:
    reset = '\033[0m'
    bold = '\033[01m'
    disable = '\033[02m'
    underline = '\033[04m'
    reverse = '\033[07m'
    strikethrough = '\033[09m'
    invisible = '\033[08m'
 
    class fg:
        black = '\033[30m'
        red = '\033[31m'
        green = '\033[32m'
        orange = '\033[33m'
        blue = '\033[34m'
        purple = '\033[35m'
        cyan = '\033[36m'
        lightgrey = '\033[37m'
        darkgrey = '\033[90m'
        lightred = '\033[91m'
        lightgreen = '\033[92m'
        yellow = '\033[93m'
        lightblue = '\033[94m'
        pink = '\033[95m'
        lightcyan = '\033[96m'

    class bg:
        black = '\033[40m'
        red = '\033[41m'
        green = '\033[42m'
        orange = '\033[43m'
        blue = '\033[44m'
        purple = '\033[45m'
        cyan = '\033[46m'
        lightgrey = '\033[47m'

def process_exists(process_name):
    progs = str(subprocess.check_output('tasklist'))
    if process_name in progs:
        return True
    else:
        return False

def seed_progress(current, total, max_poll_count, seed_start):
    bar_length = 25
    fraction = min(1.0, current / total)

    arrow = int(fraction * bar_length - 1) * '-' + '>'
    padding = int(bar_length - len(arrow)) * ' '
    
    elapsed = (time.time() - seed_start)
    elapsed_str = time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))
    
    dead_percent = ''
    threshold = int(max_poll_count / 2)
    diff = max_poll_count - info.player_count
    thresh_diff = max_poll_count - threshold
    if seeding_yaml["move_on_if_server_dead"] and max_poll_count > 9:
        dead_fraction = min(1.0, diff / thresh_diff)
        
        dead_percent = f'Dying: {colors.fg.orange}{diff}{colors.reset}/{colors.fg.orange}{thresh_diff}  {int(dead_fraction*100)}{colors.reset}%{colors.reset}'

    progress_done = current >= total or (seeding_yaml["move_on_if_server_dead"] and max_poll_count > 9 and diff >= thresh_diff)
    ending = '\n' if progress_done else '\r'

    print(f'Seed progress: [{colors.fg.green}{arrow}{colors.reset}{padding}]  Status: {colors.fg.green}{current}{colors.reset}/{colors.fg.green}{total}  {int(fraction*100)}{colors.reset}%  Elapsed: {colors.fg.green}{elapsed_str}{colors.reset}  {dead_percent}', end=ending)

try:
    print('Loading seeding.yaml')
    with open('seeding.yaml', 'r') as file:
        seeding_yaml = yaml.safe_load(file)
    print(seeding_yaml)
    print()
    print()

    query_timeout = seeding_yaml["server_query_timeout"]

    valid_servers = []

    def perpetual_seeding_search():
        print()
        print(f'{colors.fg.orange}Ran out of servers. Perpetual seeding enabled, searching for servers to seed...{colors.reset}')
        
        # Note: no password filter doesn't seem to work
        servers_to_add = []
        for server_addr in gs.query_master(r'\appid\686810\password\0\full\1\empty\1', max_servers=500):
            try:
                info = a2s.info(server_addr, timeout=2)
  
                if not info.password_protected and info.player_count < 50 and info.player_count > 10 and info.max_players == 100 and "CN" not in info.server_name:
                    servers_to_add.append((info.player_count, info, server_addr))
            except:
                continue
        
        # join most populated servers first
        servers_to_add.sort(key=lambda a: a[0], reverse=True)
        
        for server in servers_to_add:
            info = server[1]
            server_addr = server[2]
            
            desc = info.server_name[0:10]
                    
            print(f'{colors.fg.green}SEEDING (Queued) [ {desc} ] query_port={server_addr[1]}, status={info.player_count}/{info.max_players}{colors.reset}')
            print(f'    {colors.fg.darkgrey}{info.server_name}{colors.reset}')
            
            server = Server()
            server.desc = desc
            server.server_ip = server_addr[0]
            server.query_port = server_addr[1]
            server.valid = True
            
            valid_servers.append(server)
            

    # Check the servers listed to monitor
    # Are they still valid? What's the query port?
    print('Initial server check')

    for try_server in seeding_yaml["seeding_list"]:
        game_connect = try_server["connect"]

        server_ip = game_connect.split(':')[0]
        server_connect_port = int(game_connect.split(':')[1])

        query_port_offset = [
            15,     # G-Portal
            17890,  # GTX
            19238,  # Low.MS
            17670,  # ???       offset from fll.fi / WTH
            18238,  # ???       offset from HLL Brasil
            20127   # ???       offset from chinese servers
        ]
        potential_query_ports = []
        for offset in query_port_offset:
            potential_query_ports.append(server_connect_port + offset)
        potential_query_ports.append(server_connect_port) # incase accidentally using query in yaml

        valid_server = False
        quit_early = False
        
        for query_port in potential_query_ports:
            try:
                info = a2s.info((server_ip, query_port), timeout=1)
                desc = try_server["description"]
                
                if seeding_yaml["verify_name"] and "verify_name" in try_server.keys() and try_server["verify_name"] not in info.server_name:
                    print(f'{colors.fg.red}INVALID [ {desc} ]. Server name did not contain keyword [ {try_server["verify_name"]} ]{colors.reset}')
                    print(f'    {colors.fg.darkgrey}{info.server_name}{colors.reset}')
                    quit_early = True
                    break
                if info.password_protected:
                    print(f'{colors.fg.red}INVALID [ {desc} ] was password protected{colors.reset}')
                    print(f'    {colors.fg.darkgrey}{info.server_name}{colors.reset}')
                    quit_early = True
                    break
                
                valid_server = True

                if info.player_count >= seeding_yaml["seeded_player_limit"]:
                    print(f'{colors.fg.lightgrey}SEEDED (Ignoring) [ {desc} ] query_port={query_port}, status={info.player_count}/{info.max_players}{colors.reset}')
                    print(f'    {colors.fg.darkgrey}{info.server_name}{colors.reset}')
                    break
                else:
                    print(f'{colors.fg.green}SEEDING (Queued) [ {desc} ] query_port={query_port}, status={info.player_count}/{info.max_players}{colors.reset}')
                    print(f'    {colors.fg.darkgrey}{info.server_name}{colors.reset}')
                
                    server = Server()
                    server.desc = try_server["description"]
                    server.server_ip = server_ip
                    server.connect_port = server_connect_port
                    server.query_port = query_port
                    server.valid = True
                    
                    valid_servers.append(server)
                
                break
            except:
                continue
        
        if not valid_server and not quit_early:
            print(f'{colors.fg.red}INVALID [ {try_server["description"]} ] Could not find query port{colors.reset}')
    print()
    print()

    if len(valid_servers) > 0 or seeding_yaml["perpetual_seed_from_steam"]:
        if process_exists('HLL-Win64-Shipping.exe'):
            print("Game already running, skipping launch and wait")
            time.sleep(1)
            print()
            print()
        else:
            print("Launching game and waiting 60 seconds...")
            subprocess.run("cmd /c start steam://run/686810")
            time.sleep(60)
            print()
            print()

        seed_index = 0
        monitor_start = False
        monitor_start2 = False
        tried_connect = False
        seed_start = time.time()
        exception_retry = 0
        max_poll_count = 0

        print("Starting seeding server rotation")
        while True:
            if seed_index >= len(valid_servers):
                if seeding_yaml["perpetual_seed_from_steam"]:
                    perpetual_seeding_search()
                    
                    if seed_index >= len(valid_servers):
                        print(f'{colors.fg.orange}Failed to find more servers. Waiting a couple minutes...{colors.reset}')
                        time.sleep(180)
                else:
                    break
            
            server = valid_servers[seed_index]
            
            if not monitor_start:
                print()
                print()
                print(f'{colors.fg.yellow}Monitoring [ {server.desc} ]{colors.reset}')
                tried_connect = False
                monitor_start = True
                seed_start = time.time()

            try:
                info = a2s.info((server.server_ip, server.query_port), timeout=query_timeout)
                
                if not monitor_start2:
                    print(f'{colors.fg.darkgrey}{info.server_name}{colors.reset}')
                    monitor_start2 = True
                
                if info.player_count > max_poll_count:
                    max_poll_count = info.player_count
                if seeding_yaml["move_on_if_server_dead"] and max_poll_count > 9 and info.player_count <= max_poll_count / 2:
                    seed_progress(info.player_count, seeding_yaml["seeded_player_limit"], max_poll_count, seed_start)
                    
                    print(f'{colors.fg.orange}{server.desc} player count has halved, likely dead.{colors.reset}')
                    print('Moving on.')
                    seed_index += 1
                    exception_retry = 0
                    monitor_start = False
                    monitor_start2 = False
                    max_poll_count = 0
                    continue
                
                if info.player_count >= seeding_yaml["seeded_player_limit"]:
                    seed_progress(info.player_count, seeding_yaml["seeded_player_limit"], max_poll_count, seed_start)

                    print(f'{server.desc} is seeded {info.player_count}/{info.max_players}')
                    print('Moving on.')
                    seed_index += 1
                    exception_retry = 0
                    monitor_start = False
                    monitor_start2 = False
                    max_poll_count = 0
                    continue
                
                if not tried_connect:
                    connect = "steam://connect/" + str(server.server_ip) + ":" + str(server.query_port)
                    command = "cmd /c start " + connect
                    
                    print('Connecting...', connect)
                    subprocess.run(command)
                    tried_connect = True
                
                seed_progress(info.player_count, seeding_yaml["seeded_player_limit"], max_poll_count, seed_start)

            except Exception as err:
                print(f"\n{colors.fg.red}Unexpected {err=}, {type(err)=}{colors.reset}")
                print(f"{colors.fg.red}Problem querying valid server {server.desc}. Retry {exception_retry+1}/4{colors.reset}")

                if exception_retry < 3:
                    exception_retry += 1
                    time.sleep(30)
                else:
                    print(f"{colors.fg.red}Failed to query 4 times. Moving on.")
                    server.valid = False
                    seed_index += 1
                    exception_retry = 0
                    monitor_start = False
                    
            if seed_index >= len(valid_servers):
                if seeding_yaml["perpetual_seed_from_steam"]:
                    perpetual_seeding_search()
                    
                    if seed_index >= len(valid_servers):
                        print(f'{colors.fg.orange}Failed to find more servers. Waiting a couple minutes...{colors.reset}')
                        time.sleep(180)
                else:
                    break
                
            time.sleep(seeding_yaml["server_query_rate"])

        print()
        print()
        
        print("Seeding Done!")
    else:
        print("No servers to be seeded")
    
except Exception as err:
    print(f"Unexpected {err=}, {type(err)=}")

print()
input("Press enter to exit")