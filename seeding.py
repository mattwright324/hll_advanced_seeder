import a2s, yaml, time, subprocess

class Server:
    def __init__(self):
        self.desc = ""
        self.server_ip = ""
        self.connect_port = 0
        self.query_port = 0
        self.valid = False

def seed_progress(current, total, seed_start):
    bar_length = 25
    fraction = current / total

    arrow = int(fraction * bar_length - 1) * '-' + '>'
    padding = int(bar_length - len(arrow)) * ' '
    
    elapsed = (time.time() - seed_start)
    elapsed_str = time.strftime("%Hh%Mm%Ss", time.gmtime(elapsed))

    ending = '\n' if current >= total else '\r'

    print(f'Seed progress: [{arrow}{padding}]  Status: {current}/{total}  {int(fraction*100)}%  Elapsed: {elapsed_str}', end=ending)

try:
    print('Loading seeding.yaml')
    with open('seeding.yaml', 'r') as file:
        seeding_yaml = yaml.safe_load(file)
    print(seeding_yaml)
    print()
    print()

    query_timeout = seeding_yaml["server_query_timeout"]

    valid_servers = []

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

        valid_server = False
        for query_port in potential_query_ports:
            try:
                info = a2s.info((server_ip, query_port), timeout=3)
                desc = try_server["description"]

                if seeding_yaml["verify_name"] and hasattr(try_server, "verify_name") and try_server["verify_name"] not in info.server_name:
                    print(f'INVALID [ {desc} l. Server name did not contain keyword [ {try_server["verify_name"]} ] was [ {info.server_name} ]')
                    break
                if info.password_protected:
                    print(f'INVALID [ {desc} ] was password protected')
                    break
                
                valid_server = True

                if info.player_count >= seeding_yaml["seeded_player_limit"]:
                    print(f'SEEDED (Ignoring) [ {desc} ] query_port={query_port}, status={info.player_count}/{info.max_players}')
                    break
                else:
                    print(f'SEEDING (Added to queue) [ {desc} ] query_port={query_port}, status={info.player_count}/{info.max_players}')
                
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
        
        if not valid_server:
            print(f'INVALID [ {try_server["description"]} ]')
    print()
    print()

    if len(valid_servers) > 0:
        print("Launching game and waiting 60 seconds...")
        subprocess.run("cmd /c start steam://run/686810")
        time.sleep(60)
        print()
        print()

        seed_index = 0
        monitor_start = False
        seed_start = time.time()
        exception_retry = 0

        print("Starting seeding server rotation")
        while True:    
            server = valid_servers[seed_index]
            
            if not monitor_start:
                print()
                print()
                print('Monitoring [', server.desc, ']')
                tried_connect = False
                monitor_start = True
                seed_start = time.time()

            try:
                info = a2s.info((server.server_ip, server.query_port), timeout=query_timeout)
                
                if info.player_count >= seeding_yaml["seeded_player_limit"]:
                    print(f'{server.desc} is seeded {info.player_count}/{info.max_players}')
                    print('Moving on.')
                    seed_index += 1
                    exception_retry = 0
                    monitor_start = False
                    continue
                
                if not tried_connect:
                    connect = "steam://connect/" + str(server.server_ip) + ":" + str(server.query_port)
                    command = "cmd /c start " + connect
                    
                    print('Connecting...', connect)
                    subprocess.run(command)
                    tried_connect = True
                
                seed_progress(info.player_count, seeding_yaml["seeded_player_limit"], seed_start)

            except Exception as err:
                print(f"Unexpected {err=}, {type(err)=}")
                print(f"Problem querying valid server {server.desc}. Retry {exception_retry}/3")

                if exception_retry < 3:
                    exception_retry += 1
                    time.sleep(30)
                else:
                    print(f"Failed to query 3 times. Moving on.")
                    server.valid = False
                    seed_index += 1
                    exception_retry = 0
                    monitor_start = False
                    
            if seed_index >= len(valid_servers):
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