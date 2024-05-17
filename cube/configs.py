# -*- coding: utf-8 -*-
import os

import application

MODEL_CUBE = 'cube'
MODEL_PANEL = 'panel'
MODEL_PORTABLE = 'portable'

TCUPI_RELAY_HOST = '192.168.0.2'
TCUPI_RELAY_PORT = 8892

TCUPI_CAMERA_HOST = '192.168.0.2'
TCUPI_CAMERA_PORT = 8893

TCUPI_DAEMON_HOST = '192.168.0.2'
TCUPI_DAEMON_PORT = 8894

TCUPI_HOST = None
TCUPI_PORT = 8891

TCUPI_RELAY_HOST = application.configs.get(
    'RELAY', 'IP', fallback=TCUPI_RELAY_HOST)
TCUPI_RELAY_PORT = application.configs.getint(
    'RELAY', 'PORT', fallback=TCUPI_RELAY_PORT)

TCUPI_CAMERA_HOST = application.configs.get(
    'CLIENT', 'IP', fallback=TCUPI_CAMERA_HOST)
TCUPI_CAMERA_PORT = application.configs.getint(
    'CLIENT', 'PORT', fallback=TCUPI_CAMERA_PORT)

TCUPI_DAEMON_HOST = application.configs.get(
    'TCUD', 'IP', fallback=TCUPI_DAEMON_HOST)
TCUPI_DAEMON_PORT = application.configs.getint(
    'TCUD', 'PORT', fallback=TCUPI_DAEMON_PORT)

TCUPI_HOST = application.configs.get('TCU', 'IP', fallback=TCUPI_HOST)
TCUPI_PORT = application.configs.getint('TCU', 'PORT', fallback=TCUPI_PORT)

# ##############################################################################
# Model
# ##############################################################################
MODEL = application.configs.get('TCU', 'MODEL', fallback=None)

# ##############################################################################
# Timeout
# ##############################################################################
UNLOCK_TIMEOUT = application.configs.getfloat(
    'TCU', 'UNLOCK_TIMEOUT', fallback=180.0)

# ##############################################################################
# Distance sensor
# ##############################################################################
DISTANCE_INTERVAL = application.configs.getfloat(
    'TCU', 'DISTANCE_INTERVAL', fallback=0.1)
DISTANCE_PERIOD = application.configs.getfloat(
    'TCU', 'DISTANCE_PERIOD', fallback=2.0)
DISTANCE_IS_THERE_OF_CHANGE = application.configs.getfloat(
    'TCU', 'DISTANCE_IS_THERE_OF_CHANGE', fallback=10.0 if MODEL in [MODEL_CUBE] else 0.0)
DISTANCE_IS_NOT_THERE_OF_CHANGE = application.configs.getfloat(
    'TCU', 'DISTANCE_IS_NOT_THERE_OF_CHANGE', fallback=10.0 if MODEL in [MODEL_CUBE] else 0.0)

varTCU_DISTANCE_MIN = application.configs.getfloat(
    'TCU', 'DISTANCE_MIN', fallback=1.5)
varTCU_DISTANCE_MAX = application.configs.getfloat(
    'TCU', 'DISTANCE_MAX', fallback=4.0)
varTCU_DISTANCE_IS_THERE = application.configs.getfloat(
    'TCU', 'DISTANCE_IS_THERE', fallback=5.0)
varSITDOWN = application.configs.getfloat('TCU', 'SITDOWN_SEC', fallback=3.0)

# ##############################################################################
# light
# ##############################################################################
LIGHT_WITH = application.configs.getboolean(
    'TCU', 'LIGHT_WITH', fallback=True if MODEL in [MODEL_CUBE, MODEL_PANEL] else False)

# ##############################################################################
# UV light
# ##############################################################################
UVLITE_WITH = application.configs.getboolean(
    'TCU', 'UVLITE_WITH', fallback=True if MODEL in [MODEL_CUBE] else False)
UVLITE_PERIOD = application.configs.getfloat(
    'TCU', 'UVLITE_PERIOD', fallback=10.0 if MODEL in [MODEL_CUBE] else 0.0)
UVLITE_WAIT_WHILE_LIT = application.configs.getboolean(
    'TCU', 'UVLITE_WAIT_WHILE_LIT', fallback=True)

# ##############################################################################
# Door Control
# ##############################################################################
DOOR_TIME_TO_LOCK_FROM_CLOSING = application.configs.getfloat(
    'TCU', 'DOOR_TIME_TO_LOCK_FROM_CLOSING', fallback=1.5)

# ##############################################################################
# Door lock
# ##############################################################################
LOCK_PULSE_TIME = application.configs.getint(
    'TCU', 'LOCK_PULSE_TIME', fallback=4500)
LOCK_PULSE_DELAY = application.configs.getint(
    'TCU', 'LOCK_PULSE_DELAY', fallback=1000)

# ##############################################################################
# upload
# ##############################################################################
SENSOR_UPLOAD_INTERVAL = application.configs.getfloat(
    'TCU', 'SENSOR_UPLOAD_INTERVAL', fallback=10)

# ##############################################################################
# pi camera
# ##############################################################################
if os.name == 'posix':
  _SPO2CAMERA_IMAGE_SAVE_PATH = application.configs.get(
      'TCU', 'SPO2CAMERA_IMAGE_GET_PATH', fallback=f'/tmp/tcu/{MODEL}' if MODEL != MODEL_PORTABLE else os.path.expanduser('~/Public'))
else:
  SPO2CAMERA_IMAGE_SAVE_PATH = application.configs.get(
      'TCU', 'SPO2CAMERA_IMAGE_GET_PATH', fallback='./')

SPO2CAMERA_IMAGE_FILE_NAME = application.configs.get(
    'TCU', 'SPO2CAMERA_IMAGE_FILE_NAME', fallback="image.png")
SPO2CAMERA_IMAGE_RESO_W = application.configs.getint(
    'TCU', 'SPO2CAMERA_IMAGE_RESO_W', fallback=800)
SPO2CAMERA_IMAGE_RESO_H = application.configs.getint(
    'TCU', 'SPO2CAMERA_IMAGE_RESO_H', fallback=600)
SPO2CAMERA_IMAGE_GET_TIMEOUT = application.configs.getfloat(
    'TCU', 'SPO2CAMERA_IMAGE_GET_TIMEOUT', fallback=5.0)

# ##############################################################################
# USB camera
# ##############################################################################
if os.name == 'posix':
  USBCAMERA_IMAGE_SAVE_PATH = application.configs.get(
      'TCU', 'USBCAMERA_IMAGE_GET_PATH', fallback=f"/tmp/tcu/{MODEL}")
else:
  USBCAMERA_IMAGE_SAVE_PATH = application.configs.get(
      'TCU', 'USBCAMERA_IMAGE_GET_PATH', fallback="./")

USBCAMERA_IMAGE_FILE_NAME = application.configs.get(
    'TCU', 'USBCAMERA_IMAGE_FILE_NAME', fallback="image.png")
USBCAMERA_IMAGE_RESO_W = application.configs.getint(
    'TCU', 'USBCAMERA_IMAGE_RESO_W', fallback=800)
USBCAMERA_IMAGE_RESO_H = application.configs.getint(
    'TCU', 'USBCAMERA_IMAGE_RESO_H', fallback=600)
USBCAMERA_IMAGE_GET_TIMEOUT = application.configs.getfloat(
    'TCU', 'PICAMERA_IMAGE_GET_TIMEOUT', fallback=5.0)

# ##############################################################################
# server
# ##############################################################################
SERVER_HOST_NAME = application.configs.get(
    'TCU', 'SERVER_HOST_NAME', fallback='cubemed.hosoya.onlinemed.biz')

# ##############################################################################
# mqtt
# ##############################################################################
ONLINEMED_SERVER_URL = application.configs.get(
    'TCU', 'MQTT_BLOKER_ADDRESS', fallback=SERVER_HOST_NAME)
ONLINEMED_SERVER_PORT = application.configs.getint(
    'TCU', 'MQTT_BLOKER_PORT', fallback=1883)
ONLINEMED_CUBE_ROOT_TOPIC = application.configs.get(
    'TCU', 'MQTT_TOPICS', fallback='minnzennkai/cube')

# ##############################################################################
# online medical
# ##############################################################################
# patient url
ONLINEMED_PATIENT_URL = application.configs.get(
    'TCU', 'ONLINEMED_PATIENT_URL', fallback=f'patient.{SERVER_HOST_NAME}')
ONLINEMED_PATIENT_KIOSK = application.configs.getboolean(
    'TCU', 'ONLINEMED_PATIENT_KIOSK', fallback=True)

# ##############################################################################
# tv control
# ##############################################################################
# TV Control
TV_CONTROL = application.configs.getboolean(
    'TCU', 'TV_CONTROL', fallback=False if MODEL != MODEL_PANEL else True)
TV_CONTROL_CEC = application.configs.getboolean(
    'TCU', 'TV_CONTROL_CEC', fallback=False if MODEL != MODEL_PANEL else True)

# turn on
TV_TURNON_SOURCE = application.configs.get(
    'TCU', 'TV_TURNON_SOURCE', fallback='IR')
TV_TURNON_WAIT = application.configs.getfloat(
    'TCU', 'TV_TURNON_WAIT', fallback=0.0)
TV_TURNON_RETRY = application.configs.getint(
    'TCU', 'TV_TURNON_RETRY_NUM', fallback=1)

# turn off
TV_TURNOFF_SOURCE = application.configs.get(
    'TCU', 'TV_TURNOFF_SOURCE', fallback='IR')
TV_TURNOFF_WAIT = application.configs.getfloat(
    'TCU', 'TV_TURNOFF_WAIT', fallback=0.0)
TV_TURNOFF_RETRY = application.configs.getint(
    'TCU', 'TV_TURNOFF_RETRY_NUM', fallback=1)

# ##############################################################################
# Panel
# ##############################################################################
FELICA_SWITCH_INTERVAL = application.configs.getfloat(
    'TCU', 'FELICA_SWITCH_INTERVAL', fallback=30.0)

# ##############################################################################
# Portable
# ##############################################################################
PORTABLE_MESSAGE_FILE = application.configs.get(
    'TCU', 'PORTABLE_MESSAGE_FILE', fallback='/home/pi/Public/message.ini')
PORTABLE_MESSAGE_TIMEOUT = application.configs.getfloat(
    'TCU', 'PORTABLE_MESSAGE_TIMEOUT', fallback=1.0)
PORTABLE_MESSAGE_R_FILE = application.configs.get(
    'TCU', 'PORTABLE_MESSAGE_R_FILE', fallback='/home/pi/Public/messageR.ini')
PORTABLE_FILEWATCH_FIXED_TIME = application.configs.getfloat(
    'TCU', 'PORTABLE_FILEWATCH_FIXED_TIME', fallback=1.0)
