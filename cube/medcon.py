# -*- coding: utf-8 -*-
""" 診療に関する処理を管理、制御するパッケージ

      * authentication
"""
from logging import getLogger
import time
from threading import Thread, Timer, Event

from . import door_control
from . import medcube
from . import onlinemed
from . import portable
from . import remocon


from .constant import *
from .configs import *
from .onlinemed import Session
from .medcube import Cube

import tcu.client
import tcu.constant

logger = getLogger(__name__)


class _MedconThread(Thread):
  """"""
  _instance = None

  @classmethod
  def getInstance(cls, timeout=180.0):
    """"""
    if cls._instance is None:
      cls._instance = cls(timeout)
    return cls._instance

  def __init__(self, cube: Cube, session: Session, mode: str | None = None) -> None:
    """"""
    if _MedconThread._instance is not None:
      raise Exception(f"This class '{__class__}' is a singleton!")
    _MedconThread._instance = self

    self._stop_event = Event()
    self._cube = cube
    self._session = session
    self._access_mode = mode

    self._has_patient_entered = False

  def stop(self):
    self._stop_event.set()

  def run(self) -> None:

    try :
      if LIGHT_WITH:
        # light on
        medcube.light_on()

      if TV_CONTROL:
        remocon.turnon(TV_TURNON_WAIT, TV_TURNON_RETRY)

      if MODEL == MODEL_CUBE:
        t = time.time()
        logger.info(f"unlock door.(by cube.open())")
        door_controller = door_control.get_controller()
        door_controller.disengage_lock()
        logger.info(f"door was unlocked at {time.time()-t:0.3f}")

        if self._access_mode == 'continueus':
          # continueus access mode ではドアは開放した状態で、患者を順に入れ替えながら診察する。
          # そのため、openの時点で患者は入室している状態とする。
          self._has_patient_entered = True
        else:
          door_controller.lock_door_on_close()
          logger.info(f"lock door on close start.(by cube.open())")

          door_controller.wait_for_open()

          self._cube.wait_enter()

          self._cube.enter_wait()
      else:
        self._cube.wait_enter()

        self._cube.enter_wait()

      logger.info(
          f'on enter. reservation_id:{self.reservation_id} idm:{self.idm} doctor is ready:{self._is_doctor_ready}')
      # 患者が入室している状態に設定
      self._has_patient_entered = True
      # 入室が完了したら距離センサーを停止
      self._distance.stop()

      logger.info(f'onlinemed_client {self._session}')
      # 患者が入室したことをサーバへ通知
      self._session._client.patient_enter()

      # 医者が待機状態であれば、診察を開始する
      while True :
        if self._session:
          if self._cube.wait_for_doctor_ready(1/1000):
            break

        if self._stop_event.is_set() :
          return

      # 診察開始
      self._cube.consultation_start()

      try :
        while self._stop_event.is_set():
          if self._cube.wait_for_close_consultation(1/1000) :
            break
      finally:
        pass
    except:
      pass
    finally :
      pass

def start(session: Session):
  """"""
  medcon = _MedconThread(session)
  medcon.start()

  return medcon
