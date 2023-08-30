# <img src="readme_icon2.png" width="466" />

Advanced, customizable, seeding script for Hell Let Loose.

Makes use of and credit to [KtodaZ](https://github.com/KtodaZ/) for batch scripts and scheduled task XML.

<img src="readme_preview.png" width="700" />

## Features

- Schedule a specific time to wake your computer and start the seed script `setup.bat`
- Seed multiple servers in a specific order
- Define priority servers by IP or search by server name
- Monitors and switches servers once each hits 50 pop
- Perpetual seeding mode
    - Searches the steam server list for additional seeding servers once it's done with your priority servers
    - Checks for servers matching criteria:
        - 10-50 pop
        - No password
        - Name does not contain keywords (CN, HLL Official, Event, Training)
        - Max players is 100 (a real server, not bob the builder)
    - Help out the rest of the HLL community!
- Detects when a server is dying rather than seeding (server pop drops by half) and moves on
- Detects when you are no longer in the server's player list for whatever reason (usually idle kick) and moves on
- Detects when the game crashed and relaunches the game to keep seeding
- Multiple seeding methods
    - `endtime` Stops and closes the game at the specified time or when done*
    - `minutes` Stops and closes the game after _N_ minutes or when done*
    - \* when done with defined list. long seed times more relevant for perpetual mode 
- Closes the game when done seeding

## Setup and Install

1. Install the latest Python 3.x
	- https://www.python.org/downloads/
	- Check the box to add Python to PATH
2. Open command prompt and install required packages
	- `pip install -r requirements.txt`
3. Open `seeding.yaml` to configure script settings and servers to seed
    - Most default values should be fine as is though can be tweaked however you want
    - Most relevant properties you'll probably want to change:
       - `seeding.method`
       - `priority.servers`
       - `priority.monitor_enabled`
       - `check_idle_kick` and `player_name`
       - `perpetual_mode.enabled`
4. Run `setup.bat` to create a scheduled task that will wake up the computer and run the seeding script

To verify a task is scheduled use `verify.bat`.

To uninstall a scheduled task use `uninstall.bat`.

To manually start the script again use `runGame.bat` (this is what the scheduled task calls).

## How it works

The python script uses A2S or the Valve Protocol to query game servers 
for their current player count and current player names joined.

https://developer.valvesoftware.com/wiki/Server_queries

It also uses the Valve Master Server Query Protocol to search for all current Hell Let Loose servers 
to search for ones that match your priority server criteria or for perpetual mode.

https://developer.valvesoftware.com/wiki/Master_Server_Query_Protocol

## Potential usages

1. I want to seed my priority servers then help out other seeding community servers. However, I also want it to go back to a priority server if it starts seeding or crashes later on.

Current seeding yaml settings are set to do this. `priority.monitor_enabled` and `perpetual_mode.enabled` are on.

It will go back and forth between priority and random perpetual servers as needed.

2. I only want to seed my priority servers and nothing else.

Disable `perpetual_mode.enabled` in the seeding yaml.

3. I want to run multiple seeding accounts with this script.

You'll need separate PCs and script instances for each one of course, however for each script its:

Recommended to stagger the `priority.min_players` or individual server `min_players`
and potentially change `seeded_player_variability` depending on number of accounts.
These settings are to mitigate issues where multiple accounts could get stuck on the same server that is dead 
or so that they all don't leave a just-seeded server at the exact same time.

For example:

- Seed account 1 script `priority.min_players: 0`
- Seed account 2 script `priority.min_players: 0`
- Seed account 3 script `priority.min_players: 2`
- Seed account 4 script `priority.min_players: 3`
- Seed account 5 script `priority.min_players: 4`

Note: since the player count doesn't exclude yourself, a minimum of 1 nearly the same as 0.