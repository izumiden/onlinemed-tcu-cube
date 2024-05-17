#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections.abc import Iterable
from collections.abc import Mapping
import inspect
from logging import getLogger, DEBUG, INFO, WARNING, ERROR, CRITICAL
from threading import Thread
from threading import Event
from typing import Any
import sys

_CONFIG_FILE_EXTENSION = "config"

logger = getLogger(__name__)

class BaseThread(Thread) :

  @property
  def stopped_event(self):
    return self._stopped_event

  def __init__(self, args: Iterable[Any] = (), kwargs: Mapping[str, Any] | None = {}, *, daemon: bool | None = None) -> None:
    super().__init__(args=args, kwargs=kwargs, daemon=daemon)

    self._stopped_event = Event()
    
  def should_keep_running(self, timeout: float = 0.0):
    """Determines whether the thread should continue running."""
    if 0.0 < timeout :
      return not self._stopped_event.wait(timeout)
    else :
      return not self._stopped_event.is_set()

  def run(self) -> None:
    while True:
      if self.should_keep_running():
        # stop
        break

  def stop(self):
    self._stopped_event.set()

class Timer(BaseThread):
  def __init__(self, interval, target, oneshot: bool | None = ..., args: Iterable[Any] = ..., kwargs: Mapping[str, Any] | None = ..., *, daemon: bool | None = ...) -> None:
    super().__init__(daemon=daemon)

    self._timer_event = Event()
    self._interval = interval
    self._target = target
    self._oneshot = oneshot
    self._args = args
    self._kwargs = kwargs


  def run(self) -> None:
    while True :
      if self._timer_event.wait(self._interval) :
        self._timer_event.clear()
 
        if not self.should_keep_running():
          # stop
          break
        else :
          # reset
          pass
      else:
        self._target(*self._args, **self._kwargs)
        if self._oneshot :
          break
 

  def reset(self, interval:int | None = ...):
    if interval is not None :
      self._interval = interval
    self._timer_event.set()


  def stop(self):
    super().stop()
    self._timer_event.set()


class ReuseThread(object):

  def __init__(self):
    super().__init__()
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
    logger.debug(
        f"exit self {self} exc_type {exc_type} exc_val {exc_val} exc_tb {exc_tb}")

  def run(self):
    logger.debug(f'default run called')

  def start(self, args=(), kwargs={}, *, daemon=None):
    logger.debug(f'start args:{args} kwargs:{kwargs} daemon:{daemon}')
    if self.is_alive():
      return
    self._thread = Thread(target=self.run, args=args, kwargs=kwargs, daemon=daemon)
    self._thread.start()
    logger.debug(f'thread start')

  def stop(self):
    self._do = False

  def join(self):
    if self.is_alive():
      self._thread.join()

  def is_alive(self):
    if self._thread is not None:
      if self._thread.is_alive():
        return True
    return False

def has_attribute(ob, attribute):
    """
    :func:`hasattr` swallows exceptions. :func:`has_attribute` tests a Python object for the
    presence of an attribute.

    :param ob:
        object to inspect
    :param attribute:
        ``str`` for the name of the attribute.
    """
    return getattr(ob, attribute, None) is not None


def location(depth=0):
  frame = inspect.currentframe().f_back
  for i in range(depth) :
    frame = frame.f_back
  return frame.f_code.co_filename, frame.f_code.co_name, frame.f_lineno


def exception(logger=logger, msg=None, depth=0, level=ERROR):
  filename, co_name, f_lineno = location(depth+1)
  output = '\n' \
           'Exception\n' \
          f'  File "{filename}", line {f_lineno}, in {co_name}\n' \
          f'      {sys.exc_info()}\n'
  if msg:
    output += f'    {msg}\n'

  if level >= CRITICAL:
    logger.critical(output)
  elif level >= ERROR:
    logger.error(output)
  elif level >= WARNING:
    logger.warning(output)
  elif level >= INFO:
    logger.info(output)
  elif level >= DEBUG:
    logger.debug(output)


def load_configs(filename='*', *, extension: str | None = _CONFIG_FILE_EXTENSION, encoding='utf-8'):

  import configparser

  if isinstance(extension, str) :
    extension.strip()

  if extension :
    if '.' in filename :
      exe = filename.split('.')[-1]
      if extension != exe :
        filename += '.' + extension
    else :
      filename += '.' + extension

  configs = configparser.ConfigParser()
  return configs.read(filename, encoding=encoding)
