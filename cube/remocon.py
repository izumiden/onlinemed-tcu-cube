#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from logging import getLogger

import time

import application
import cecclient
import irrp

logger = getLogger(__name__)

_turnon_source = 'IR'
_turnon_wait = 0.0
_turnon_retry = 0.0
_turnoff_source = 'IR'
_turnoff_wait = 0.0
_turnoff_retry = 0.0
_cec_use = False


# ##############################################################################
# tv control
# ##############################################################################
_cec_use = application.configs.getboolean('TCU', 'TV_CONTROL_CEC', fallback=False)

# turn on
_turnon_source = application.configs.get('TCU', 'TV_TURNON_SOURCE', fallback='IR')
_turnon_wait = application.configs.getfloat('TCU', 'TV_TURNON_WAIT', fallback=0.0)
_turnon_retry = application.configs.getint('TCU', 'TV_TURNON_RETRY_NUM', fallback=1)

# turn off
_turnoff_source = application.configs.get('TCU', 'TV_TURNOFF_SOURCE', fallback='IR')
_turnoff_wait = application.configs.getfloat('TCU', 'TV_TURNOFF_WAIT', fallback=0.0)
_turnoff_retry = application.configs.getint('TCU', 'TV_TURNOFF_RETRY_NUM', fallback=1)

def init( turnon_source=_turnon_source
        , turnon_wait=_turnon_wait
        , turnon_retry=_turnon_retry
        #
        , turnoff_source=_turnoff_source
        , turnoff_wait=_turnoff_wait
        , turnoff_retry=_turnoff_retry
        #
        , cec_use=_cec_use
        ) :
  global _turnon_source
  global _turnon_wait
  global _turnon_retry
  global _turnoff_source
  global _turnoff_wait
  global _turnoff_retry
  global _cec_use

  _turnon_source = turnon_source
  _turnon_wait = turnon_wait
  _turnon_retry = turnon_retry
  _turnoff_source = turnoff_source
  _turnoff_wait = turnoff_wait
  _turnoff_retry = turnoff_retry
  _cec_use = cec_use

  logger.debug(f"--remocon init")
  logger.debug(f"  ├ turnon_source  :{_turnon_source}")
  logger.debug(f"  ├ turnon_wait    :{_turnon_wait}")
  logger.debug(f"  ├ turnon_retry   :{_turnon_retry}")
  logger.debug(f"  ├ turnoff_source :{_turnoff_source}")
  logger.debug(f"  ├ turnoff_wait   :{_turnoff_wait}")
  logger.debug(f"  ├ turnoff_retry  :{_turnoff_retry}")
  logger.debug(f"  └ cec_use        :{_cec_use}")

def on() :
  logger.debug(f"on turnon_source:{_turnon_source} cec_use:{_cec_use}")
  if _turnon_source == 'IR' :
    irrp.playback(['power'])
  elif _turnon_source == 'CEC' :
    if _cec_use :
      logger.debug(f"cecclient.on")
      cecclient.on()

def standby() :
  if _turnoff_source == 'IR' :
    irrp.playback(['power'])
  elif _turnoff_source == 'CEC' :
    if _cec_use :
      cecclient.standby()

def turnon(wait=0.0, retry=0) :
  logger.debug(f"--remocon turnon_tv")
  logger.debug(f"  ├ source  :{_turnon_source}")
  logger.debug(f"  ├ wait    :{wait}")
  logger.debug(f"  ├ retry   :{retry}")
  logger.debug(f"  └ cec_use U:{_cec_use}")

  try :
    for retry in range(retry+1) :
      logger.debug(f"count:{retry}")
      if _cec_use :
        if cecclient.power_status() :
          logger.debug(f"break {cecclient.power_status()}")
          break
      on()
      if not _cec_use :
        logger.debug(f"break cec_use:{_cec_use}")
        break
      if wait :
        time.sleep(wait)
      logger.debug(f"count end:{retry}")

    logger.debug(f"active")
    if _cec_use :
      cecclient.active()
  except :
    logger.exception("")

def turnoff(wait=0.0, retry=0) :
  logger.debug(f"--remocon turnoff_tv")
  logger.debug(f"  ├ source  :{_turnoff_source}")
  logger.debug(f"  ├ wait    :{wait}")
  logger.debug(f"  ├ retry   :{retry}")
  logger.debug(f"  └ cec_use :{_cec_use}")

  try :
    for retry in range(retry+1) :
      if _cec_use :
        if not cecclient.power_status() :
          break
      standby()
      if not _cec_use :
        break
      if wait :
        time.sleep(wait)
  except :
    logger.exception("")

# ##############################################################################
init()


# ##############################################################################
if __name__ == '__main__':

  import argparse
  import logging

  argp = argparse.ArgumentParser()
  argp.add_argument("--log", type=str, default='DEBUG')
  args = argp.parse_args()

  LOGLEVEL = args.log.upper()
  loglevel = getattr(logging, LOGLEVEL, None)
  if isinstance(loglevel, int) :
    logger.setLevel(loglevel)

  logging_stream_handler = logging.StreamHandler()
  logger.addHandler(logging_stream_handler)

  try :
    init()

    while True :
      turnon(1, 2)
      print('wait 10 ...')
      time.sleep(10)
      turnoff(1, 2)
      print('wait 10 ...')
      time.sleep(10)
  except :
    logger.exception('')
