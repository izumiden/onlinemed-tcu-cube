#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
from logging import getLogger
import os.path

import application
import fwatchdog

SECTION_MESSAGE = 'MESSAGE'
KEY_STATUS = 'STATUS'
KEY_ID = 'ID'
KEY_REQUEST = 'REQ'

MESSAGE_STATUS_START = 'START'
MESSAGE_STATUS_RESPID = 'RESPID'
MESSAGE_STATUS_WEBOPEN = 'WEBOPEN'
MESSAGE_STATUS_EXE = 'EXE'
MESSAGE_STATUS_END = 'END'

MESSAGE_REQUEST_IMAGE = 'IMAGE'

logger = getLogger(__name__)

# ##############################################################################
# Portable
# ##############################################################################
PORTABLE_MESSAGE_FILE = application.configs.get(
    'TCU', 'PORTABLE_MESSAGE_FILE', fallback='/home/pi/Public/message.ini')
PORTABLE_MESSAGE_R_FILE = application.configs.get(
    'TCU', 'PORTABLE_MESSAGE_R_FILE', fallback='/home/pi/Public/messageR.ini')
PORTABLE_FILEWATCH_FIXED_TIME = application.configs.getfloat(
    'TCU', 'PORTABLE_FILEWATCH_FIXED_TIME', fallback=1.0)


class Message():
  def __init__(self, status: str) -> None:
    self._status = status

  @property
  def status(self) -> ...:
    return self._status


class NoticeMessage(Message):
  def __init__(self, status: str, id: ...) -> None:
    super().__init__(status)
    self._id = id

  @property
  def id(self) -> ...:
    return self._id


class RequestMessage(Message):
  def __init__(self, status: str, request: ...) -> None:
    super().__init__(status)
    self._request = request

  @property
  def request(self) -> ...:
    return self._request


class StartMessage(NoticeMessage):
  def __init__(self, id: ...) -> None:
    super().__init__(MESSAGE_STATUS_START, id)


class NotifyIDMessage(NoticeMessage):
  def __init__(self, id: ...) -> None:
    super().__init__(MESSAGE_STATUS_RESPID, id)


class WebOpenMessage(NoticeMessage):
  def __init__(self, id) -> None:
    super().__init__(MESSAGE_STATUS_WEBOPEN, id)


class ExecuteMessage(RequestMessage):
  def __init__(self, request) -> None:
    super().__init__(MESSAGE_STATUS_EXE, request)


class EndMessage(RequestMessage):
  def __init__(self, request) -> None:
    super().__init__(MESSAGE_STATUS_END, request)


def load_message(filepath: str) -> Message | None:
  message = None
  if os.path.isfile(filepath):
    configs = configparser.ConfigParser()
    configs.read(filepath)
    status = configs.get(SECTION_MESSAGE, KEY_STATUS, fallback=None)
    if status == MESSAGE_STATUS_START:
      id = configs.get(SECTION_MESSAGE, KEY_ID, fallback=None)
      message = StartMessage(id)
    elif status == MESSAGE_STATUS_RESPID:
      id = configs.get(SECTION_MESSAGE, KEY_ID, fallback=None)
      message = NotifyIDMessage(id)
    elif status == MESSAGE_STATUS_WEBOPEN:
      id = configs.get(SECTION_MESSAGE, KEY_ID, fallback=None)
      message = WebOpenMessage(id)
    elif status == MESSAGE_STATUS_EXE:
      request = configs.get(SECTION_MESSAGE, KEY_REQUEST, fallback=None)
      message = ExecuteMessage(request)
    elif MESSAGE_STATUS_END:
      request = configs.get(SECTION_MESSAGE, KEY_REQUEST, fallback=None)
      message = EndMessage(request)
  return message


def send_message(message: Message, filepath: str = PORTABLE_MESSAGE_FILE, timeout: float = 0.0) -> bool:
  if isinstance(message, Message):
    try :
      configs = configparser.ConfigParser()
      configs.add_section(SECTION_MESSAGE)
      configs.set(SECTION_MESSAGE, KEY_STATUS, message.status)
      if isinstance(message, NoticeMessage):
        configs.set(SECTION_MESSAGE, KEY_ID, message.id)
      if isinstance(message, RequestMessage):
        configs.set(SECTION_MESSAGE, KEY_REQUEST, message.request)
      if timeout and 0.0 < timeout:
        with fwatchdog.observe(filepath, False, timeout) as observer:
          with open(filepath, 'w') as file:
            configs.write(file)
          if observer.on_deleted_event.wait(timeout):
            return True
          else :
            os.remove(filepath)
      else :
        with open(filepath, 'w') as file:
          configs.write(file)
    except configparser.Error:
      logger.exception('')

    return False

def send_start_message(felicaid=..., filepath: str = PORTABLE_MESSAGE_FILE, timeout: float = 0.0):
  message = StartMessage(felicaid)
  return send_message(message, filepath, timeout)


def send_notify_id_message(id=..., filepath: str = PORTABLE_MESSAGE_FILE, timeout: float = 0.0):
  logger.info(f'send_notify_id_message id:{id} filepath:{filepath}')
  message = NotifyIDMessage(str(id))
  return send_message(message, filepath, timeout)


def send_web_open_message(id=..., filepath: str = PORTABLE_MESSAGE_FILE, timeout: float = 0.0):
  message = WebOpenMessage(str(id))
  return send_message(message, filepath, timeout)


def send_request_message(request=..., filepath: str = PORTABLE_MESSAGE_FILE, timeout: float = 0.0):
  message = ExecuteMessage(request)
  return send_message(message, filepath, timeout)


if __name__ == "__main__":
  import logging
  import camera

  logging.basicConfig(level=logging.INFO, format=None)
  
  # ##############################################################################
  # pi camera
  # ##############################################################################
  _SPO2CAMERA_IMAGE_SAVE_PATH = application.configs.get(
      'TCU', 'SPO2CAMERA_IMAGE_GET_PATH', fallback=os.path.expanduser('/Public'))
  _SPO2CAMERA_IMAGE_FILE_NAME = application.configs.get(
      'TCU', 'SPO2CAMERA_IMAGE_FILE_NAME', fallback="image.png")
  _SPO2CAMERA_IMAGE_GET_TIMEOUT = application.configs.getfloat(
      'TCU', 'SPO2CAMERA_IMAGE_GET_TIMEOUT', fallback=5.0)

  filepath = _SPO2CAMERA_IMAGE_SAVE_PATH
  if os.path.isdir(filepath):
    if filepath[-1] != '/':
      filepath += '/'
    filepath += _SPO2CAMERA_IMAGE_FILE_NAME

    try:
      camera.free(filepath)
      send_request_message(MESSAGE_REQUEST_IMAGE)
      with fwatchdog.observe(
              filepath, False, PORTABLE_FILEWATCH_FIXED_TIME) as observer:
        observer.wait(_SPO2CAMERA_IMAGE_GET_TIMEOUT)
        image = camera.load_image(filepath)
    finally:
      camera.free(filepath)
