#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from logging import getLogger

import application
import tcp

_CMD_KEY_WHITEBOARD = "whiteboard"
_CMD_KEY_STETHOSCOPE = "stethoscope"

_CMD_KEY_OPERATION = "operation"
_OPERATION_OPEN = "open"
_OPERATION_CLOSE = "close"
_OPERATION_CLICK = "click"

_CMD_KEY_DISPLAY = "display"

_CMD_KEY_URL = "url"
_CMD_KEY_BY = "by"
_CMD_KEY_ID = "id"

# ##############################################################################
# white board
# ##############################################################################
ONLINEMED_WHITEBOARD_URL = application.configs.get('TCU', 'ONLINEMED_WHITEBOARD_URL', fallback="cubemed.hosoya.onlinemed.biz:8088")
ONLINEMED_WHITEBOARD_MODE = application.configs.get('TCU', 'ONLINEMED_WHITEBOARD_MODE', fallback="patient")
# ##############################################################################
# stethoscope
# ##############################################################################
ONLINEMED_STETHOSCOPE_URL = application.configs.get('TCU', 'ONLINEMED_STETHOSCOPE_URL', fallback="patient.cubemed.hosoya.onlinemed.biz/stethoscope")



logger = getLogger(__name__)

class Whiteboard(object) :

  def __init__(self, address, port
                , *
                , url=ONLINEMED_WHITEBOARD_URL
                , mode=ONLINEMED_WHITEBOARD_MODE
                ) :
    super().__init__()

    self._addr = address
    self._port = port
    self._url = url
    self._mode = mode

  def __enter__(self) :
    return self.open()

  def __exit__(self, exception_type, exception_value, traceback) :
    self.close()

  def _send(self, command) :
    with tcp.Client(self._addr, self._port) as client :
      client.send(json.dumps(command))

  def open(self, reservation_id) :
    command = {
      _CMD_KEY_WHITEBOARD : {
        _CMD_KEY_OPERATION : _OPERATION_OPEN,
        _CMD_KEY_URL : f"https://{self._url}/"
                      + f"?reservation_id={reservation_id}"
                      + f"&mode={self._mode}"
      }
    }
    logger.info(f"Whiteboard open {command}")
    self._send(command)
    logger.info(f"Whiteboard opened")

  def close(self) :
    command = {
      _CMD_KEY_WHITEBOARD : {
        _CMD_KEY_OPERATION : _OPERATION_CLOSE
      }
    }
    logger.info(f"Whiteboard close {command}")
    self._send(command)
    logger.info(f"Whiteboard closed")

  # 0:deactive current display device
  # 1:stethoscope active
  # 2:touchpanel active
  def function(self, reservation_id, status) :
    if isinstance(status, int) :
      if status == 0 :
        self.open(reservation_id)
      elif status == 1 :
        command = {
          _CMD_KEY_STETHOSCOPE : {
            _CMD_KEY_OPERATION : _OPERATION_OPEN,
            _CMD_KEY_URL : f"https://{ONLINEMED_STETHOSCOPE_URL}"
                          + f"?reservation_id={reservation_id}"
          }
        }
        logger.info(f"Whiteboard function {command}")
        self._send(command)
      elif status == 2 :
        self.open(reservation_id)

  def button(self, reservation_id, status) :
    command = {
      _CMD_KEY_STETHOSCOPE : {
        _CMD_KEY_OPERATION : _OPERATION_CLICK,
        _CMD_KEY_URL : f"https://{ONLINEMED_STETHOSCOPE_URL}"
                      + f"?reservation_id={reservation_id}"
      }
    }
    logger.info(f"Whiteboard function {command}")
    self._send(command)



def open( address, port, reservation_id
          , *
          , url=ONLINEMED_WHITEBOARD_URL, mode=ONLINEMED_WHITEBOARD_MODE) :

  wb = Whiteboard( address, port, url=url, mode=mode)
  wb.open(reservation_id)
  return wb

def close( address, port) :
  wb = Whiteboard( address, port)
  wb.close()


if __name__ == '__main__':
  import argparse
  import configparser

  p = argparse.ArgumentParser()
  p.add_argument("--open", "-o", action="store_true")
  p.add_argument("--close", "-c", action="store_true")
  p.add_argument("--id", "-i", type=int, default=0)

  args = p.parse_args()

  config_ini = configparser.ConfigParser()
  config_ini.read("config.ini", encoding='utf-8')
  varClientIP = config_ini.get('CLIENT', 'IP')
  varClientPort = int(config_ini.get('CLIENT', 'PORT'))
  print(varClientIP)
  print(varClientPort)


  if args.open :
    open(varClientIP, varClientPort, args.id)
  elif args.close :
    close(varClientIP, varClientPort)
