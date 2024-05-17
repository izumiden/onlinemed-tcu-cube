#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import errno
from logging import getLogger
import os
import socket
import time
import threading

import utils


logger = getLogger(__name__)

def _client_thread(client, address, target) :

  logger.debug(f"[*] Connected!! [ Source : {address}]")
  message = client.recv(1024)
  if 0 < len(message) :
    logger.debug(f"[*] recived!! [{message}]")
    # parameter = pickle.loads(message)
    # message = message.decode('utf-8')
    if target is not None :
      target(client, address, message)

class Server(threading.Thread):
  """docstring for Server."""

  def __init__(self, address, port, *, num=5, target=None, daemon=None) :
    super().__init__(daemon=daemon)
    if os.name == 'posix':
      import netifaces
      if address in ("eth0", "wlan0"):
        iface = netifaces.ifaddresses(address)
        ipv4_addr = iface.get(netifaces.AF_INET)
        if ipv4_addr is not None :
          self._address = (ipv4_addr[0]['addr'], port)
          logger.info(
              f"TCP server was created from address {self._address} [{address}]")
        else:
          self._address = ("localhost", port)
          logger.info(f" {self._address} wasn't there,")
          logger.info(" so TCP server was created on localhost.")
      else :
        self._address = (address, port)
        logger.info(
            f"TCP server was created from address {self._address}")
    else :
      self._address = (address, port)
      logger.info(
          f"TCP server was created from address {self._address}")

    self._num = num
    self._target = target
    self._do = False
    self._listen = False

  def __enter__(self) :
    self.start()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  def run(self) :

    addr_in_use = False
    self._do = True
    while self._do :
      try :
        if addr_in_use :
          time.sleep(1)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock :
          sock.bind(self._address)
          sock.listen(self._num)
          if addr_in_use :
            addr_in_use = False
            logger.info(f"Address {self._address} bind success.")
            self._listen = True

          while self._do :
            try :
              client, address = sock.accept()
              try :
                thread = threading.Thread(target=_client_thread, args=(client, address, self._target))
              finally :
                client = None
                address = None
              thread.start()
            except (socket.herror, socket.gaierror, socket.timeout):
              raise
            except Exception:
              logger.exception(utils.location())

      except (socket.herror, socket.gaierror, socket.timeout) as e:
        utils.exception(logger)
        time.sleep(1)
      except OSError as oserr :
        if oserr.errno in (errno.EADDRINUSE, errno.WSAEADDRINUSE):
          logger.info(
              f"Address {self._address} already in use.wait for release address.")
          addr_in_use = True
        else :
          pass
      except :
        pass

  def stop(self) :
      if self._do :
          self._do = False
          try :
              with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                  s.connect(self._address)
          except (socket.herror, socket.gaierror, socket.timeout):
              pass

  def is_listen(self) :
    return self._listen

class Client(object):
  """docstring for Server."""

  def __init__(self, address, port) :

    logger.debug("tcp.Client.__init__()")
    if os.name == 'posix':
      if address in ("eth0", "wlan0"):
        iface = netifaces.ifaddresses(address)
        ipv4_addr = iface.get(netifaces.AF_INET)
        if ipv4_addr is not None :
          self._address = (ipv4_addr[0]['addr'], port)
          logger.debug(f"TCP crient was created from address {self._address} [{address}]")
        else :
          self._address = ("localhost", port)
          logger.debug(f" {self._address} wasn't there,")
          logger.debug( " so TCP crient was created on localhost.")
      else :
        self._address = (address, port)
        logger.debug(f"TCP crient was created from address {self._address}")
    else:
      self._address = (address, port)
      logger.debug(f"TCP crient was created from address {self._address}")

    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.debug("socket.socket(socket.AF_INET, socket.SOCK_STREAM)")


  def __enter__(self) :
      return self

  def __exit__(self, exc_type, exc_value, traceback):
      self._socket = None

  def settimeout(self, timeout) :
    self._socket.settimeout(timeout)

  def send(self, args) :
    logger.debug(f"tcp.Client.send({args})")
    try :
      self._socket.connect(self._address)
      logger.debug(f"self._socket.connect({self._address})")
      try:
        # msg = pickle.dumps(args)
        msg = args.encode('utf-8')
        self._socket.send(msg)
        logger.debug(f"tcp.Client.send({msg})")
        resp = self._socket.recv(1024)
        response = resp.decode('utf-8')
        logger.debug(f"response ----->:{response}")
        return response
      finally :
        self._socket.close()
        logger.debug("tcp.Client._socket.close()")
    except (socket.herror, socket.gaierror, socket.timeout):
      pass
    except OSError:
      logger.exception(f"{utils.location()}\naddress:{self._address}")
    return None

if __name__ == '__main__':

  import json

  with Client("eth0", 8891) as c:
    c.send(json.dumps({"sw":
                        [{"swNo":1,"status":"off"},
                          {"swNo":2,"status":"off"},
                          {"swNo":3,"status":"off"}]}))
