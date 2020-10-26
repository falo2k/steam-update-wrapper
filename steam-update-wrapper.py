import sys
#from os import path
import os.path
import time
import json
import subprocess
import logging
from logging import handlers
from steam.client import SteamClient

configfilename = 'config.json'
logfile = 'steam-update-wrapper.log.txt'
lastupdatecheck = -1


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

def getlatestbuildtime(appid, buildname):
    """Get the last updated timestamp for the given appid and build name"""
    client = SteamClient()

    client.anonymous_login()

    result = client.get_product_info(apps=[appid])

    buildid = result['apps'][appid]['depots']['branches']['buildname']['buildid']
    timeupdated = result['apps'][appid]['depots']['branches']['buildname']['timeupdated']

    client.logout()

    return timeupdated

def startgameprocess():
    print('starting game')

def stopgameprocess():
    print('stopping game')

def updategame():
    print('updating game')

def parsebranch(extraflags):
    return 'public'

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

    checkinterval = configdata.get('checkinterval', 10)

    global gamecommand
    gamecommand = ['ping', '-t', 'www.google.com'] if sys.platform.startswith('win32') else ['ping', 'www.google.com']

    # Load the command line arguments as the game executable
    # TODO need to handle nothing being passed here
    if len(sys.argv) > 1:
         gamecommand = sys.argv[1:]

    logger.info(f'Game will be executed as: {gamecommand}')

    # Save arguments as process to run
    # Get branch from steamcmdextras
    # Store last checked time
    # Update game
    # Launch game
    # While true
    # Check for update vs last checked time
    # if update
    #   Kill game
    #   Update game
    #   Update last updated to steamcmd time
    #   Re-Launch game
    # Sleep for checkinterval


    logger.info(f"Scheduling update process to run every {checkinterval} minutes")


if __name__ == "__main__":
    main()
