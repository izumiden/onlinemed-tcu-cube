#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import errno
from logging import getLogger
import os
import sys
import time
from threading import Event
import usb1

import binascii
import nfc
import nfc.tag.tt3
import nfc.tag.tt4

import utils

logger = getLogger(__name__)

class Reader(utils.BaseThread):
  def __init__(self, on_connected = None, *, daemon: bool | None = None) -> None:
    logger.info(f'Reader.__init__(daemon:{daemon})')
    super().__init__(daemon=daemon)

    self._ready_event = Event()

    self.on_startup = None
    self.on_connected = None

    self.exception = None

    if on_connected :
      self.on_connected = on_connected

  def has_exception(self) -> bool :
    return True if self.exception is not None else False

  def is_ready(self) :
    return self._ready_event.is_set()

  def wait(self, timeout : float | None = None):
    return self._ready_event.wait(timeout)

  def run(self) -> None:
    logger.debug(f'Reader.run()')
    try:
      rdwr_option = {}
      if self.on_startup :
        rdwr_option['on-startup'] = self.on_startup
      if self.on_connected:
        rdwr_option['on-connect'] = self.on_connected

      # タッチ時のハンドラを設定して待機する
      while self.should_keep_running():
          try:
            with nfc.ContactlessFrontend('usb') as clf:
              logger.info(f'NFC ContactlessFrontend {rdwr_option}')
              self.exception = None
              self._ready_event.set()

              while True :
                result = clf.connect(
                    rdwr=rdwr_option,
                    terminate=lambda: not self.should_keep_running()
                    )
                if result :
                  logger.debug(f'NFC connected')
                else :
                  break
          except usb1.USBErrorAccess as e:
            if logger.level > logging.DEBUG:
              logger.error(f'USB Error: Access')
            else :
              logger.exception(f'USB Error: Access')
            self.exception = e
            time.sleep(1.0)
          except usb1.USBErrorNotSupported as e:
            if logger.level > logging.DEBUG:
              logger.error(f'USB Error: Not Supported Device.')
            else:
              logger.exception(f'USB Error: Not Supported Device.')
            self.exception = e
            time.sleep(1.0)
          except IOError as e:
            if e.errno == errno.ENODEV:  # No such device
              self.exception = e
              if logger.level > logging.DEBUG:
                logger.error(f'IO Error: No such device')
              else:
                logger.exception(f'IO Error: No such device')
              time.sleep(1.0)
            else:
              raise e
          finally :
            self._ready_event.clear()
    finally:
      if self.should_keep_running() :
        self.stop()
      logger.debug(f'Reader.fin()')


if __name__ == '__main__':

  import argparse
  import logging
  import os
  import signal
  import sys
  import application

  def termed(signum, frame):
    # logger.info("SIGTERM!")
    logger.info("")
    sys.exit(0)

  if os.name == 'posix' :
    if application.is_process(os.path.basename(__file__)):
      sys.exit(-1)
    # Terme
    signal.signal(signal.SIGTERM, termed)
    # Ctrl + c
    signal.signal(signal.SIGINT, termed)

  argp = argparse.ArgumentParser()
  argp.add_argument("-d", "--debug", help="debug log output",
                    action="store_true")
  argp.add_argument("--log", type=str, default='INFO')
  args = argp.parse_args()

  #
  # set log lebel
  #
  if args.debug:
    loglevel = logging.DEBUG
  else:
    loglevel = getattr(logging, args.log.upper(), None)

  if isinstance(loglevel, int) :
    logger.setLevel(loglevel)

  # ログ出力のフォーマットを作成
  logging_formatter = logging.Formatter(
      "%(asctime)s,%(name)s,%(levelname).3s,%(message)s")

  logging_stream_handler = logging.StreamHandler()
  logging_stream_handler.setFormatter(logging_formatter)

  logger.addHandler(logging_stream_handler)

  logger.info("Felica reader program start.")

  reader = Reader()

  def connected(tag):
    # # タグのIDなどを出力する
    logger.info(f"connected({tag})")
    logger.debug(type(tag))
    if isinstance(tag, nfc.tag.tt3.Type3Tag):
      logger.debug("tag is Type3Tag")
      try:
        idm = tag.identifier
        logger.debug(idm)
        idm = binascii.hexlify(idm).upper()
        logger.debug(idm.decode('utf-8'))
        # 内容を16進数で出力する
        logger.debug(f'  ' + '\n  '.join(tag.dump()))
      except nfc.tag.tt3.Type3TagCommandError:
        pass
      except Exception:
        logger.exception("")
    elif isinstance(tag, nfc.tag.tt4.Type4Tag):
      logger.info("tag is Type4Tag")
      try:
        # 内容を16進数で出力する
        logger.info("\n".join(["\t" + line for line in tag.dump()]))
      except Exception as e:
        logger.info("error: %s" % e)
    else:
      logger.debug("error: tag isn't Type3Tag")

    # return True  # カードが離れるまでに1回のみ
    return False  # カードが離れるまで繰り返し

  try :
    reader.on_connected = connected
    reader.start()

    while True :
      time.sleep(1.0)
  except KeyboardInterrupt:
    print('')
  finally :
    reader.stop()

    import threading
    for thread in threading.enumerate():
      if thread is threading.current_thread() :
        logger.info("current:")
      logger.info(thread)
