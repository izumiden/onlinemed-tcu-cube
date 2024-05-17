# -*- coding: utf-8 -*-
import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
import time
from threading import Thread

import tcu.client

from .configs import *

logger = getLogger(__name__)


class DistanceSensor:
  """"""
  def __init__(self, interval, period):
    """"""
    # Check the inputs
    if not isinstance(interval, (int, float)):
      raise TypeError("interval should be a number.")
    if interval <= 0:
      raise ValueError("interval should be a positive integer.")

    if not isinstance(period, (int, float)):
      raise TypeError("period should be a number.")
    if period <= 0:
      raise ValueError("period should be a positive integer.")

    self._interval = interval
    self._window_size = divmod(period, interval)
    self._result = False

  async def get_distance(self, host=None, port=None):
    """"""
    if host is None:
      host = TCUPI_DAEMON_HOST
    if port is None:
      port = TCUPI_DAEMON_PORT

    _, distance = tcu.client.request_async("distance", address=(host, port))
    return distance

  async def _check(self, threshold, presence, timeout, host=None, port=None):
    """"""
    # Check the inputs
    if not isinstance(threshold, (int, float)):
      raise TypeError("threshold should be a number.")
    if threshold <= 0:
      raise ValueError("threshold should be a positive number.")

    if timeout is not None:
      if not isinstance(timeout, (int, float)):
        raise TypeError("timeout should be a number.")
      if timeout <= 0:
        raise ValueError("timeout should be a positive number.")

    start_time = time.time()
    values = deque()
    sum = 0

    while True:
      if timeout and (time.time() - start_time) >= timeout:
        return False

      distance = await self.get_distance(host, port)

      values.append(distance)
      sum += distance

      if len(values) > self._window_size:
        sum -= values.popleft()

      if len(values) == self._window_size:
        moving_average = sum / self._window_size
        if moving_average != threshold :
          if (moving_average > threshold) == presence:
            return True

      await asyncio.sleep(self._interval)

  def start_check(self, threshold, presence, callback=None, timeout=None, host=None, port=None):
    """"""
    def start_loop(threshold, presence, callback, timeout, host, port):
      """"""
      loop = asyncio.new_event_loop()
      result = loop.run_until_complete(
          self._check(threshold, presence, callback, timeout, host, port))
      if callback:
          callback(result)
      return result

    if callback is not None:
      t = Thread(target=start_loop, args=(
          threshold, presence, callback, timeout, host, port))
      t.start()
    else :
      return start_loop(threshold, presence, callback, timeout, host, port)

  def start_check_presence(self, threshold, callback=None, timeout=None, host=None, port=None):
    """"""
    self.start_check(threshold, True, callback, timeout, host, port)

  def start_check_absence(self, threshold, callback=None, timeout=None, host=None, port=None):
    """"""
    self.start_check(threshold, False, callback, timeout, host, port)

  def check_presence(self, threshold, timeout=None, host=None, port=None):
    """"""
    return self.start_check(threshold, True, None, timeout, host, port)

  def check_absence(self, threshold, timeout=None, host=None, port=None):
    """"""
    return self.start_check(threshold, False, None, timeout, host, port)

  async def async_check(self, threshold, presence, timeout=None, host=None, port=None):
    """"""
    return await self._check(threshold, presence, timeout, host, port)

  async def async_check_presence(self, threshold, timeout=None, host=None, port=None):
    """"""
    return await self.async_check(threshold, True, timeout, host, port)

  async def async_check_absence(self, threshold, timeout=None, host=None, port=None):
    """"""
    return await self.async_check(threshold, False, timeout, host, port)
