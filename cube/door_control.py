# -*- coding: utf-8 -*-
from logging import getLogger
import time
from threading import RLock, Event

from tcu.relay.constant import *
from tcu.relay import client
from tcu.relay import Switches

from configs import TCUPI_RELAY_HOST, TCUPI_RELAY_PORT, LOCK_PULSE_TIME, LOCK_PULSE_DELAY, DISTANCE_INTERVAL, DOOR_TIME_TO_LOCK_FROM_CLOSING
from cube import cube_thread

logger = getLogger(__name__)


class DoorControlException(Exception):
  pass


class TimeoutException(DoorControlException):
  pass


class OpenTimeoutException(TimeoutException):
  pass


class LockTimeoutException(TimeoutException):
  pass


class Controller(cube_thread):

  _instance = None

  @classmethod
  def getInstance(cls, timeout=180.0):
    if cls._instance is None:
      cls._instance = cls(timeout)
    return cls._instance

  @property
  def timeout(self) -> float:
    return self._timeout

  @property
  def islock(self) -> bool:
    with self._resource_rlock:
      return self._electronic_lock_status

  def __init__(self, timeout=180.0):

    if Controller._instance is not None:
      raise Exception(f"This class '{__class__}' is a singleton!")
    Controller._instance = self

    super().__init__(name="door_control")

    self._is_timeout = False
    self._timeout = timeout

    self.on_timeover = None

    self.on_open_event = Event()
    self.on_close_event = Event()

    self._resource_rlock = RLock()

    self._electronic_lock_status = False

  def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
    if self._resource_rlock.acquire(blocking, timeout) :
      logger.debug(f"Controller.resource acquire.")
      return True
    return False

  def release(self):
    try :
      self._resource_rlock.release()
      logger.debug(f"Controller.resource release.")
    except :
      logger.exception("Controller.resource release has occuered exception.")

  def _engage_lock(self):
    """電子錠を施錠する
    """
    with self._resource_rlock:
      logger.debug(f"Controller._engage_lock()")
      resp_msg = client.door_lock(
          (TCUPI_RELAY_HOST, TCUPI_RELAY_PORT), LOCK_PULSE_TIME, LOCK_PULSE_DELAY)
      logger.debug(f"door_lock rest resp:{resp_msg}")
      self._electronic_lock_status = False

  def _disengage_lock(self):
    """電子錠を解錠する
    """
    with self._resource_rlock:
      logger.debug(f"Controller._disengage_lock()")
      resp_msg = client.door_unlock(
          (TCUPI_RELAY_HOST, TCUPI_RELAY_PORT), LOCK_PULSE_TIME, LOCK_PULSE_DELAY)
      logger.debug(f"door_unlock resp:{resp_msg}")
      self._electronic_lock_status = True

  def disengage_lock(self):
    """電子錠を解錠する
    """
    if not self._do:
      try:
        # Door unlock
        stime = time.time()
        logger.info(f"unlock door.(by door_control thread)")
        self._disengage_lock()
        logger.info(f"door was unlocked at {time.time()-stime:0.3f}")
        self.lock_door_on_close()
      except:
        raise

  def lock_door_on_close(self):
    if not self._do:
      # Door lock
      self.start()

  def set_timeout(self, timeout:float) -> None:
    if type(timeout) is not float:
      tout = float(timeout)
    else :
      tout = timeout

    if tout <= 0.0:
      raise ValueError(
          f'timeout must be a float greater than 0.0.{type(timeout)}: {timeout}')
    self._timeout = tout

  def is_timeout(self):
    return self._is_timeout

  def clear_open_flag(self):
    self.on_open_event.clear()

  def is_opened(self):
    self.on_open_event.is_set()

  def wait_for_open(self, timeout: float | None = None):
    if self.on_open_event.wait(timeout) :
      if self.is_timeout():
        raise OpenTimeoutException(
            f"The open process did not finish within the given time.")

  def clear_close_flag(self):
    self.on_close_event.clear()

  def is_closed(self):
    self.on_close_event.is_set()

  def wait_for_close(self, timeout: float | None = None)->bool:
    if self.on_close_event.wait(timeout) :
      if self.is_timeout() :
        raise LockTimeoutException(
            f"The close process did not finish within the given time.")

  def _call_event_on_open(self):
    self.on_close_event.clear()
    self.on_open_event.set()

  def _call_event_on_close(self):
    self.on_open_event.clear()
    self.on_close_event.set()

  def run(self):

    self.on_open_event.clear
    self.on_close_event.clear

    is_opend = False
    self._do = True
    self._is_timeout = False

    is_lock = False
    time_door_close = 0

    try:
      logger.debug(f'door control run {self}')
      stime = time.time()

      while self._do:
        # interval is 100 milliseconds
        time.sleep(DISTANCE_INTERVAL)
        tm = time.time()

        if not is_opend:
          if is_open():
            is_opend = True
            self._call_event_on_open()
            logger.debug(f"door is opened {tm-stime:0.3f}")
          else:
            if self._timeout < tm - stime:
              logger.info(f"door unlock time is over :{tm-stime:0.3f}")
              self._engage_lock()
              logger.info(f"door was unlocked at {time.time()-stime:0.3f}")
              if is_open():
                  logger.info(f"door unlock time is over :{tm-stime:0.3f}")
                  self._disengage_lock()
                  logger.info(f"door was unlocked at {time.time()-stime:0.3f}")
              else:
                self._is_timeout = True
                self._call_event_on_open()
                self._call_event_on_close()
                logger.info(
                    f"door call event on_close {time.time()-stime:0.3f}")
                break
        else:
          if is_open():
            # clear door close time
            time_door_close = 0
            if is_lock:
              # Door unlock
              logger.info(f"unlock door at {tm-stime:0.3f}")
              self._disengage_lock()
              logger.info(f"door was unlocked at {time.time()-stime:0.3f}")
              is_lock = False
          else:
            # door is closeed
            if time_door_close:
              if DOOR_TIME_TO_LOCK_FROM_CLOSING < tm - time_door_close:
                logger.info(f"lock door at {tm-stime:0.3f}")
                self._engage_lock()
                is_lock = True
                logger.info(f"door was locked at {time.time()-stime:0.3f}")
                if is_open():
                  logger.info(f"door unlock time is over :{tm-stime:0.3f}")
                  self._disengage_lock()
                  logger.info(f"door was unlocked at {time.time()-stime:0.3f}")
                  is_lock = False
                else:
                  self._call_event_on_close()
                  logger.info(
                      f"door call event on_close {time.time()-stime:0.3f}")
                  break
            else:
              time_door_close = tm
              logger.info(f"door is closed at {time_door_close-stime:0.3f}")
          # : if door_is_open()
        # : if not is_opend
      # : while self._do
    except:
      logger.exception('door control thread exception.')

    finally:
      if self._do :
        self._do = False
      else :
        self._is_timeout = True
        self._call_event_on_open()
        self._call_event_on_close()

    logger.info(f"_door_control run fin. {time.time()-stime:0.3f}")
  # : def run(self)


def create_controller(timeout: float | None = None) -> Controller:
  return Controller.getInstance(timeout)


def get_controller() -> Controller:
  return Controller.getInstance()


def set_timeout(timeout: float)->None:
  controller = Controller.getInstance()
  controller.set_timeout(timeout)


def is_timeout()->bool:
  controller = Controller.getInstance()
  return controller.is_timeout()


def lock_door_on_close():
  controller = Controller.getInstance()
  return controller.lock_door_on_close()


def stop():
  controller = Controller.getInstance()
  return controller.stop()


def is_close() -> bool:
  switches = Switches.getInstance()
  try:
    door_switch = switches[SW_1]
    return bool(door_switch)
  except KeyError:
    return False


def is_open() -> bool:
  return not is_close()

