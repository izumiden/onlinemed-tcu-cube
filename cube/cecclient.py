#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from logging import getLogger

# import asyncio
import subprocess
import time

CEC_LOG_ERROR   = 1
CEC_LOG_WARNING = 2
CEC_LOG_NOTICE  = 4
CEC_LOG_TRAFFIC = 8
CEC_LOG_DEBUG   = 16
CEC_LOG_ALL     = 31

logger = getLogger(__name__)

def _cec_client_sync(command, address=0, loglevel=CEC_LOG_ERROR) :

  stdin = f'{command} {address}'.encode('utf-8')

  with subprocess.Popen(
    ['cec-client', '-s', '-d', f'{loglevel}']
      , stdin=subprocess.PIPE
        , stdout=subprocess.PIPE
          ) as pcecclient :

    communicate = pcecclient.communicate(stdin)[0].decode('utf-8')
    logger.debug(f'---\n{communicate}')
    logger.debug('---')
    return communicate

# async def _cec_client_async(command, address=0, loglevel=CEC_LOG_ERROR) :
#
#   stdin = f'{command} {address}'.encode('utf-8')
#
#   pcecclient = await asyncio.create_subprocess_shell(
#     f'cec-client -s -d {loglevel}'
#     , stdin=asyncio.subprocess.PIPE
#     , stdout=asyncio.subprocess.PIPE
#     )
#
#   stdout, stderr = await pcecclient.communicate(stdin)
#   communicate = stdout.decode('utf-8')
#   logger.debug(f'---\n{communicate}')
#   logger.debug('---')
#   return communicate

def _cec_client(command, address=0, loglevel=CEC_LOG_ERROR) :
  # return await _cec_client_async(command, address, loglevel)
  return _cec_client_sync(command, address, loglevel)

def power_status( address=0, loglevel=CEC_LOG_ERROR) :
  communicate = _cec_client('pow', address)
  for line in communicate.split('\n') :
    logger.debug(line)
    if line.startswith('power status:') :
      power_status = line.split(':')[1].strip()
      logger.info(f'cec pow status:{power_status}')
      if power_status == 'on' :
        return True
  return False

def active( address=0, loglevel=CEC_LOG_ERROR) :
  communicate = _cec_client('as', address)
  # for line in communicate.split('\n') :
  #   logger.debug(line)
  #   # if line.startswith('power status:') :
  #   #   power_status = line.split(':')[1].strip()
  #   #   logger.info(power_status)
  #   #   if power_status == 'on' :
  #   #     return True
  return True

def on( address=0, loglevel=CEC_LOG_ERROR) :
  communicate = _cec_client('on', address)
  # for line in communicate.split('\n') :
  #   logger.debug(line)
  #   # if line.startswith('power status:') :
  #   #   power_status = line.split(':')[1].strip()
  #   #   logger.info(power_status)
  #   #   if power_status == 'on' :
  #   #     return True
  return True

def standby( address=0, loglevel=CEC_LOG_ERROR) :
  communicate = _cec_client('standby', address)
  # for line in communicate.split('\n') :
  #   logger.debug(line)
  #   # if line.startswith('power status:') :
  #   #   power_status = line.split(':')[1].strip()
  #   #   logger.info(power_status)
  #   #   if power_status == 'on' :
  #   #     return True
  return True

if __name__ == '__main__':

  import argparse
  import logging

  logging_stream_handler = logging.StreamHandler()
  logger.addHandler(logging_stream_handler)

  argp = argparse.ArgumentParser()
  argp.add_argument('command', nargs='+', type=str, help='command')

  # argg = argp.add_mutually_exclusive_group(required=True)
  # argg.add_argument("--on",  help="tv control on",  action="store_true")
  # argg.add_argument("--off", help="tv control off", action="store_true")

  argp.add_argument("--log", type=str, default='DEBUG')
  args = argp.parse_args()

  LOGLEVEL = args.log.upper()
  loglevel = getattr(logging, LOGLEVEL, None)
  if isinstance(loglevel, int) :
    logger.setLevel(loglevel)

  def main(args) :
    argn = len(args.command)
    if 0 < argn :
      try :
        logger.info(f'{args.command}')

        command = args.command[0]
        address = 0
        if 1 < argn :
          s = args.command[1]
          if s.isdigit() :
            address = int(s)

        logger.info(f'cec-client {command} {address}')

        if command == 'status' :
          power_status(address)
        elif command == 'active' :
          active(address)
        elif command == 'on' :
          on(address)
        elif command == 'standby' :
          standby(address)
        else :
          _cec_client(command, address)

      except :
        logger.exception('')

  main(args)
