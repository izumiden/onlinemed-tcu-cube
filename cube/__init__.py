# -*- coding: utf-8 -*-
__version__ = '0.1.1'

from logging import getLogger
import os
import threading

from .constant import *

__all__ = ['application', 'configs']


logger = getLogger(__name__)

#
# 環境変数 編集
#
if os.getenv('PIGPIO_ADDR') is not None:
  print(f'PIGPIO_ADDR : {os.environ["PIGPIO_ADDR"]}')

from dotenv import load_dotenv
load_dotenv(".env")
if os.getenv('PIGPIO_ADDR') is not None:
  print(f'load_dotenv->PIGPIO_ADDR : {os.environ["PIGPIO_ADDR"]}')

if os.getenv('PIGPIO_ADDR') is None:
  os.environ['PIGPIO_ADDR'] = TCU_HOSTNAME
  print(f'PIGPIO_ADDR : {os.environ["PIGPIO_ADDR"]}')


#
# パッケージ変数 定義
#



class cube_thread(object):

  def __init__(self, name: str | None = None):
    super().__init__()
    self._name = name
    self._thread = None
    self._do = False

  def __del__(self):
    self.stop()
    self.join()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.stop()
    self.join()
    logger.info(
        f"exit self {self} exc_type {exc_type} exc_val {exc_val} exc_tb {exc_tb}")

  def run(self):
    pass

  def start(self, args=(), kwargs={}, *, daemon=None):
    if self._thread is not None:
      if self._thread.is_alive():
        return
    self._thread = threading.Thread(
        target=self.run, name=self._name, args=args, kwargs=kwargs, daemon=daemon)
    self._thread.start()

  def stop(self):
    self._do = False

  def join(self):
    if self._thread is not None:
      if self._thread.is_alive():
        self._thread.join()

  def is_alive(self):
    if self._thread is not None:
      if self._thread.is_alive():
        return True
    return False
