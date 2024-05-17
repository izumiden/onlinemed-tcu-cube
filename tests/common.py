# -*- coding: utf-8 -*-
import argparse
import logging

format = "%(asctime)s,%(name)s,%(levelname).3s,%(message)s"

logging.basicConfig(level=logging.DEBUG, format=format)

def ArgumentParser() -> argparse.ArgumentParser:
  argp = argparse.ArgumentParser()
  argp.add_argument("-d", "--debug", help="debug log output",
                    action="store_true")
  argp.add_argument("--log", type=str, default='INFO')
  return argp

def setlevel_for_root_logger(args: int | argparse.Namespace):

  if isinstance(args, argparse.Namespace):
    if getattr(args, 'debug') and args.debug:
      loglevel = logging.DEBUG
    else:
      if getattr(args, 'log'):
        loglevel = getattr(logging, args.log.upper(), None)
      else :
        return
  elif isinstance(args, int):
    loglevel = args
  else :
    raise TypeError(
        f"The args must be of type str or None. args:{args} type:{type(args)}")

  root_logger = logging.getLogger()
  root_logger.setLevel(loglevel)


def getLogger(name : str | None = None) -> logging.Logger :
  return logging.getLogger(name)

if __name__ == '__main__' :
  import pkgutil
  import tcu

  # パッケージ名を指定して、パッケージに含まれるサブパッケージの一覧を取得する
  packages_name = 'tcu'
  subpackages = [name for _, name, _ in pkgutil.iter_modules([packages_name])]

  # 結果を表示する
  print(f"{packages_name} subpackages{subpackages}")

  # パッケージ名を指定して、パッケージに含まれるサブパッケージの一覧を取得する
  subpackages = [name for _, name, _ in pkgutil.iter_modules(['tcu.relay'])]

  # 結果を表示する
  print(f"relay subpackages{subpackages}")

  # パッケージ名を指定して、パッケージに含まれるサブパッケージの一覧を取得する
  subpackages = [name for _, name, _ in pkgutil.iter_modules(['relay.client'])]

  # 結果を表示する
  print(f"relay.client subpackages{subpackages}")
