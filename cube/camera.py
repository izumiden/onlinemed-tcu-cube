#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import imghdr
import json
import os
import time
from typing import Any
from logging import getLogger

logger = getLogger(__name__)

PICAMERA = 0
USBCAMERA = 1


__default_image_path = '/tmp'
__default_image_name = 'image.png'
__default_resoW = 800
__default_resoH = 600
__default_timeout = 3.0

CONNECT_WAIT = 3.0
RETRY_WAIT_UNIT = 0.1

def free(path) :
  if os.path.isfile(path) :
    try :
      os.remove(path)
      logger.info(f"remove file {path}")
      return True
    except OSError as ose:
      logger.info(ose)
  elif os.path.isdir(path) :
    pass
  else :
    return True

  return False

def load_image(path)->Any:
  if os.path.isfile(path):
    # ファイルの拡張子を取得
    splitext = os.path.splitext(path)
    ext = splitext[-1].lstrip('.')
    # 画像ファイルの種類を取得
    imagetype = imghdr.what(path)
    logger.info(f"path {path} ext {ext} type {imagetype}")
    if ext == imagetype:
      with open(path, 'rb') as f:
        logger.info(f"readable {f.readable()} {path}")
        image = f.read()
        return image
  return b''

async def shoot_async(address, port, device
                    , *
                    , path : str | None = None
                    , fileName = __default_image_name
                    , resoW = __default_resoW
                    , resoH = __default_resoH
                    , timeout = __default_timeout
                    ) :

  if path :
    pathlist = os.path.split(path)
    logger.debug(f"shoot_async {pathlist} = os.path.split({path}) ")
    if pathlist[0] == '.':
      if len(pathlist) == 1:
        path = os.getcwd()
      elif len(pathlist) == 2 and not pathlist[1]:
        path = os.getcwd()
      else:
        path = os.path.join(os.getcwd(), pathlist[1:])
    elif pathlist[0] == '' :
      if pathlist[1] == '.':
        path = os.getcwd()
      else :
        path = os.path.join(os.getcwd(), path)

    if not os.path.isdir(path):
      try :
        os.makedirs(path)
      except :
        path = os.getcwd()
  else :
    path = os.getcwd()

  path = os.path.join(path, fileName)

  if free(path) :
    camera = {'select':device, 'resoW':resoW, 'resoH':resoH, 'file':path}
    message = json.dumps({"camera":camera})
    logger.info(f"camera Send {address}:{port} {message}")

    conn_etime = time.time() + CONNECT_WAIT
    conn_sleeptime = 0
    conn_try = 0
    while True:
      try:
        sttime = time.time()
        # reader, writer = await asyncio.wait_for(
        #                   asyncio.open_connection(address, port)
        #                   , timeout=1.0)
        reader, writer = await asyncio.open_connection(address, port)
        writer.write(message.encode('utf-8'))
        # 切断待ち
        if timeout and 0.0 < timeout:
          await asyncio.wait_for(reader.read(), timeout)
        else :
          await reader.read()
        logger.info(f"image shoot time {time.time()-sttime:0.3f}.")

        logger.info(f"read timeout {timeout}.")
        tm = time.time()
        if not timeout :
          tout = tm + 0.5
        else :
          tout = sttime + timeout
          if tout < tm + 0.5 :
            tout += 0.5
        while True :
          image = load_image(path)
          if image:
            return image
          if time.time() < tout :
            break
          await asyncio.sleep(0.1)
      except (OSError, ConnectionRefusedError):
        conn_try += 1
        conn_sleeptime += RETRY_WAIT_UNIT * conn_try
        if conn_etime <= time.time() + conn_sleeptime:
          logger.exception("camera.shoot_async(). connect timeout.")
          break
        asyncio.sleep(conn_sleeptime)
      except asyncio.TimeoutError:
        logger.exception(f"camera.shoot_async().timeout:{timeout}")
        break
  else :
    logger.info(f"free failed {path}")

  return b''

def shoot(address
        , port
        , device
        , *
        , path = None
        , fileName = __default_image_name
        , resoW = __default_resoW
        , resoH = __default_resoH
        , timeout = __default_timeout
        ) :
  return asyncio.run(
          shoot_async(address, port, device, path=path, fileName=fileName, resoW=resoW, resoH=resoH, timeout=timeout)
          )

if __name__ == '__main__':

  import argparse
  import logging
  import application
  import signal
  import sys
  # import base64

  def termed(signum, frame):
    # logger.info("SIGTERM!")
    logger.info("")
    sys.exit(0)

  # Terme
  signal.signal(signal.SIGTERM, termed)
  # Ctrl + c
  signal.signal(signal.SIGINT, termed)

  address = application.configs['CLIENT']['IP']
  port = int(application.configs['CLIENT']['PORT'])

  argp = argparse.ArgumentParser()
  argp.add_argument("-d", "--debug", help="debug log level", type=str, default="INFO")

  argg = argp.add_mutually_exclusive_group(required=False)
  argg.add_argument("--pi" , help="pi camera" , action="store_true")
  argg.add_argument("--usb", help="usb camera", action="store_true")

  argp.add_argument("--address", type=str, default=address)
  argp.add_argument("--port", type=str, default=port)
  argp.add_argument("-p", "--filepath", type=str, default=None)
  argp.add_argument("--filename", type=str, default="image.png")
  argp.add_argument("--resoW", type=int, default=800)
  argp.add_argument("--resoH", type=int, default=600)
  argp.add_argument("--timeout", type=float, default=0.0)

  args = argp.parse_args()

  LOGLEVEL = args.debug.upper()
  loglevel = getattr(logging, LOGLEVEL, None)
  if isinstance(loglevel, int) :
    logger.setLevel(loglevel)

  logging_stream_handler = logging.StreamHandler()
  logger.addHandler(logging_stream_handler)


  if args.usb :
    device = USBCAMERA
  else :
    device = PICAMERA

  path = args.filepath
  try :
    if not os.path.isdir(path) :
      os.makedirs(path)
  except :
    path = None

  logger.info(f"path {path}")
  img = shoot(args.address, args.port, device
            , path = path
            , fileName = args.filename
            , resoW = args.resoW
            , resoH = args.resoH
            , timeout=args.timeout)
  # img = shoot(address, port, USBCAMERA)
  imagetype = imghdr.what(None, h=img)
  logger.info(f"file type:{imagetype} size:{len(img)}.")
