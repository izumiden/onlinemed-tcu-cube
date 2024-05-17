# -*- coding: utf-8 -*-
import asyncio
from concurrent.futures import ThreadPoolExecutor
import configparser
import logging
import logging.config
from logging import getLogger, FileHandler
import os
from pathlib import Path
from pystray import Icon, Menu, MenuItem
from PIL import Image
import re
import shutil
import sys
import subprocess
import time
import tkinter
from tkinter import filedialog, messagebox
import threading
from threading import Thread, Event
import yaml

from constant import *

# ##############################################################################
# ログ定義
# ##############################################################################
try:
  logging.config.fileConfig(LOGGING_CONFIG_FILE)
except (configparser.MissingSectionHeaderError, KeyError):
  with open(LOGGING_CONFIG_FILE) as f:
    try:
      yaml_conf = yaml.safe_load(f)
      logging.config.dictConfig(yaml_conf)
    except FileNotFoundError:
      logging.exception("log config FileNotFoundError.")
    except (yaml.parser.ParserError, KeyError, ValueError):
      logging.exception("log config yaml parse error.")

# create logger
logger = getLogger(__name__)

def get_logfile_path():
  """"""
  root_logger = logging.getLogger()
    # ハンドラを探してファイル名を表示します
  for handler in root_logger.handlers:
    if isinstance(handler, FileHandler):
      return handler.baseFilename


root_logger = logging.getLogger()
logger .info(f"logger.handlers {root_logger.handlers}")


# ##############################################################################
#
# ##############################################################################
from . import medcube

_g_stop_event = Event()

def quit(icon: Icon):
  """"""
  if not _g_stop_event.is_set() :
    _g_stop_event.set()
    logger.info('app.quit()')

    medcube.stop()
    logger.info('medcube.stop()')

    if icon :
      icon.stop()
      logger.info('quit() - icon.stop()')


def show_error_messagebox(error_strings: str, title: str = "Error"):
  """"""
  root = tkinter.Tk()
  try:
    root.withdraw()  # 余分なウィンドウを非表示にする
    messagebox.showerror(title, error_strings)
  finally:
    root.destroy()  # tkinter のインスタンスを閉じる


def icon_menu_log_display(icon: Icon = None, item=None):
  """"""
  def _display() :
    """"""
    log_file = get_logfile_path()
    if log_file :
      path_log_file = Path(log_file)
      if path_log_file.is_file() :
        try :
          if os.name == 'nt':  # Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(['powershell.exe', '-Command',
                            'Start-Process', str(path_log_file)], check=True, startupinfo=startupinfo)
          else:  # Linux and MacOS
            subprocess.run(['open', f'"{str(path_log_file)}"'], check=True)
        except subprocess.CalledProcessError as e:
          logger.exception(f"display log")
          show_error_messagebox(f"ログファイルの表示に失敗しました。:{e}")
      else :
        show_error_messagebox(f"規定の場所にログファイルがありません。:{log_file}")
    else :
      show_error_messagebox(f"ログファイルが見つかりません。")

  t = Thread(target=_display)
  t.start()


def icon_menu_log_save_as(icon: Icon = None, item=None):
  """"""
  def _save_as() :
    """"""
    log_file = get_logfile_path()
    if log_file:
      path_log_file = Path(log_file)
      if path_log_file.is_file():

        base_filename = "cube"
        extension = ".log"
        if os.name == 'nt':  # Windows
          userprofile = os.getenv('USERPROFILE')
          logger.debug(f"userprofile {userprofile}")
          if userprofile :
            home_dir = Path(userprofile)
            if not home_dir.is_dir() :
              home_dir = Path.home()
          else :
            home_dir = Path.home()
        else:  # Linux and MacOS
          home_dir = Path.home()

        default_dir = home_dir / "Desktop"
        logger.debug(
            f"Desktop {default_dir} type:{type(default_dir)} is_dir:{default_dir.is_dir()}")
        if not default_dir.is_dir() :
          default_dir = home_dir / "デスクトップ"
          logger.debug(
              f"デスクトップ {default_dir} type:{type(default_dir)} is_dir:{default_dir.is_dir()}")
          if not default_dir.is_dir():
            default_dir = home_dir
            logger.debug(
                f"エラー {default_dir} type:{type(default_dir)} is_dir:{default_dir.is_dir()}")

        file_full_path = default_dir / (base_filename + extension)
        logger.debug(
            f"file_full_path {file_full_path} type:{type(file_full_path)} exists:{file_full_path.exists()}")
        if not file_full_path.exists():
          default_filename = f"{base_filename}{extension}"
        else :
          # default_dirの中の全てのファイルとディレクトリをリスト化
          existing_filenames = list(default_dir.iterdir())
          logger.debug(f"_save_as existing_filenames:{existing_filenames}")

          # 正規表現で数値を取り出す
          regex = re.compile(rf"{base_filename} \((\d+)\){extension}")

          # indices = [int(regex.search(f).group(1))
          #           for f in existing_filenames if regex.search(f)]
          indices = [int(regex.search(str(f)).group(1))
                      for f in existing_filenames if regex.search(str(f)) is not None]
          # indices = 0
          # for f in existing_filenames:
          #   result = regex.search(str(f))
          #   logger.debug(f"{result} = regex.search({f})")
          #   if result is not None:
          #     indices = int(regex.search(str(f)).group(1))

          if indices:
            # 最大のインデックスを取得し、それに1を加える
            max_index = max(indices)
            count = max_index + 1
          else:
            # マッチするものがなければ、インデックスは1
            count = 1

          default_filename = f"{base_filename} ({count}){extension}"

        try :
          root = tkinter.Tk()
          try:
            root.withdraw()  # 余分なウィンドウを非表示にする
            file_path = filedialog.asksaveasfilename(defaultextension=extension, initialdir=default_dir, initialfile=default_filename, filetypes=[
                                                      ("Log files", "*.log"), ("All files", "*.*")])
            if file_path:
              shutil.copyfile(log_file, file_path)  # ログファイルを選択した場所にコピーする
          finally:
            root.destroy()  # tkinter のインスタンスを閉じる
        except :
          show_error_messagebox(f"ログファイルの保存に失敗しました。:{log_file}")
      else:
        show_error_messagebox(f"規定の場所にログファイルがありません。:{log_file}")
    else:
      show_error_messagebox(f"ログファイルが見つかりません。")

  t = Thread(target=_save_as)
  t.start()

def icon_menu_log_open_folder(icon: Icon = None, item=None):
  """"""
  def _open_folder() :
    """"""
    log_file = get_logfile_path()
    if log_file:
      path_log_file = Path(log_file)
      path_log_dir = path_log_file.parent
      if path_log_dir.is_dir():
        try:
          if os.name == 'nt':  # Windows
            # subprocess.run(['explorer', str(path_log_dir)],
            #                 check=True, shell=True)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(['powershell.exe', '-Command',
                            'Start-Process', str(path_log_dir)], check=True, startupinfo=startupinfo)
          else:  # Linux and MacOS
            subprocess.run(['open', str(path_log_dir)], check=True)
        except subprocess.CalledProcessError as e:
          logger.exception(f"display log")
          show_error_messagebox(f"ログディレクトリの表示に失敗しました。:{e}")
      else:
        show_error_messagebox(f"規定の場所にディレクトリがありません。:{path_log_dir}")
    else:
      show_error_messagebox(f"ログディレクトリが見つかりません。")

  t = Thread(target=_open_folder)
  t.start()


def cube_task(loop: asyncio.AbstractEventLoop, callback) -> None:
  """"""
  asyncio.set_event_loop(loop)
  while not _g_stop_event.is_set():
    try:
      medcube.set_callback_on_serving(callback)
      loop.run_until_complete(medcube.start_async())
    except OSError as e:

      import errno
      if e.errno == (errno.EADDRNOTAVAIL, errno.WSAEADDRNOTAVAIL):
        logger.info(
            f"cube_task has occured OSError. Cannot assign requested address {e}")
        time.sleep(10.0)
        continue
      elif e.errno in (errno.EADDRINUSE, errno.WSAEADDRINUSE):
        logger.info(f"cube_task has occured OSError. Address already in use {e}")
        time.sleep(10.0)
        continue
      else:
        logger.exception('cube.__main__ OSError!')
        break
    except:
      logger.exception('cube.__main__ Except!')
      break


def cube_start():
  """"""
  _is_serving = Event()

  def callback_on_serving_cube():
    _is_serving.set()

  loop = asyncio.new_event_loop()
  t = Thread(target=cube_task, args=(loop, callback_on_serving_cube))
  t.start()
  return t
  # try :
  #   future = executor.submit(cube_task, loop, callback_on_serving_cube)
  #   _is_serving.wait()
  #   return future
  # except :
  #   loop.close()
  #   raise


def icon_start():
  """"""
  try:
    image = Image.open(ICON_FILE)
    submenu_log = Menu(MenuItem('Display', icon_menu_log_display), MenuItem(
        'Save As', icon_menu_log_save_as), MenuItem('Open Folder', icon_menu_log_open_folder))
    menu = Menu(MenuItem('Log', submenu_log), MenuItem('Quit', quit))
    icon = Icon("onlineMed Cube", icon=image,
                menu=menu, title='OnlineMed Cube')

    # future = executor.submit(icon.run)
    # return future, icon

    t = Thread(target=icon.run)
    t.start()
    return t, icon
  except:
    logger.exception(f"icon create has occured exception.")
  return None

exit_code = -1
try:
  cube_thread = cube_start()

  try :
    icon_thread = None
    icon = None
    result = icon_start()
    if result is not None:
      icon_thread, icon = result
    try :
      while not _g_stop_event.is_set() :
        if not cube_thread.is_alive() :
          logger.info(f"cube_thread done.")
          break
        if icon_thread is not None :
          if not icon_thread.is_alive():
            logger.info(f"icon_thread done.")
            break
        time.sleep(0.1)
      logger.info(f"loop exit.")
    finally :
      logger.info(f"loop finally.")
      quit(icon)
      logger.info(f"icon quit.")
      icon_thread.join()
      logger.info(f"icon stop.")
  finally :
    cube_thread.join()

  exit_code = 0

except KeyboardInterrupt:
  if logger.level < logging.INFO :
    logger.exception('cube.__main__.KeyboardInterrupt')
  else:
    logger.info('cube.__main__.KeyboardInterrupt')
  if os.name == 'posix':
    print()
  else :
    print('^C')
  exit_code = -1
except:
  logger.exception('cube.__main__.except')
  exit_code = -1
finally:
  logger.debug('cube.__main__.finnally')

  try :
    while True:
      is_there_not_daemon_thread = False
      for thread in threading.enumerate():
        if thread is threading.current_thread():
          logger.info(f"--current:{thread}")
        else :
          logger.info(thread)
          if not thread.daemon :
            is_not_there_daemon_thread = True
      logger.info("--")
      if is_there_not_daemon_thread:
        time.sleep(1.0)
      else :
        break
  except KeyboardInterrupt:
    if os.name == 'posix':
      print()
    else:
      print('^C')
  finally :
    pass
    logger.debug('cube.__main__ final')
    # quit(_g_icon)

sys.exit(exit_code)
