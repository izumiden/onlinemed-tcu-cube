#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import errno
import json
from logging import getLogger
import paho.mqtt.client
import os
import time
from threading import Thread, Lock, Event

logger = getLogger(__name__)


class DoubleAuthError(Exception):
  """
  Exception raised when an attempt is made to perform an authentication operation
  that has already been completed.

  This error is typically raised when a function or method responsible for
  user authentication is called more than once for the same user in a context
  where this is not expected or allowed.
  """
  pass

class Session(object) :
  """
  """
  @property
  def idm(self) :
    return self._idm

  @idm.setter
  def idm(self, val):
    if val is None :
      self._idm = val
    else :
      int(val, 0x10)
      self._idm = val

  @property
  def reservation_id(self) :
    return self._reservation_id

  def _reservation_id_set(self, val):
    self._reservation_id = val

  def __init__(self, client, idm=None, reservation_id=None) :
    self._idm = None
    self._reservation_id = None

    self.idm = idm
    self._reservation_id_set(reservation_id)
    self._client = client

  def __bool__(self):
    logger.debug(f'{self}.__bool__()')
    return bool(self._reservation_id)

  def __set__(self, object, value) :
    logger.debug(f'{self}.__set__({object}, {value})')
    if self._idm :
      self._reservation_id = value

  def __eq__(self, object) :
    logger.debug(f'{self}.__eq__({object})')
    if isinstance(object, Session) :
      return self._reservation_id == object._reservation_id
    else :
      return self._reservation_id == object

  def __ne__(self, object) :
    logger.debug(f'{self}.__ne__({object})')
    return not self.__eq__(object)

  def close(self) :
    self._idm = None
    self._reservation_id = None
    self._client = None

class Client(object):
  """
  """
  @property
  def session(self) -> Session:
    return self._session

  @property
  def reservation_id(self) :
    if self._session :
      return self._session.reservation_id
    return None

  @property
  def idm(self) :
    if self._session :
      return self._session.idm
    return None

  @property
  def device_id(self):
    return self._device_id

  @device_id.setter
  def device_id(self, value):
    self._device_id = str(value)

  @property
  def is_connected(self) -> bool:
    return self._is_connected

  @property
  def is_authenticated(self) -> bool:
    return bool(self.reservation_id)

  def __init__(self, broker:str, port:int, roottopics: str = '', url: str = '', keepalive=60, timeout: float = 10.0):

    if os.name == 'posix':
      import netifaces
      # MAC ADDRESS
      iface_data = None
      for interface in netifaces.interfaces():
        ifaddress = netifaces.ifaddresses(interface)
        logger.debug ('Interface: {}'.format(interface))
        logger.debug ('\tMAC Address')
        logger.debug ('\t\t{}'.format(ifaddress.get(netifaces.AF_LINK)))
        logger.debug ('\tIPv4 Address')
        logger.debug ('\t\t{}'.format(ifaddress.get(netifaces.AF_INET)))
        logger.debug ('\tIPv6 Address')
        logger.debug ('\t\t{}'.format(ifaddress.get(netifaces.AF_INET6)))

        if ifaddress.get(netifaces.AF_INET) is not None :
          if interface == "eth0" :
            iface_data = ifaddress
            break
          else :
            if iface_data is None :
              iface_data = ifaddress

      self._device_id = iface_data.get(netifaces.AF_LINK)[0]["addr"]
      self._ip_addr = iface_data.get(netifaces.AF_INET)[0]['addr']
    else :
      self._device_id = 'deviceid'

    self._broker = broker
    self._port = port
    self._keepalive = keepalive
    self._timeout = timeout
    self._root_topics = roottopics

    self._idm = None
    self._client = None
    self._is_connected = False

    self._auth_request_lock = Lock()
    self._auth_lock = Lock()

    self._on_connect_event = Event()
    self._auth_done_event = Event()
    # self._on_disconnect_event = Event()
    self._session = None

    self.on_request_cube_open = None
    self.on_request_web_open = None
    self.on_request_shoot_spo2 = None
    self.on_request_shoot_usbcamera = None
    self.on_panel_function = None
    self.on_panel_func_button = None
    self.on_panel_func_stop = None
    self.on_panel_func_exit = None

    self._url = url.rstrip('/')

  def __enter__(self) :
    self.connect()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb) :
    self.disconnect()

  def __bool__(self) :
    return False if self._client is None else True

  def _subscribe_command(self, topic):
    """
    """
    logger.info(f"subscribe topic:{topic} type :{type(topic)}")

    def _set_subscribe_topic(topic):
      topics = f"{self._root_topics}/{topic}/{self._device_id}"
      logger.debug(f"set subscribe topic :{topics}.")
      self._client.subscribe(topics)

    if isinstance(topic, str):
      _set_subscribe_topic(topic)
    elif isinstance(topic, list):
      for tpc in topic:
        _set_subscribe_topic(tpc)

  def _unsubscribe_command(self, topic):
    """
    """
    self._client.unsubscribe(f"{self._root_topics}/{topic}/{self._device_id}")

  def authentication(self, idm: str, timeout: float | None = None):
    """
    """
    def connect_by_os_name():
      if os.name == 'posix':
        self._client.connect(
            self._broker, self._port, keepalive=self._keepalive, bind_address=self._ip_addr)
        logger.info(
            f"mqtt connect broker {self._broker}:{self._port} keepalive {self._keepalive} src ip addr {self._ip_addr}")
      else:
        self._client.connect(
            self._broker, self._port,keepalive=self._keepalive)
        logger.info(
            f"mqtt connect broker {self._broker}:{self._port} keepalive {self._keepalive}")

    def authentication_thread(timeout: float = 10.0, auth_locked_event: Event | None = None):

      try :
        with self._auth_lock :
          logger.debug(f"authentication locked. {idm}")

          if auth_locked_event :
            auth_locked_event.set()

          if self._client is None:
            self._client = paho.mqtt.client.Client(
                userdata=self, protocol=paho.mqtt.client.MQTTv311)
            self._client.enable_logger(getLogger('paho.mqtt.client'))
            self._client.on_connect = on_connect
            self._client.on_message = on_message
            self._client.on_disconnect = on_disconnect

            self._on_connect_event.clear()

            connect_by_os_name()
          else :
            is_recconect = self._on_connect_event.is_set()
            self._on_connect_event.clear()

            if not is_recconect :
              connect_by_os_name()
            else:
              self._client.reconnect()
              logger.info(f"mqtt reconnect broker")

          self._client.loop_start()
          logger.info(f"mqtt loop start")

          t = time.time()
          if not self._on_connect_event.wait(timeout):
            errer_msg = "mqtt connect timeout"
            logger.info(errer_msg)
            self._client.loop_stop()
            raise TimeoutError(errno.ETIMEDOUT, os.strerror(
                errno.ETIMEDOUT), errer_msg)

          if timeout is not None:
            timeout -= time.time() - t
            if timeout < 0.0 :
              timeout = 0.0

          # サーバへ認証処理要求
          # entry コマンド送信
          publish_topics = f"{self._root_topics}/entry/{self._device_id}"
          message = {
              'unixtime': int(time.time()), 'ferica_id': idm
          }
          logger.info(f"authentication:{publish_topics}")
          logger.info(f"message:{message}")

          self._auth_done_event.clear()
          self._client.publish(publish_topics, json.dumps(message))
          self._session = Session(self, idm)

          if timeout is not None:
            # timeoutが指定されている場合は、認証完了を待つ
            if not self._auth_done_event.wait(timeout):
              # 認証処理がタイムアウト
              self.disconnect()
          else :
            # timeoutが未指定の場合は、タイムアウト処理を行わない
            pass

      except :
        logger.exception(f"authentication_thread except has occuered.")

    with self._auth_request_lock :
      logger.debug(f"check authentication is lock. {idm}")
      if self._auth_lock.locked() :
        raise DoubleAuthError(
            f"Duplicate authentication attempt detected for idm: {idm}")

      # 認証スレッドを開始
      auth_locked_event = Event()
      thread = Thread(target=authentication_thread, kwargs={
                      'timeout': timeout, 'auth_locked_event': auth_locked_event})
      thread.start()
      # 認証処理ロック取得完了まで待機
      auth_locked_event.wait()

  def disconnect(self):
    logger.info(f'__onlinemed_client_disconnect {self}')
    try :
      if self._auth_lock.locked():
        self._auth_done_event.set()

      if self._client is not None :
        self._client.disconnect()
        self._client.loop_stop()
        self._session = None
        logger.info(f'mqtt disconnected {self._client}')
      else :
        logger.info(f'mqtt is not connected.')
    finally :
      self._client = None
    logger.info('--')
    logger.info('')

  def measure(self, data : dict) :
    publish_topics = f"{self._root_topics}"
    message = {
        'unix_time': int(time.time()), "device_id": self._device_id, 'reservation_id': self.reservation_id, **data
    }
    logger.debug(f"measure:{publish_topics}")
    logger.debug(f"message:{message}")

    self._client.publish(publish_topics, json.dumps(message))

  def res_spo2(self, image) :
    publish_topics = f"{self._root_topics}/resspo2/{self._device_id}"
    message = {
                'unixtime'      :int(time.time())
              , 'reservation_id':self.reservation_id
              }
    logger.info(f"resspo2:{publish_topics}")
    logger.info(f"message:{message}")

    image_b64encode = base64.b64encode(image)
    image_utf8decord = image_b64encode.decode("utf-8")
    message['spo2_image'] = image_utf8decord

    logger.info(f"image      type {type(image)} size {len(image)} bytes")
    logger.info(f"b64encode  type {type(image_b64encode)} size {len(image_b64encode):} bytes")
    logger.info(f"utf8decord type {type(image_utf8decord)} size {len(image_utf8decord)} bytes")

    self._client.publish(publish_topics, json.dumps(message))

  def res_usbcamera(self, image) :
    publish_topics = f"{self._root_topics}/resusbcam/{self._device_id}"
    message = {
                'unixtime'      :int(time.time())
              , 'reservation_id':self.reservation_id
              }
    logger.info(f"resusbcam:{publish_topics}")
    logger.info(f"message:{message}")

    image_b64encode = base64.b64encode(image)
    image_utf8decord = image_b64encode.decode("utf-8")
    message['usbcam_image'] = image_utf8decord

    logger.info(f"image      type {type(image)} size {len(image)} bytes")
    logger.info(f"b64encode  type {type(image_b64encode)} size {len(image_b64encode):} bytes")
    logger.info(f"utf8decord type {type(image_utf8decord)} size {len(image_utf8decord)} bytes")

    self._client.publish(publish_topics, json.dumps(message))

  def patient_status(self, status) :

    publish_topics = f"{self._root_topics}/patient_status/{self._device_id}"
    message = {
                  'unixtime':int(time.time())
                , 'reservation_id':self.reservation_id
                , 'status':status
              }
    logger.info(f"patient_status:{publish_topics}")
    logger.info(f"message:{message}")

    self._client.publish(publish_topics, json.dumps(message))

  def patient_enter(self) :
    return self.patient_status('enter')

  def patient_exit(self) :
    return self.patient_status('exit')

  def _handle_cube_open(self, unixtime=None, reservation_id=None):
    """"""
    self._auth_done_event.set()

    if not reservation_id:
      self._session = None
    else:
      self._session._reservation_id_set(reservation_id)

    if self.on_request_cube_open:
      self.on_request_cube_open(self)

  def _handle_web_open(self, unixtime=None, reservation_id=None, status=None):
    """"""
    logger.info(f"_on_request_web_open")
    if not reservation_id:
      self._session = None
    else:
      self._session._reservation_id_set(reservation_id)

    if self.on_request_web_open:
      self.on_request_web_open(self)

  def _handle_shoot_spo2(self, unixtime=None, reservation_id=None):
    """"""
    logger.info(f"_on_request_shoot_spo2")
    if self.on_request_shoot_spo2:
      self.on_request_shoot_spo2(self)

  def _handle_shoot_usbcamera(self, unixtime=None, reservation_id=None):
    """"""
    logger.info(f"_on_request_shoot_usbcamera")
    if self.on_request_shoot_usbcamera:
      self.on_request_shoot_usbcamera(self)

  def _handle_function(self, unixtime=None, reservation_id=None, status=None):
    """"""
    logger.info(
        f"_on_panel_function reservation_id:{reservation_id} status is {status}")
    if self.on_panel_function:
      self.on_panel_function(self, status)

  def _handle_func_button(self, unixtime=None, reservation_id=None, status=None):
    """"""
    logger.info(
        f"_on_panel_function reservation_id:{reservation_id} status is {status}")
    if self.on_panel_func_button:
      self.on_panel_func_button(self, status)

  def _handle_func_stop(self, unixtime=None, reservation_id=None, status=None):
    """"""
    logger.info(
        f"_on_panel_func_stop reservation_id:{reservation_id} status is {status}")
    if self.on_panel_func_stop:
      self.on_panel_func_stop(self, status)

  def _handle_func_exit(self, unixtime=None, reservation_id=None, status=None):
    """"""
    logger.info(
        f"_on_panel_func_exit reservation_id:{reservation_id} status is {status}")
    if self.on_panel_func_exit:
      self.on_panel_func_exit(self, status)


def on_connect(client: paho.mqtt.client.Client, userdata: Client, flags, rc):
  try:
    if rc == 0:
      userdata._is_connected = True
      userdata._on_connect_event.set()
      logger.info(
          f"Connected to MQTT Broker! flags:{flags} client {client} userdata:{userdata}")
      userdata._subscribe_command(['cube_open', 'web_open', 'reqspo2', 'requsbcam', 'panelfunction_open', 'panelfunction_call', 'panelfunction_stop', 'panelfunction_exit'
                          ])
    else:
      logger.info(f"Failed to connect, return code {rc}\n")
      userdata._is_connected = False
  except:
    logger.exception('Exception occurred on_connect()!')


def on_disconnect(client: paho.mqtt.client.Client, userdata: Client, rc):
  try:
    userdata._is_connected = False
    if rc == 0:
      logger.info(
          f"Disconnected to MQTT Broker! client {client} userdata:{userdata}")
    else:
      logger.info(f"Failed to disconnect, return code {rc}\n")
  except:
    logger.exception('Exception occurred on_disconnect()!')


def on_message(client: paho.mqtt.client.Client, userdata: Client, msg):
  try:
    logger.info(
        f"Received from `{msg.topic}` `{msg.payload}` with userdata `{userdata}`")
    topics = msg.topic.rsplit('/', 2)

    deviceid = topics[-1]
    topic = topics[-2]

    msg_data = json.loads(msg.payload.decode())

    def on_message_thread(**msg_data):
      try:
        if topic == 'cube_open':
          userdata._handle_cube_open(**msg_data)
        elif topic == 'web_open':
          userdata._handle_web_open(**msg_data)
        elif topic == 'reqspo2':
          userdata._handle_shoot_spo2(**msg_data)
        elif topic == 'requsbcam':
          userdata._handle_shoot_usbcamera(**msg_data)
        elif topic == 'panelfunction_open':
          userdata._handle_function(**msg_data)
        elif topic == 'panelfunction_call':
          userdata._handle_func_button(**msg_data)
        # elif topic == 'panelfunction_stop' :
        #   _on_panel_func_stop(userdata, **msg_data)
        elif topic == 'panelfunction_stop':
          userdata._handle_func_exit(**msg_data)
      except:
        logger.exception('Exception occurred on_message_thread()!')
    thread = Thread(target=on_message_thread, kwargs=msg_data)
    thread.start()
  except:
    logger.exception('Exception occurred on_message()!')


if __name__ == '__main__':

  # mosquitto_pub -h cubemed.hosoya.onlinemed.biz -t minnzennkai/cube/panel_func_exit/e4:5f:01:4b:64:50 -m '{"reservation_id":309, "status":1}'

  import application
  import argparse
  import logging

  _ONLINEMED_SERVER_URL = application.configs.get('TCU', 'MQTT_BLOKER_ADDRESS', fallback='cubemed.hosoya.onlinemed.biz')
  _ONLINEMED_SERVER_PORT = application.configs.getint('TCU', 'MQTT_BLOKER_PORT', fallback=1883)
  _ONLINEMED_CUBE_ROOT_TOPIC = application.configs.get('TCU', 'MQTT_TOPICS', fallback='minnzennkai/cube')
  _ONLINEMED_PATIENT_URL = application.configs.get('TCU', 'ONLINEMED_PATIENT_URL', fallback='patient.cubemed.hosoya.onlinemed.biz/index.html')


  argp = argparse.ArgumentParser()
  argp.add_argument("--log", type=str, default='DEBUG')

  argp.add_argument("--broker", type=str, default=_ONLINEMED_SERVER_URL)
  argp.add_argument("--port", type=int, default=_ONLINEMED_SERVER_PORT)
  argp.add_argument("--topic", type=str, default=_ONLINEMED_CUBE_ROOT_TOPIC)

  argp.add_argument("-c", "--command", type=str, default=None)
  argp.add_argument("--id", default=0)

  args = argp.parse_args()

  LOGLEVEL = args.log.upper()
  loglevel = getattr(logging, LOGLEVEL, None)
  if isinstance(loglevel, int) :
    logger.setLevel(loglevel)

  logging_stream_handler = logging.StreamHandler()
  logger.addHandler(logging_stream_handler)

  if args.command :
    message = {
                'unixtime':int(time.time())
              , 'reservation_id':args.id
    }

    mqtt = paho.mqtt.client.Client(protocol=paho.mqtt.client.MQTTv311)
    mqtt.connect(args.broker, args.port)
    mqtt.publish(f'{args.topic}/{args.command}', json.dumps(message))
  else :
    client = Client(_ONLINEMED_SERVER_URL, _ONLINEMED_SERVER_PORT, _ONLINEMED_CUBE_ROOT_TOPIC, _ONLINEMED_PATIENT_URL)

    client.connect()

    while(True) :
      try :
        time.sleep(1.0)
      except :
        logger.exception("")
        break
