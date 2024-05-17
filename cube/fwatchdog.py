#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from genericpath import isdir
import os
from watchdog.events import EVENT_TYPE_MOVED, EVENT_TYPE_DELETED, EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED
from watchdog.events import FileSystemEvent
from watchdog.events import PatternMatchingEventHandler
import watchdog.observers
from logging import getLogger, DEBUG, INFO

from threading import Thread
from threading import Event, Lock
import time

logger = getLogger(__name__)
logger.setLevel(DEBUG)

FILE_EVENT_CREATED = EVENT_TYPE_CREATED
FILE_EVENT_MODIFIED = EVENT_TYPE_MODIFIED
FILE_EVENT_DELETED = EVENT_TYPE_DELETED
FILE_EVENT_MOVED = EVENT_TYPE_MOVED


def is_created(event: FileSystemEvent):
  return (event.event_type == EVENT_TYPE_CREATED)


def is_modified(event: FileSystemEvent):
  return (event.event_type == EVENT_TYPE_MODIFIED)


def is_deleted(event: FileSystemEvent):
  return (event.event_type == EVENT_TYPE_DELETED)


def is_moved(event: FileSystemEvent):
  return (event.event_type == EVENT_TYPE_MOVED)


class Observer(Thread):

  def __init__(self, filepath, recursive: bool = False, fixed_interval: float = 0.1, *, daemon=None):
    super().__init__(daemon=daemon)
    if os.path.isdir(filepath):
      dirname = filepath
      filename = '*'
    else:
      dirname = os.path.dirname(filepath)
      filename = os.path.basename(filepath)

    self._tm = time.time()
    self._do = False
    self._file_event_lock = Lock()
    self._file_event = Event()
    self.on_file_event = Event()
    self.on_created_event = Event()
    self.on_deleted_event = Event()
    self.on_modified_event = Event()
    self.on_moved_event = Event()
    self._file_system_event = None
    self._event_file_system_event = None

    self._fixed_interval = fixed_interval

    event_handler = PatternMatchingEventHandler([filename], ignore_directories=True)
    event_handler.on_created = self._on_created
    event_handler.on_deleted = self._on_deleted
    event_handler.on_modified = self._on_modified
    event_handler.on_moved = self._on_moved
    self._observer = watchdog.observers.Observer()
    self._observer.schedule(event_handler, dirname, recursive=recursive)

  def __enter__(self) -> object:
    self.start()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.stop()
    self.join()

  def run(self) :
    try :
      self._observer.start()
      self._do = True

      while self._do :
        if self._file_event.wait(self._fixed_interval):
          with self._file_event_lock:
            if self._file_system_event \
                    and self._file_system_event.event_type == EVENT_TYPE_DELETED:
              self._on_event(self._file_system_event)
              self._file_system_event = None
            self._file_event.clear()
        else:
          with self._file_event_lock:
            if self._file_system_event:
              self._on_event(self._file_system_event)
              self._file_system_event = None
    except:
      logger.exception("")
    finally :
      try :
        if self._observer.is_alive() :
          self._observer.stop()
          self._observer.join()
      except :
        logger.exception("")


  def stop(self) :
    self._do = False

  def is_set(self):
    return self.on_file_event.is_set()

  def clear(self):
    self._event_file_system_event = None
    return self.on_file_event.clear()

  def wait(self, timeout=None):
    return self.on_file_event.wait(timeout)

  def get_event(self):
    return self._event_file_system_event

  def on_any_event(self, event):
    """Catch-all event handler.

    :param event:
        The event object representing the file system event.
    :type event:
        :class:`FileSystemEvent`
    """
    logger.debug(f'call on_any_event {event}')

  def on_created(self, event):
    """Called when a file or directory is created.

    :param event:
        Event representing file/directory creation.
    :type event:
        :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
    """
    logger.debug(f'call on_created {event}')

  def on_deleted(self, event):
    """Called when a file or directory is deleted.

    :param event:
        Event representing file/directory deletion.
    :type event:
        :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
    """
    logger.debug(f'call on_created {event}')

  def on_modified(self, event):
    """Called when a file or directory is modified.

    :param event:
        Event representing file/directory modification.
    :type event:
        :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
    """
    logger.debug(f'call on_modified {event}')

  def on_moved(self, event):
    """Called when a file or a directory is moved or renamed.

    :param event:
        Event representing file/directory movement.
    :type event:
        :class:`DirMovedEvent` or :class:`FileMovedEvent`
    """
    logger.debug(f'call on_moved {event}')

  def _on_event(self ,event:FileSystemEvent):
    self._event_file_system_event = event

    self.on_file_event.set()
    self.on_any_event(self._file_system_event)

    if self._file_system_event.event_type == EVENT_TYPE_CREATED:
      self.on_created_event.set()
      self.on_created(self._file_system_event)
    elif self._file_system_event.event_type == EVENT_TYPE_DELETED:
      self.on_deleted_event.set()
      self.on_deleted(self._file_system_event)
    elif self._file_system_event.event_type == EVENT_TYPE_MODIFIED:
      self.on_modified_event.set()
      self.on_modified(self._file_system_event)
    elif self._file_system_event.event_type == EVENT_TYPE_MOVED:
      self.on_moved_event.set()
      self.on_moved(self._file_system_event)

  def _file_event_set(self, event:FileSystemEvent) :
    if not isinstance(event, FileSystemEvent) :
      raise ValueError(f'event is not FileSystemEvent. event was {event}')
    with self._file_event_lock :
      self._file_system_event = event
      self._file_event.set()

  def _on_created(self, event):
    try :
      if not event.is_directory:
        filepath = event.src_path
        filename = os.path.basename(filepath)
        logger.debug(f'on_created {filename} {event.event_type}')

        self._file_system_event = event
        self._file_event.set()
    except:
      logger.exception("")

  def _on_deleted(self, event):
    try:
      if not event.is_directory:
        filepath = event.src_path
        filename = os.path.basename(filepath)
        logger.debug(f'on_deleted {filename} {event.event_type}')

        self._file_system_event = event
        self._file_event.set()
    except:
      logger.exception("")

  def _on_modified(self, event):
    try:
      if not event.is_directory:
        filepath = event.src_path
        filename = os.path.basename(filepath)
        logger.debug(f'on_modified {filename} {event.event_type}')

        if self._file_system_event :
          if self._file_system_event.event_type not in ('created', 'moved'):
            self._file_system_event = event
        else :
          self._file_system_event = event
        self._file_event.set()
    except:
      logger.exception("")

  def _on_moved(self, event):
    try:
      if not event.is_directory:
        src_path = event.src_path
        src_filename = os.path.basename(src_path)
        dest_path = event.dest_path
        dest_filename = os.path.basename(dest_path)
        logger.debug(
            f'on_moved {src_filename} to {dest_filename} {event.event_type}')
        self._file_system_event = event
        self._file_event.set()
    except:
      logger.exception("")


def observe(filepath: str | None = ..., recursive: bool = False, fixed_interval: float = 0.1) -> Observer:
  logger.info(filepath)
  observer = Observer(filepath, recursive, fixed_interval)
  return observer


if __name__ == "__main__":
  import logging
    
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(name)s : %(message)s'
                      )

  path = '/home/pi/Public/message.ini'

  observer = observe(path)
  try:
    observer.start()
    while True:
      observer.wait()
      observer.clear()
      logger.info(f'observer event!')
  except KeyboardInterrupt:
    observer.stop()
  observer.join()
  print("")
