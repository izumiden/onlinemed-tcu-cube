#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import configparser
import subprocess
import os

class _config(object) :

  def __init__(self) :
    pass


def is_process(name) :
    """
    2重起動 防止

    Attributes
    ----------
    name : str
        プロセス名称(pythonソースファイル名)
        例)
        import os
        import application
        file_name = os.path.basename(__file__)
        if application.is_process(file_name) :
            print("process is running.")
            exit()
    """
    if os.name == 'posix' :
      with subprocess.Popen(
              ["ps", "-ef"], stdout=subprocess.PIPE) as p1 :
          with subprocess.Popen(
                  ["grep", name], stdin=p1.stdout, stdout=subprocess.PIPE) as p2 :
              with subprocess.Popen(
                      ["grep", "python"], stdin=p2.stdout, stdout=subprocess.PIPE) as p3 :
                  with subprocess.Popen(
                          ["wc", "-l"], stdin=p3.stdout, stdout=subprocess.PIPE) as p4 :

                      output = p4.communicate()[0].decode("utf8").replace('\n','')
                      if int(output) != 1:
                          return True
                      return False
    else :
       return False


# 指定したiniファイルが存在しない場合、エラー発生
if not os.path.exists('config.ini'):
  configs = {'DEFAULT':{}}
else :
  configs = configparser.ConfigParser()
  configs.read('config.ini', encoding='utf-8')
  # for section in configs.sections() :
  #   sectobj = _config()
  #   for option in configs.options(section) :
  #     str_value = configs.get(section, option)
  #     # convert to boolean
  #     if 'true' == str_value.lower() :
  #       value = True
  #     elif 'false' == str_value.lower() :
  #       value = False
  #     else :
  #       try :
  #         # convert to decimal
  #         if str_value.isdecimal() :
  #           value = int(str_value)
  #         else :
  #           value = float(str_value)
  #       except ValueError :
  #         try :
  #           # convert to ip address
  #           value = ipaddress.ip_address(str_value)
  #         except ValueError :
  #           value = str_value

  #     # print(section.lower(), option, value, type(value))
  #     setattr(sectobj, option, value)
  #   setattr(configs, section.lower(), sectobj)

# if __name__ == '__main__':
#   print(configs.tcu.model)
