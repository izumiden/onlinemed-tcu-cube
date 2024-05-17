#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import binascii
import csv
from collections import deque
import configparser
import concurrent.futures
import json
from logging import getLogger
import nfc
import nfc.tag.tt3
import os
import socket
from threading import Thread, Lock, RLock, Event, current_thread
import time

import tcu
import tcu.client
import tcu.relay.client
from tcu.relay import Switch, Switches
from tcu.relay.constant import *

from . import camera
from . import door_control
from . import felica
from . import fwatchdog
from . import onlinemed
from . import portable
from . import remocon
from . import utils
from . import browser

from .configs import *
from .whiteboard import Whiteboard

from cube import cube_thread


logger = getLogger(__name__)



_g_cube = None

# remocon.init(
#           turnon_source=_TV_TURNON_SOURCE, turnon_wait=_TV_TURNON_WAIT, turnon_retry=_TV_TURNON_RETRY
#         , turnoff_source=_TV_TURNOFF_SOURCE, turnoff_wait=_TV_TURNOFF_WAIT, turnoff_retry=_TV_TURNOFF_RETRY
#         , cec_use=_TV_CONTROL_CEC
#         )


class MedCubeException(Exception):
  pass


class BusyError(MedCubeException):
  pass


class _SensorThread(Thread):

  def __init__(self, interval=10.0, *, wait: float | None = None, daemon: bool | None = False) -> None:

    self._timer_event = Event()

    self._interval = interval
    self._wait = wait if wait is not None else self._interval
    self._do = False

    super().__init__(daemon=daemon)

  def __dell__(self) :
    if self.is_alive() :
      self.stop()

  def run(self) :

    global onlinemed_client

    tcu.client.request("start", address=(TCUPI_DAEMON_HOST, TCUPI_DAEMON_PORT))
    try :
      self._do = True

      while self._do :

        if onlinemed_client :
          try :
            result, measure = tcu.client.request(
                "measure", address=(TCUPI_DAEMON_HOST, TCUPI_DAEMON_PORT))

            if result == tcu.constant.CODE_SUCCESS:
              onlinemed_client.measure(measure)
          except :
            logger.error("exception occuered by _sensor_thread.run().")
            logger.exception(f"location:{utils.location()}")
        self._timer_event.wait(self._interval)

    finally :
      tcu.client.request("stop", address=(
          TCUPI_DAEMON_HOST, TCUPI_DAEMON_PORT))

  def kill(self):
    self._do = False
    self._timer_event.set()

  def stop(self) :
    self.kill()
    self.join()

from cube import cube_thread

class _DistanceSensor(cube_thread):
  """ 距離センサー
  """
  @property
  def wait_to_enter(self) :
    """"""
    return True if 0.0 < self._threshold else False

  @property
  def wait_to_leave(self) :
    """"""
    return True if 0.0 < self._leave_threshold else False

  @property
  def is_awaiting_entry(self) -> bool :
    """"""
    return self._await_enter

  @property
  def is_awaiting_leave(self) -> bool:
    """"""
    return self._await_leave

  def __init__(self, interval, period, threshold, leave_threshold=None, *, ch=2):
    """"""
    super().__init__("DistanceSensor")

    self._await_enter = False
    self._is_enter = Event()
    self.on_enter = None

    self._await_leave = False
    self._is_leave = Event()
    self.on_leave = None

    self._timeout = 0
    self.on_timeout = None

    self._interval = interval
    self._period = period
    self._threshold = threshold
    self._leave_threshold = threshold if leave_threshold is None else leave_threshold

  def clear(self) :
    """"""
    self._is_enter.clear()
    self._is_leave.clear()

  def get(self) :
    """"""
    _, distance = tcu.client.request(
        "distance", address=(TCUPI_DAEMON_HOST, TCUPI_DAEMON_PORT))
    # logger.info(f"request distance result:{result} distance:{distance}")
    return distance

  def enter_wait(self, timeout:float|None=None) -> bool:
    """"""
    return self._is_enter.wait(timeout)

  def is_enter(self, timeout: float | None = None) -> bool:
    """"""
    return self._is_enter.is_set()

  def wait_enter(self, timeout=180.0):
    """"""
    self.stop()
    self.join()
    if self._threshold > 0.0 :
      self._await_enter = True
      self._is_enter.clear()
      if 0 < timeout :
        self._timeout = time.time() + timeout
      else :
        self._timeout = 0
      self.start()
    else :
      if self.on_enter :
        self.on_enter()

  def leave_wait(self, timeout:float|None=None) -> bool:
    """"""
    return self._is_leave.wait(timeout)

  def is_leave(self, timeout: float | None = None) -> bool:
    """"""
    return self._is_leave.is_set()

  def wait_leave(self, timeout=180.0) :
    """"""
    self.stop()
    self.join()

    self._await_leave = True
    self._is_leave.clear()
    if 0 < timeout :
      self._timeout = time.time() + timeout
    else :
      self._timeout = 0
    self.start()

  def time_on(self, timeout=180.0):
    """"""
    try :
      if 0 < timeout :
        self._timeout = time.time() + timeout
    except :
      pass

  def run(self) :
    """"""
    stime = time.time()

    mvavg_window_size, mod = divmod(self._period, self._interval)
    if mod :
      mvavg_window_size += 1
    mvavg_values = deque()
    mvavg_sum = 0
    mvavg = 0

    distance = self.get()

    try :
      self._do = True
      pre1sec = pre = tm = time.time()
      while self._do :
        # interval
        pre = tm
        tm = time.time()
        interval = self._interval - (tm - pre)
        if interval > 0.0 :
          time.sleep(interval)

        #
        # check is there
        #
        tm = time.time()
        #
        dist = self.get()
        try :
          # logger.debug(f"DistanceSensor run() distance:{distance} dist:{dist}")
          diff = abs(distance - dist)
          # calc moving averrage
          if mvavg_window_size <= len(mvavg_values) :
            val = mvavg_values.popleft()
            mvavg_sum -= val
          mvavg_values.append(diff)
          mvavg_sum += diff
          num = len(mvavg_values)
          if num :
            mvavg = mvavg_sum / num
          else :
            mvavg = mvavg_sum

          logstr = f"distance {dist} diff {diff}"
          logstr += f" is enter:{self._is_enter.is_set()} is leave:{self._is_leave.is_set()}"
          logstr += f" time {tm-stime:0.3f}"
          logstr += f" avg {mvavg:0.3f} num {num}"
          logoutput = False
          if 1.0 <= tm - pre1sec :
            pre1sec = tm
            logoutput = True
            logger.debug(logstr)
          # else :
          #   logger.debug(logstr)

          if mvavg_window_size <= num :
            if self._await_enter :
              logstr = f"distance is judge ? threshold enter {self._threshold} < value:{mvavg:0.3f}"
              if logoutput :
                logger.info(logstr)
              # else :
              #   logger.debug(logstr)

              if self._threshold == 0.0 or self._threshold < mvavg :
                if not self._is_enter.is_set() :
                  self._is_enter.set()
                  self._await_enter = False
                  logger.info("enter.")
                  if self.on_enter :
                    self.on_enter()
                  break

            if self._await_leave :
              logstr = f"distance is judge ? threshold value {mvavg:0.3f} < leave {self._leave_threshold}"
              if logoutput :
                logger.info(logstr)
              # else :
              #   logger.debug(logstr)

              if self._leave_threshold == 0.0 or mvavg < self._leave_threshold :
                if not self._is_leave.is_set() :
                  self._is_leave.set()
                  self._await_leave = False
                  logger.info("leave.")
                  if self.on_leave :
                    self.on_leave()
                  break
        finally :
          distance = dist

        if 0 < self._timeout < tm :
          logger.info(f'distance time is over timeout:{tm-stime:0.3f} ')
          self.stop()
          if self.on_timeout :
            self.on_timeout()
    finally :
      self._do = False
      self.clear()

# ##############################################################################
class Cube() :
  """"""

  _instance = None
  _create_lock = Lock()

  # ############################################################################
  @property
  def mode(self) :
    """"""
    return self._access_mode

  # ############################################################################
  @property
  def reservation_id(self) :
    """"""
    if self._session :
      return self._session.reservation_id
    return None

  @property
  def idm(self) :
    """"""
    if self._session :
      return self._session.idm
    return None

  @property
  def open_time(self) :
    """"""
    return self._open_time

  def __init__(self) :
    """"""
    with Cube._create_lock :
      if Cube._instance is not None:
        raise Exception(f"This class '{__class__}' is a singleton!")

      super().__init__()
      logger.info(f'_cube.__init__({type(self)}:{self})')

      self._distance =  _DistanceSensor(
          interval=DISTANCE_INTERVAL, period=DISTANCE_PERIOD, threshold=DISTANCE_IS_THERE_OF_CHANGE, leave_threshold=DISTANCE_IS_NOT_THERE_OF_CHANGE)

      self._distance.on_enter = self.on_enter
      self._distance.on_timeout = self.on_timeout

      self._has_patient_entered = False

      self._doctor_ready = Event()

      self._finish_event = Event()

      self._session = None

      self._access_mode = None

      self._open_time = None

      self._blowser = None

      self._sensor = None

      self._whiteboard = Whiteboard(TCUPI_CAMERA_HOST, TCUPI_CAMERA_PORT)

      self._resource_access = RLock()

      Cube._instance = self

  def stop(self) :
    """"""
    try :
      if self._session :
        self._session = None

      if self._sensor:
        self._sensor.stop()
    finally :
      try :
        door_control.stop()
      finally :
        try :
          self._distance.stop()
        finally :
          if self._whiteboard :
            self._whiteboard.close()

  def is_doctor_ready(self):
    return self._doctor_ready.is_set()

  def doctor_ready(self):
    return self._doctor_ready.set()

  def wait_for_doctor_ready(self, timeout:float|None=None)->bool:
    return self._doctor_ready.wait(timeout)

  def enter_wait(self):
    self._distance.enter_wait()

  def is_enter(self) :
    self._distance.is_enter()

  def wait_for_close_consultation(self, timeout: float | None = None) -> bool:
    return self._finish_event.wait(timeout)

  def is_closed_consultation(self) -> bool :
    return self._finish_event.is_set()

  # ############################################################################
  def wait_enter(self, timeout: float | None = None):
    self._distance.wait_enter()

  # ############################################################################
  def wait_leave(self, timeout: float | None = None):
    self._distance.wait_leave()

  # ############################################################################
  def on_enter(self) :
    with self._resource_access:
      logger.info(
          f'on enter. reservation_id:{self.reservation_id} idm:{self.idm} doctor is ready:{self._doctor_ready.is_set()}')
      # 患者が入室している状態に設定
      self._has_patient_entered = True
      # 距離センサーを停止
      self._distance.stop()

      logger.info(f'onlinemed_client {onlinemed_client}')
      if onlinemed_client :
        # 患者が入室したことをサーバへ通知
        onlinemed_client.patient_enter()

      # 医者が待機状態であれば、診察を開始する
      if self._session:
        if self._doctor_ready.is_set():
          # 診察開始
          self.consultation_start()

  def on_timeout(self) :
    if self._distance.is_awaiting_entry:
      terminate_consultation()

  # ############################################################################
  def open(self, session:onlinemed.Session, mode=None) :
    """ cube_openコマンド受信時の処理
    """
    if self._resource_access.acquire(timeout=10.0):
      try:
        if not self._session :

          open_time = time.time()

          logger.info(
              f'cube open reservation_id: {session.reservation_id} idm:{session.idm} mode:{mode} MODEL:{MODEL} time:{open_time:0.3f}')

          if LIGHT_WITH :
            # light on
            light_on()
          try:
            if TV_CONTROL :
              remocon.turnon(TV_TURNON_WAIT, TV_TURNON_RETRY)
            try :
              if MODEL == MODEL_CUBE:
                t = time.time()
                # 電子錠を解錠する。
                door_controller = door_control.get_controller()
                logger.debug(f"unlock door.(by cube.open())")
                door_controller.disengage_lock()
                logger.info(f"door was unlocked at {time.time()-t:0.3f}")

                if mode == 'continueus':
                  # continueus access mode ではドアは開放した状態で、患者を順に入れ替えながら診察する。
                  # そのため、openの時点で患者は入室している状態とする。
                  self._has_patient_entered = True
                else :
                    door_controller.lock_door_on_close()
                    logger.debug(f"lock door on close start.(by cube.open())")

                    try:
                      # ドアが開くのを待つ
                      if door_controller.wait_for_open() :
                        # 患者がまだ入室してなければ、入室を待つ。
                        if not self._has_patient_entered :
                          self.wait_enter()
                    except door_control.TimeoutException as e:
                      # ドアが規定時間内に開かなかったら、door_controller.wait_for_open()で
                      # TimeoutException例外が発生する。
                      # そのままraiseするので上位で処理を行うこと。
                      raise e

              # finish eventをクリア
              self._finish_event.clear()
              # 各種情報をセット
              self._session = session
              self._access_mode = mode
              self._open_time = open_time
            except :
              if TV_CONTROL :
                remocon.turnoff(TV_TURNOFF_WAIT, TV_TURNOFF_RETRY)
              raise
          except :
            if LIGHT_WITH:
              logger.info(f'light off... because {__class__}.open has occuert exception')
              light_off()
            raise
      finally :
        self._resource_access.release()
  # ############################################################################
  def web_open(self, reservation_id) -> None :
    """ web_openコマンド受信時の処理
    """
    with self._resource_access:
      logger.info(
          f'cube web open mode:{self.mode} reservation_id:{reservation_id}')
      # 医者が待機中の状態に設定
      self._doctor_ready.set()
      # 患者が入室済みであれば、診察を開始する。
      if self._has_patient_entered :
        # 診察開始
        self.consultation_start()
      #

  # ############################################################################
  def consultation_start(self) :
    """ 診察を開始する。
    """

    def open_whiteboard(wb: Whiteboard, reservation_id: object | None = None):
      """"""
      if isinstance(wb, Whiteboard):
        wb.open(reservation_id)

    def open_blowser(reservation_id: object | None = None):
      """"""
      url = f"https://{ONLINEMED_PATIENT_URL}?reservation_id={reservation_id}"
      logger.info(f"selenium browser open url {url}")
      return browser.open(
          url, kiosk=ONLINEMED_PATIENT_KIOSK, profile=r"t8qam33a.OnlineMed Cube")

    with self._resource_access :
      if self._session :
        #
        with concurrent.futures.ThreadPoolExecutor(thread_name_prefix="consultation_start") as executor:
          # ホワイトボードを開く
          future_open_whiteboard = executor.submit(open_whiteboard, self._whiteboard, self.reservation_id)
          try :
            if MODEL != MODEL_PORTABLE:
              if not self._blowser :
                # 通話画面を起動する
                future_open_blowser = executor.submit(
                    open_blowser, self.reservation_id)
                self._blowser = future_open_blowser.result()
          finally:
            future_open_whiteboard.result()

        # センサーデータアップロードスレッドを開始
        if not self._sensor:
          self._sensor = _SensorThread()
          self._sensor.start()

        logger.info(
            f"sensor start reservation_id:{self.reservation_id} server:{ONLINEMED_SERVER_URL}")

  # ############################################################################
  def close_consultation(self):
    """ 退出時の処理
    """
    logger.info(f'Cube.close_consultation() MODEL:{MODEL}')
    def _close_consultation_thread():
      """"""
      with self._resource_access :
        if MODEL == MODEL_CUBE:
          door_controller = door_control.get_controller()
          door_controller.acquire()
          try :
            if door_controller.is_alive():
              logger.debug(f'cube exit door is alive...')
              door_controller.clear_close_flag()
            else:
              logger.debug(f'cube exit door is not alive.')

              door_controller.clear_close_flag()
              door_controller.disengage_lock()
              door_controller.lock_door_on_close()
          finally:
            door_controller.release()

          logger.debug(f'wait for close at door controller...')
          # ドアが閉じるのを待つ
          door_controller.wait_for_close()
          # if MODEL == MODEL_CUBE:
        try :
          if self._distance.wait_to_leave:
            # 患者が退出するのを待つ
            logger.debug(f'wait leave...')
            self._distance.wait_leave()
            logger.debug(f'fin wait for door close.')
            self._distance.leave_wait()
          # 診察を完了する。
          self.finish_consultation()
        except door_control.LockTimeoutException:
          pass

    if not self._resource_access.acquire(blocking=False) :
      raise BusyError("deveice already in process.")

    try :
      thread = Thread(target=_close_consultation_thread, daemon=False)
      thread.start()
    finally:
      self._resource_access.release()

  def finish_consultation(self):
    """ 診察を完了したときの処理
    """

    def notify_patient_exit(cube: Cube) -> None:
      """ サーバーへ患者の退出を通知する。
      """
      logger.info(f'onlinemed_client {onlinemed_client}')

      if cube._sensor:
        logger.info(f'sensor stop...')
        cube._sensor.stop()
        cube._sensor.join()
      cube._sensor = None

      if onlinemed_client:
        onlinemed_client.patient_exit()
      # 患者の入室状態のフラグをクリア
      cube._has_patient_entered = False

    def terminate_whiteboard(cube: Cube):
      """ ホワイトボードを閉じる。
      """
      if cube._whiteboard:
        cube._whiteboard.close()

    def terminate_blowser(cube: Cube):
      """ ブラウザを閉じる
      """
      cube._doctor_ready.clear()

      if cube._blowser:
        cube._blowser.close()
      cube._blowser = None

    def terminate_tv(cube: Cube):
      """ テレビを消す
      """
      logger.info(
          f'remocon turnoff wait:{TV_TURNOFF_WAIT} retry:{TV_TURNOFF_RETRY}')
      remocon.turnoff(TV_TURNOFF_WAIT, TV_TURNOFF_RETRY)

    with self._resource_access:
      if self._session :

        logger.info(f'finish consultation. MODEL:{MODEL}')

        # 照明を消す。
        if LIGHT_WITH:
          logger.info(f'light off...')
          light_off()

        # 距離センサーを停止する。
        self._distance.stop()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="finish_consultation") as executor:
          # サーバーへ患者の退出を通知する。
          future_notify_patient_exit = executor.submit(notify_patient_exit, self)
          try :
            # ホワイトボードを閉じる
            future_terminate_whiteboard = executor.submit(
                terminate_whiteboard, self)
            try :
              # ブラウザを閉じる
              future_terminate_blowser = executor.submit(terminate_blowser, self)
              try :
                # TVを接続していれば、テレビを消す。
                if TV_CONTROL:
                  future_terminate_tv = executor.submit(terminate_tv, self)
                  future_terminate_tv.result()
              finally :
                future_terminate_blowser.result()
            finally :
              future_terminate_whiteboard.result()
          finally :
            future_notify_patient_exit.result()

        # 距離センサーの停止を待つ
        self._distance.join()

        # 各処理が正常終了したかを確認する。
        if not self._sensor :
          if not self._blowser :
            # 完了を確認して、セッションを終了する。
            self._session = None

            # UVライトを点灯して、室内を消毒する。
            if UVLITE_WITH and 0.0 < UVLITE_PERIOD:
              logger.info(f'uv light on ... wait {UVLITE_PERIOD} sec.')
              irradiate_uvlight(wait=UVLITE_WAIT_WHILE_LIT)

            terminate_consultation()
            logger.info(f'terminate onlinemed.')

            self._finish_event.set()

  # ############################################################################
  def reset(self) :
    """ 各パラメータをリセットする。
    * セッションの終了が正常に完了出来なかったときに診療を開始出来るよう暫定で入れた処理。
    * とりあえず動いてはいるがリセットの内容とタイミングが適切かは検討する必要がある。
    * そもそもセッションの終了処理を適切に行えれば不要な処理である。
    """
    self._session = None
    self._open_time = None

# class _cube() :   ############################################################


# ##############################################################################
#
# ##############################################################################
def on_cube_open(client: onlinemed.Client):
  logger.info(f"Felica authentication. reservationid {client.reservation_id}")
  if client.is_authenticated:
    if _g_cube.reservation_id :
      # 暫定処理。Cube.reset()のdocstringを参照のこと。
      if _g_cube.reservation_id != client.reservation_id :
        _g_cube.reset()

    if MODEL == MODEL_PORTABLE :
      portable.send_notify_id_message(
          client.reservation_id, PORTABLE_MESSAGE_FILE, PORTABLE_MESSAGE_TIMEOUT)
      mode = None
    else :
      # felica.csvにidmがある場合は、continueusモードで診療を行う。
      felica_list_file = 'felica.csv'
      felica_idm_list = []
      if os.path.isfile(felica_list_file) :
        try :
          with open(felica_list_file, newline='') as csvfile:
            csvreader_felica = csv.reader(csvfile, dialect='excel')
            for row in csvreader_felica:
              felica_idm_list.append(row[0])
        except :
          pass

      if client.idm in felica_idm_list :
        mode = 'continueus'
      else :
        mode = None
    try :
      _g_cube.open(client.session, mode)
    except door_control.Exception:
      # 正常終了しなかったら、
      terminate_consultation()
  else :
    terminate_consultation()
# def on_cube_open() :  ########################################################


def on_web_open(client: onlinemed.Client):
  if MODEL == MODEL_PORTABLE:
    portable.send_web_open_message(
        client.reservation_id, PORTABLE_MESSAGE_FILE, PORTABLE_MESSAGE_TIMEOUT)

  _g_cube.web_open(client.reservation_id)
# def on_web_open() : ##########################################################


def on_request_spo2(client: onlinemed.Client):
  if MODEL == MODEL_PORTABLE:
    filepath = SPO2CAMERA_IMAGE_SAVE_PATH
    logger.info(f'on_request_spo2 {filepath}')
    if os.path.isdir(filepath) :
      if filepath[-1] != '/':
        filepath += '/'
      logger.info(f'on_request_spo2 os.path.isdir {filepath}')
      filepath += SPO2CAMERA_IMAGE_FILE_NAME
      logger.info(f'on_request_spo2 file {filepath}')

      camera.free(filepath)
      try :
        portable.send_request_message(
            portable.MESSAGE_REQUEST_IMAGE, PORTABLE_MESSAGE_FILE, PORTABLE_MESSAGE_TIMEOUT)
        with fwatchdog.observe(
            filepath, False, PORTABLE_FILEWATCH_FIXED_TIME) as observer :
          observer.wait(SPO2CAMERA_IMAGE_GET_TIMEOUT)
          image = camera.load_image(filepath)
        client.res_spo2(image)
      finally :
        camera.free(filepath)
  else:
    image = camera_shoot(TCUPI_CAMERA_HOST, TCUPI_CAMERA_PORT
                        , camera.PICAMERA
                        , path = SPO2CAMERA_IMAGE_SAVE_PATH
                        , fileName = SPO2CAMERA_IMAGE_FILE_NAME
                        , resoW = SPO2CAMERA_IMAGE_RESO_W
                        , resoH = SPO2CAMERA_IMAGE_RESO_H
                        , timeout = SPO2CAMERA_IMAGE_GET_TIMEOUT
                        )
    client.res_spo2(image)

  logger.info(f"taken with pi camera {len(image)} {type(image)}")
# def on_request_spo2() : ######################################################


def on_request_usbcamera(client: onlinemed.Client):
  image = camera_shoot(TCUPI_CAMERA_HOST, TCUPI_CAMERA_PORT
                      , camera.USBCAMERA
                      , path = USBCAMERA_IMAGE_SAVE_PATH
                      , fileName = USBCAMERA_IMAGE_FILE_NAME
                      , resoW = USBCAMERA_IMAGE_RESO_W
                      , resoH = USBCAMERA_IMAGE_RESO_H
                      , timeout = USBCAMERA_IMAGE_GET_TIMEOUT
                      )
  logger.info(f"taken with usb camera {len(image)} {type(image)}")

  client.res_usbcamera(image)
# def on_request_shoot_usbcamera() :  ##########################################


def on_panel_function(client: onlinemed.Client, status):
  if MODEL == MODEL_PORTABLE:
    pass
  else :
    if _g_cube:
      if _g_cube._whiteboard :
        logger.info(f'on_panel_function reservation_id:{client.reservation_id} status:{status}')
        _g_cube._whiteboard.function(client.reservation_id, status)
# def on_panel_function() : ####################################################


def on_panel_func_button(client: onlinemed.Client, status):
  if MODEL == MODEL_PORTABLE:
    pass
  else :
    if _g_cube :
      if _g_cube._whiteboard :
        logger.info(f'on_panel_func_button reservation_id:{client.reservation_id} status:{status}')
        _g_cube._whiteboard.button(client.reservation_id, status)
# def on_panel_func_button() :  ################################################


def on_panel_func_stop(client: onlinemed.Client, status):
  global _g_cube
  if MODEL == MODEL_PORTABLE:
    pass
  else:
    if _g_cube:
      if _g_cube._whiteboard :
        logger.info(f'on_panel_func_stop reservation_id:{client.reservation_id} status:{status}')
        _g_cube._whiteboard.button(client.reservation_id, status)
# def on_panel_func_stop() : ####################################################


def on_panel_func_exit(client: onlinemed.Client, status):
  global _g_cube
  if MODEL == MODEL_PORTABLE:
    pass
  else:
    if _g_cube:
      if _g_cube._whiteboard :
        logger.info(f'on_panel_func_exit reservation_id:{client.reservation_id} status:{status}')
        _g_cube._whiteboard.function(client.reservation_id, 0)
# def on_panel_func_exit() :  ##################################################


# ##############################################################################
#
# ##############################################################################
onlinemed_client = None
def authentication(idm) :
  global onlinemed_client

  logger.info(f'cube authentication idm {idm} onlinemed_client:{onlinemed_client}')

  if MODEL == MODEL_PORTABLE :
    portable.send_start_message(
        idm, PORTABLE_MESSAGE_FILE, PORTABLE_MESSAGE_TIMEOUT)

  if not onlinemed_client:

    client = onlinemed.Client(ONLINEMED_SERVER_URL
                                        , ONLINEMED_SERVER_PORT
                                        , ONLINEMED_CUBE_ROOT_TOPIC
                                        , ONLINEMED_PATIENT_URL)

    client.on_request_cube_open = on_cube_open
    client.on_request_web_open = on_web_open
    client.on_request_shoot_spo2 = on_request_spo2
    client.on_request_shoot_usbcamera = on_request_usbcamera
    client.on_panel_function = on_panel_function
    client.on_panel_func_button = on_panel_func_button
    client.on_panel_func_stop = on_panel_func_stop
    client.on_panel_func_exit = on_panel_func_exit

    result, deviceid = tcu.client.request(
        "deviceid", address=(TCUPI_DAEMON_HOST, TCUPI_DAEMON_PORT))
    if result == tcu.constant.CODE_SUCCESS :
      client.device_id = deviceid

    onlinemed_client = client

  try :
    onlinemed_client.authentication(idm, timeout=10.0)
  except onlinemed.DoubleAuthError as e:
    logger.info(f"Onlinemed authentication is already in progress.\n{str(e)}")

# def authentication() : #######################################################


def terminate_consultation() :
  global onlinemed_client
  try :
    if onlinemed_client :
      onlinemed_client.disconnect()
  finally :
    onlinemed_client = None
# def authentication() : #######################################################


def light_on() :
  """"""
  logger.info("light on")
  rest_msg = tcu.relay.client.light_on((TCUPI_RELAY_HOST, TCUPI_RELAY_PORT))
  client_request(rest_msg)


def light_off() :
  """"""
  logger.info("light off")
  rest_msg = tcu.relay.client.light_off((TCUPI_RELAY_HOST, TCUPI_RELAY_PORT))
  client_request(rest_msg)


def uvlight_on() :
  """"""
  logger.info("uvlight on")
  rest_msg = tcu.relay.client.uvlight_on((TCUPI_RELAY_HOST, TCUPI_RELAY_PORT))
  client_request(rest_msg)


def uvlight_off() :
  """"""
  logger.info("uvlight off")
  rest_msg = tcu.relay.client.uvlight_off((TCUPI_RELAY_HOST, TCUPI_RELAY_PORT))
  client_request(rest_msg)


def irradiate_uvlight(*, wait=False) :
  """"""
  #
  def _irradiate_uvlight(period) :
    rest_msg = uvlight_on()
    client_request(rest_msg)
    start = time.time()
    while True :
      time.sleep(0.1)
      t = time.time()
      if period <= t - start :
        rest_msg = uvlight_off()
        client_request(rest_msg)
        break

  if wait :
    _irradiate_uvlight(UVLITE_PERIOD)
  else :
    thread = Thread(target=_irradiate_uvlight, args=(UVLITE_PERIOD,))
    thread.start()


def camera_shoot(address, port, device, path: str, fileName: str, resoW: int, resoH: int, timeout: float):
  """"""
  atask = camera.shoot_async(address, port, device, path=path, fileName=fileName,
                      resoW=resoW, resoH=resoH, timeout=timeout)
  _current_thread = current_thread()
  if _g_thread == _current_thread:
    _g_loop.run_until_complete(atask)
  else:
    if _g_loop:
      future = asyncio.run_coroutine_threadsafe(atask, _g_loop)
      future.result()


def on_open():
  """"""
  global _g_cube
  if _g_cube.mode == 'continueus' :
    pass
  else :
    door_control.get_controller().disengage_lock()


def on_close() :
  """"""
  pass


def on_switch() :
  """"""
  global _g_cube
  logger.info(f"on_switch {_g_cube}")
  if _g_cube :
    try :
      _g_cube.close_consultation()
    except BusyError as e:
      logger.info(f"Cube Busy. {type(e)}: {e}")


def felica_reader_on_connected(tag):
  """"""
  if isinstance(tag, nfc.tag.tt3.Type3Tag):
    binidm = binascii.hexlify(tag.identifier).upper()
    idm = binidm.decode('utf-8')
    try:
      if MODEL == MODEL_PANEL:
        if _g_cube.reservation_id:
          logger.info(
              f"Felica authentication idm:{idm} reservation_id:{_g_cube.reservation_id}.")
          if _g_cube.open_time:
            t = time.time()
            if t >= _g_cube.open_time + FELICA_SWITCH_INTERVAL:
              if _g_cube.idm and _g_cube.idm == idm:
                try :
                  _g_cube.close_consultation()
                except BusyError as e:
                  logger.info(f"Cube Busy. {type(e)}: {e}")
        else:
          authentication(idm)
      else:
        authentication(idm)
    # except TimeoutError as e:
    except socket.gaierror:
      pass
    except TimeoutError:
      pass
    except:
      logger.exception('')

  return True  # カードが離れるまでに1回のみ
# def felica_reader_on_connected(tag):


def on_changed_message_file(event):
  """"""
  logger.info(f'on_changed_message_file {event}')
  if utils.has_attribute(event, 'dest_path'):
    filepath = event.dest_path
  elif utils.has_attribute(event, 'src_path'):
    filepath = event.src_path
  else :
    return

  if os.path.isfile(filepath):
    try :
      configs = configparser.ConfigParser()
      configs.read(filepath)
      status = configs.get(portable.SECTION_MESSAGE, portable.KEY_STATUS, fallback=None)
      if status == portable.MESSAGE_STATUS_END :
        try:
          _g_cube.close_consultation()
        except BusyError as e:
          logger.info(f"Cube Busy. {type(e)}: {e}")
    finally :
      os.remove(filepath)


def client_notify_switch_status(sw_list: list = []):
  """"""
  logger.debug(f'client_notify_switch_status sw_list:{sw_list}.')
  switches = tcu.relay.Switches.getInstance()
  for sw in sw_list:
    try :
      notifySw = Switch(**sw)
    except (KeyError, ValueError):
      logger.exception('client_notify_switch_status error.')
      continue

    try:
      switch = switches[notifySw.swno]
      if switch != notifySw:
        switch.status = notifySw.status
        if switch.swno == SW_1:
          if door_control.is_open():
            logger.debug("client_notify_switch_status door on open.")
            on_open()
          else:
            logger.debug("client_notify_switch_status door on close.")
            on_close()
        elif switch.swno == SW_2:
          on_switch()
    except KeyError:
      switches.add_switch(notifySw)


_g_client_request_lock = Lock()
def client_request(message) :
  """"""
  if message:
    def thread(message):
      with _g_client_request_lock :
        try:
          json_data = json.loads(message)
          if SECTION_SW in json_data :
            sw_list = json_data[SECTION_SW]
            client_notify_switch_status(sw_list)

          if SECTION_RELAY in json_data :
            relay_list = json_data[SECTION_RELAY]

        except json.JSONDecodeError as e:
          logger.warning(e)
    th = Thread(target=thread, args=(message,))
    th.start()


async def client_connected(reader:asyncio.StreamReader, writer:asyncio.StreamWriter) :
  """"""
  try:
    message = b''

    peername = writer.get_extra_info('peername')
    sockname = writer.get_extra_info('sockname')
    try:
      message = await asyncio.wait_for(reader.read(1), 5.0)
      while not reader.at_eof():
        message += await asyncio.wait_for(reader.read(1), 0.1)
    except asyncio.TimeoutError :
      # logger.info(f"asyncio.TimeoutError")
      pass
    finally :
      writer.close()
      await writer.wait_closed()
    logger.info(f"address:{sockname} from {peername} message {message}.")

    if message :
      client_request(message.decode('utf-8'))
  except :
    logger.exception(f"client_connected has occerrd exception. peername:{peername} sockname:{sockname}.")

_g_serving_event = Event()
_g_async_event_stop = asyncio.Event()
_g_cube = None
_g_thread = None
_g_loop = None
async def start_async(host: str | None = None, port: int | None = None, loop: asyncio.AbstractEventLoop | None = None):
  """"""
  global _g_serving_event
  global _g_async_event_stop
  global _g_cube
  global _g_loop
  global _g_thread

  if not host :
    host = TCUPI_HOST

  if not port :
    port = TCUPI_PORT

  running_loop = None
  try :
    running_loop = asyncio.get_running_loop()
  except RuntimeError :
    pass

  if loop is None :
    try :
      loop = asyncio.get_running_loop()
    except RuntimeError :
      # アクティブなイベントループがない場合は、生成してイベントループをセットする。
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
  else :
    if not isinstance(loop, asyncio.AbstractEventLoop) :
      raise TypeError(f"loop should be a asyncio event loop. {loop}")

    try:
      running_loop = asyncio.get_running_loop()
      if running_loop != loop :
        raise RuntimeError(f"The loop is different than a running event loop.")
    except RuntimeError:
      # アクティブなイベントループがない場合は、イベントループをセットする。
      asyncio.set_event_loop(loop)


  async with await asyncio.start_server(client_connected, host, port) as async_server:

    _g_thread = current_thread()
    _g_loop = loop
    try :
      addr = async_server.sockets[0].getsockname()

      logger.info(f'Serving on {addr}')
      _callback_on_serving()
      _g_serving_event.set()
      try :
        door_control.create_controller(UNLOCK_TIMEOUT)
        logger.info('DoorController create Instance...')

        _g_cube = Cube()
        logger.info(f'_g_cube create Instance... {_g_cube}')
        try :
          Switches.getInstance()
          logger.info('Switches create Instance...')

          _felica_reader = felica.Reader(on_connected=felica_reader_on_connected)
          try:
            _felica_reader.start()

            _occured_exception = None
            while not _g_async_event_stop.is_set():
              try:
                resp = await tcu.relay.client.get_status_async((TCUPI_RELAY_HOST, TCUPI_RELAY_PORT), 20)
                if resp :
                  client_request(resp)
                  break
              except (ConnectionError, asyncio.TimeoutError) as e:
                if type(_occured_exception) != type(e) :
                  logger.warning(f"wait connect relay server... {type(e)}:{e}")
                _occured_exception = e
              except OSError as e:
                if os.name == 'nt':
                  if type(_occured_exception) != type(e):
                    logger.warning(
                        f"wait connect relay server... {type(e)}:errno {e.errno} winerrno {e.winerror} {e}")
                else :
                  if type(_occured_exception) != type(e):
                    logger.exception(
                        f"wait connect relay server... {type(e)}:errno {e.errno} {e}")
                _occured_exception = e
              except KeyboardInterrupt:
                raise
              except asyncio.exceptions.CancelledError:
                raise
              except Exception as e:
                if type(_occured_exception) != type(e):
                  logger.exception(
                      f"An unexpected error occurred while connecting to the relay server.")
                _occured_exception = e


              await asyncio.sleep(10.0)

            if _g_async_event_stop.is_set() :
              return

            if MODEL == MODEL_PORTABLE :
              observer = fwatchdog.observe(PORTABLE_MESSAGE_R_FILE)
              observer.on_created = on_changed_message_file
              observer.on_modified = on_changed_message_file
              observer.start()
              logger.debug('cube observer.start()')
            else :
              observer = None

            logger.debug(f"cube run...")
            try :
              await _g_async_event_stop.wait()
            finally :
              if observer:
                observer.stop()
                observer.join()
                logger.debug('observer.stop()')
          finally:
            _felica_reader.stop()
            logger.debug('_felica_reader.stop()')
        finally:
          if _g_cube :
            _g_cube.stop()
            _g_cube = None
          logger.debug('cube exit')
      except KeyboardInterrupt :
        raise
      except asyncio.exceptions.CancelledError:
        raise
      except OSError as e:
          logger.exception(f'Error!! occured by create cube instance.:(errno:{e.errno})')
      except Exception as e:
          logger.exception(f'Error!! occured by create cube instance.:({type(e)})')
    finally :
      _g_thread = None
      _g_loop = None

def is_serving(timeout=0.0) :
  """"""
  return _g_serving_event.wait(timeout)

def stop():
  """"""
  logger.debug(f'medcube.stop() start. _g_thread:{_g_thread}')
  if _g_thread is not None and _g_thread.is_alive() :
    logger.debug('medcube.stop() _g_thread is alive.')
    _current_thread = current_thread()
    if _g_thread == _current_thread :
      _g_async_event_stop.set()
      logger.debug('medcube.stop(). Stop in own thread.')
    else :
      if _g_loop :
        async def _set_async_event_stop():
          _g_async_event_stop.set()
          logger.debug('medcube.stop() _set_async_event_stop.set().')

        logger.debug('medcube.stop() _g_async_event_stop thread set.')
        future = asyncio.run_coroutine_threadsafe(_set_async_event_stop(), _g_loop)
        logger.debug('medcube.stop() _g_async_event_stop thread run.')
        future.result()
        logger.debug('medcube.stop(). Stopped from another thread.')


def _callback_on_serving():
  pass


def set_callback_on_serving(callback) :
  global _callback_on_serving
  if callable(callback) :
    _callback_on_serving = callback

if __name__ == '__main__':
  # start()
  asyncio.run(start_async())
