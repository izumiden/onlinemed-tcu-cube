#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox import service as fs
from selenium.webdriver.chrome import service as cs
from selenium.common.exceptions import NoSuchElementException, WebDriverException


from logging import getLogger
import os
from pathlib import PurePath, Path
import time

logger = getLogger(__name__)

_URL = "https://patient.cubemed.hosoya.onlinemed.biz/index.html?reservation_id=0"

class Webbrowser(metaclass=ABCMeta):
  """docstring for Webblowser."""

  def __init__(self, url=None, kiosk=True, safe_mode=False):
      super().__init__()

      if os.name == 'posix':
        if 'DISPLAY' not in os.environ:
          os.environ['DISPLAY'] = ':0.0'

      self._driver = None
      self._proc = None
      self._url = _URL

      if url is not None:
        if type(url) is str:
          self._url = url

      self._kiosk = bool(kiosk)
      self._safe_mode = bool(safe_mode)

  def __enter__(self):
      return self.open()

  def __exit__(self, exception_type, exception_value, traceback):
      self.close()

  def is_kisok(self) -> bool:
    return self._kiosk

  def is_safe_mode(self) -> bool:
    return self._safe_mode

  @abstractmethod
  def open(self) -> object:
      return self

  def get(self, url):
    self._driver.get(url)

  def close(self):
    if self._driver is not None:
      logger.info("webbrowser close.")
      if self._driver:
        self._driver.quit()
        self._driver = None
      if self._proc:
        self._proc.close()

  def is_inpage(self) -> bool:
    try:
      if hasattr(self._driver, 'find_element_by_tag_name'):
        try:
          html_tag = self._driver.find_element_by_tag_name('html')
          return True
        except NoSuchElementException as e:
          pass
    except:
        raise
    return False


class Chromebrowser(Webbrowser):
  """docstring for Firefoxbrowser."""

  def __init__(self, url=None, kiosk=True, safe_mode=False, profile: str | None = "Default"):
    super().__init__(url, kiosk, safe_mode)

    self._profile = profile

  def open(self):
    self._options = webdriver.ChromeOptions()
    if self._kiosk:
        self._options.add_argument('--kiosk')
    # self._options.add_argument('--no-sandbox')
    # self._options.add_argument('--disable-setuid-sandbox')

    # self._options.add_argument(f'-app={self._url}')
    # self._options.add_argument(self._url)

    if self._profile:
      user_data_dir = r"C:\Users\sizum\AppData\Local\Google\Chrome\User Data"
      self._options.add_argument(f'--user-data-dir={user_data_dir}')
      self._options.add_argument(f'--profile-directory={self._profile}')

    self._options.add_experimental_option(
        "excludeSwitches", ['enable-automation'])

    logger.debug(f"ChromeOptions:{self._options.arguments}")

    executable_path = Path.cwd() / "chromedriver\chromedriver.exe"
    logger.debug(f"executable_path:{executable_path}")

    # chrome_service = cs.Service(
    #     executable_path="/usr/lib/chromium-browser/chromedriver")
    chrome_service = cs.Service(executable_path=str(executable_path))
    self._driver = webdriver.Chrome(
        service=chrome_service, 
        options=self._options)
    self.get(self._url)

    return self


class Firefoxbrowser(Webbrowser):
  """docstring for Firefoxbrowser."""

  def __init__(self, url=None, *, kiosk=True, safe_mode=False, profile: str | None = None, executable_path: str | None = None, log_path: str | None = None):
      super().__init__(url, kiosk, safe_mode)

      if os.name == 'nt':
        if profile :
          path = Path(profile)
          if path.is_absolute():
            self._profile = path
          else:
            path_appdata = os.getenv('APPDATA')
            if path_appdata :
              path = Path(path_appdata)
              logger.debug(f"appdata:{path}")
            else:
              path = Path.home() / r'AppData\Roaming'

            path = path / r'Mozilla\Firefox\Profiles' / profile

            if path.is_dir() :
              self._profile = path
              logger.debug(f"dir profile:(type{type(self._profile)}) {self._profile}")
            else:
              self._profile = profile
              logger.debug(f"not dir profile:(type{type(self._profile)}) {self._profile}")
        else :
          self._profile = "default"

        logger.info(f"profile:{self._profile}")

        self._executable_path = Path.cwd() / r'geckodriver\geckodriver.exe'
        self._log_path = r'geckodriver\geckodriver.log'
      elif os.name == 'posix':
        self._profile = Path.home() / '.mozilla/firefox/7cam16m1.default-esr'
        self._executable_path = '/usr/local/bin/geckodriver'
        self._log_path = '/tmp/geckodriver.log'
      else:
        self._profile = profile
        self._executable_path = 'geckodriver'
        self._log_path = r'geckodriver.log'

      if isinstance(executable_path, str):
        if os.path.isdir(executable_path):
          self._executable_path = executable_path

      if isinstance(log_path, str):
        if os.path.isdir(log_path):
          self._log_path = log_path

  def profile_root() :
    if os.name == 'nt':
      path = os.getenv('APPDATA')
      if path:
        path = PurePath(path)
      else:
        path = Path.home() / r'AppData\Roaming'
      return path / r'Mozilla\Firefox\Profiles'
    elif os.name == 'posix':
      return Path.home() / '.mozilla/firefox'
    else:
      return Path.cwd()


  def open(self):
    if self._driver is None:
      options = webdriver.FirefoxOptions()
      options.add_argument(self._url)
      if self._kiosk:
        options.add_argument('--kiosk')
      if self._safe_mode:
        options.add_argument('-safe-mode')
      if self._profile :
        if isinstance(self._profile, PurePath) :
          options.add_argument('-profile')
        else :
          options.add_argument('-P')
        options.add_argument(str(self._profile))

      options.set_preference("browser.cache.disk.enable", False)


      if os.name == 'nt':
        options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

      logger.debug(
          f'firefox.service executable_path={self._executable_path} log_path={self._log_path}')

      service = fs.Service(
          executable_path=str(self._executable_path), log_path=self._log_path)
      self._driver = webdriver.Firefox(
          service=service, options=options)
      # self.get(self._url)

      return self


class Edgebrowser(Webbrowser):
  """docstring for Edgebrowser."""

  def __init__(self, url=None, *, kiosk=True, safe_mode=False, profile: str | None = None, executable_path: str | None = None, log_path: str | None = None):
      super().__init__(url, kiosk, safe_mode)

      self._profile = f"{os.path.expanduser('~')}\\AppData\\Local\\Microsoft\\Edge\\User Data"
      if isinstance(profile, str):
        if os.path.isdir(profile):
          self._profile = profile


  def open(self):
    if self._driver is None:
      options = EdgeOptions()
      
      # options.add_argument('-app={}'.format(self._url))
      if self._kiosk:
        options.add_argument('--kiosk')
      if self._safe_mode:
        options.add_argument('-safe-mode')
      options.add_argument(f"--user-data-dir={self._profile}")
      # options.add_argument(f"--profile-directory=Profile 1")
      options.use_chromium = True
      options.add_experimental_option('excludeSwitches', ['enable-automation'])
      logger.info(options.arguments)
      driverpath = r'D:\Users\sizum\OneDrive\Developments\projects\OnlineMed\TCU\rpi\home\pi\Tcu\cube\edgedriver\x64\msedgedriver.exe'
      service = EdgeService(executable_path=driverpath)
      self._driver = webdriver.Edge(service=service, options=options)
      self.get(self._url)

      return self


def open(url=None, *, kiosk=True, profile=None):
  try :
    wb = None
    if os.name == 'nt':
      # wb = Edgebrowser(url, kiosk=kiosk)
      wb = Firefoxbrowser(url, kiosk=kiosk, profile=profile)
    elif os.name == 'posix':
      wb = Firefoxbrowser(url, kiosk=kiosk, profile=profile)
    else :
      wb = Chromebrowser(url, kiosk=kiosk, profile=profile)

    if wb is not None :
      wb.open()
      logger.info("webbrowser open.")
    return wb
  finally :
    pass

if __name__ == '__main__':
  #
  # サービス停止時に終了処理を行うための設定
  #
  import signal
  import sys
  import logging

  if os.name == 'posix':
    def termed(signum, frame):
      print("")
      # print("SIGTERM!")
      sys.exit(0)

    # Terme
    signal.signal(signal.SIGTERM, termed)
    # Ctrl + c
    signal.signal(signal.SIGINT, termed)

  import argparse

  argp = argparse.ArgumentParser()

  argg = argp.add_mutually_exclusive_group()
  argg.add_argument("-E", "--Edge", action="store_true")
  argg.add_argument("-C", "--Chrome", action="store_true")
  argg.add_argument("-F", "--Firefox", action="store_true")

  argp.add_argument("--kiosk", action="store_true")
  argp.add_argument("--url", type=str, default=None)
  argp.add_argument("--debug", "-d", action="store_true")

  args = argp.parse_args()

  if args.debug :
    loglevel = logging.DEBUG
  else :
    loglevel = logging.INFO

  logging.basicConfig(level=logging.DEBUG, format=None)

  if args.Edge :
    blowser = Edgebrowser(url=args.url, kiosk=args.kiosk)
  elif args.Chrome:
    blowser = Chromebrowser(
        url=args.url, kiosk=args.kiosk, profile="Profile 1")
  elif args.Firefox:
    blowser = Firefoxbrowser(
        url=args.url, kiosk=args.kiosk, profile="OnlineMed Cube")
  else :
    if os.name == 'nt':
      blowser = Edgebrowser(url=args.url, kiosk=args.kiosk)
    else :
      blowser = Chromebrowser(
          url=args.url, kiosk=args.kiosk)

  with blowser:
    while True:
      try :
        # if not blowser.is_inpage() :
        #   break;
        time.sleep(1)
      except (NoSuchElementException, WebDriverException) as e:
        break
