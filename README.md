# HLL Advanced Seeder

Seeding script automatically launches the game and seeds multiple HLL servers

Extended with Python for more advanced seeding automation, based on initial batch scripts from KtodaZ.

## Setup and Install

1. Install the latest Python 3.x
	- https://www.python.org/downloads/
	- Check the box to add Python to PATH
2. Open command prompt and install required packages
	- `pip install -r requirements.txt`
3. Open `config.txt` and set the time in minutes for when to close the game
4. Open `seeding.yaml` to configure python script settings and servers to seed
    - Use the `Steam > View > Game Server` browser to find and copy `ip:port` for desired servers
	- Set a verify_name for each incase they change hosts
5. Run `setup.bat` to create a scheduled task that will wake up the computer and run the seeding script

## How it works

The python script uses A2S or the Valve Protocol to query the specified game servers for their current player count at a specified interval of seconds.

https://developer.valvesoftware.com/wiki/Server_queries