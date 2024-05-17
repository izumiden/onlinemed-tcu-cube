# -*- coding: utf-8 -*-
import sys

import cube

if __name__ == '__main__':
  print("app start.")
  try :
    cube.app.start()
    sys.exit(0)
  except:
    import logging
    logging.exception("")
    sys.exit(-1)
