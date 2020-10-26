import sys
import os
import os.path
import time
import json
import subprocess
import logging
import regex as re
from logging import handlers
from steam.client import SteamClient

configfilename = 'config.json'
logfile = 'steam-update-wrapper.log.txt'
lastupdatecheck = 0

# Configure logging to file and stream
def initlogs():
    global logger
    logger = logging.getLogger('steam-update-wrapper')
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)6s - %(message)s')
    fh = handlers.RotatingFileHandler(filename=logfile, encoding='utf-8', mode='a', maxBytes=50000, backupCount=5)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Logging initialised to {logfile}")

def loadconfig(filename):
    if not os.path.exists(filename):
        logger.error(f'No configuration file found - expected {filename}.  Exiting.')
        sys.exit()

    # Load the configuration file from config.json
    logger.info(f"Reading configuration file {filename}")
    with open('config.json') as config_file:
        config = json.load(config_file)
        return config

def getlatestbuildtime(appid, branch):
    """Get the last updated timestamp for the given appid and build
    name in seconds from the epoch"""
    try:

        client = SteamClient()

        client.anonymous_login()

        result = client.get_product_info(apps=[appid])

        buildid = result['apps'][appid]['depots']['branches'][branch]['buildid']
        timeupdated = int(result['apps'][appid]['depots']['branches'][branch]['timeupdated'])

        client.logout()

        logger.info(f'Last update time for appid {appid} on branch {branch} identified as {time.ctime(timeupdated)}.')

        return timeupdated
    except:
        logger.error(f'There was an issue fetching the latest build information from Steam for appid {appid} on branch {branch}.  Defaulting last updated time to epoch.')
        return 0

def parsebranch(extraflags):
    # If it's exactly -beta, return "beta", otherwise use regex.  If no match, return public.
    if extraflags.endswith('-beta'):
        return 'beta'

    pattern = r"-beta +(?P<branch>[a-zA-Z0-9_]*)? ?[\-+]?"

    match = re.match(pattern, extraflags)

    if match is not None:
        branch = match.group('branch')
        if branch == '':
            branch = 'beta'
        return branch

    return 'public'

def updategame(steamcmd, installdir, appid, extraflags):
    try:
        fullsteamcmd = f'{steamcmd} +login anonymous +force_install_dir {installdir} +app_update {appid} {extraflags} +quit'
        logger.info(f'Calling: {fullsteamcmd}')
        process = subprocess.run(fullsteamcmd)
        if process.returncode == 0:
            logger.info(f'Steamcmd exited successfully')
        else:
            logger.error(f'Steamcmd failed in some way')
            raise Exception("Steamcmd returned a non-zero exit code")
    except:
        logger.error(f'There was an issue running the steamcmd update.  Check your configuration.')
        raise

def startgameprocess(commandline):
    try:
        process = subprocess.Popen(commandline)
        logger.info(f'Successfully called game executable')
        return process
    except:
        logger.error(f'There was an issue launching the background process')
        raise

def stopgameprocess(process):
    logger.info(f'Sending SIGTERM to {process.pid}')
    process.terminate()
    logger.info(f'Waiting for process {process.pid} to terminate')
    process.wait()
    logger.info(f'Process terminated.  Hasta la vista baby.')

def main():
    initlogs()
    global configdata
    configdata = loadconfig(configfilename)

    # Check interval, defaults to 10 minutes
    appid = configdata.get('appid', -1)
    if appid == -1:
        logger.error(f'Must set an appid in  {configfilename}')
        sys.exit()

    steamcmdextras = configdata.get('steamcmdextras', '')
    if steamcmdextras == '':
        logger.info(f'No steamcmdextras setting in {configfilename}.  Defaulting to public branch.')
        branch = 'public'
    else:
        logger.info(f'Attempting to parse branch from steamcmdextras setting ({steamcmdextras})')
        branch = parsebranch(steamcmdextras)
        logger.info(f'Branch set to {branch}')

    steamcmd = configdata.get('steamcmd', 'steamcmd')
    logger.info(f'Steamcmd will run as {steamcmd}')

    installdir = configdata.get('installdir', None)
    if installdir is None:
        logger.info(f'No installdir set in {configfilename}.  Defaulting to current directory.')
        installdir = '.'

    checkinterval = configdata.get('checkinterval', 10)

    global gamecommand
    gamecommand = ['ping', '-t', 'www.google.com'] if sys.platform.startswith('win32') else ['ping', 'www.google.com']

    # Load the command line arguments as the game executable
    # TODO need to handle nothing being passed here
    if len(sys.argv) > 1:
         gamecommand = sys.argv[1:]

    # Store last checked time
    lastupdatecheck = time.time()
    logger.info(f'Saved last checked time as {time.ctime(lastupdatecheck)}.  Attempting initial game update.')

    # Update the game for first run
    updategame(steamcmd, installdir, appid, steamcmdextras)

    logger.info(f'Game updated.  Starting game using {" ".join(gamecommand)}.')
    gameprocess = startgameprocess(gamecommand)

    # testlife = 15
    # logger.info(f'Sleeping for {testlife}s')
    # time.sleep(testlife)
    # stopgameprocess(gameprocess)

    logger.info(f"Scheduling update process to run at {checkinterval} minute intervals")
    time.sleep(checkinterval * 60)
    while True:
        updatetime = time.time()
        logger.info(f'Running update check at {time.ctime(updatetime)} - Last Check/Update At {time.ctime(lastupdatecheck)}')
        latestbuildtime = getlatestbuildtime(appid, branch)

        if lastupdatecheck < latestbuildtime:
            logger.info(f'Latest build time of {time.ctime(latestbuildtime)} is after last check.  Update needed.  Stopping server.')
            stopgameprocess(gameprocess)
            logger.info(f'Updating game using steamcmd.')
            updategame(steamcmd, installdir, appid, steamcmdextras)
            logger.info(f'Game updated.  Starting game using {" ".join(gamecommand)}.')
            gameprocess = startgameprocess(gamecommand)
            lastupdatecheck = latestbuildtime
        else:
            logger.info(f'Latest build time of {time.ctime(latestbuildtime)} is before last check.  No update needed.  Checking game process ({gameprocess.pid}) is still running')
            lastupdatecheck = updatetime
            gameprocess.poll()

            if gameprocess.returncode is not None:
                logger.warning(f'Game process has exited since last check.  Restarting game using {" ".join(gamecommand)}.')
                gameprocess = startgameprocess(gamecommand)

        time.sleep(checkinterval * 60)


if __name__ == "__main__":
    main()
