#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# A native messaging host.

import struct
import sys
import json
from urllib.parse import unquote
import subprocess
from subprocess import PIPE
import os
import re
import logging
import traceback

currentOS = sys.platform
logger = logging.getLogger('local-filesystem-links-native-host')
LOG_PATH = None

def configure_logging():
  global LOG_PATH
  if getattr(sys, 'frozen', False):
    host_path = sys.executable
  else:
    host_path = sys.argv[0]
  logging_marker = os.path.join(
    os.path.dirname(os.path.abspath(host_path)),
    'logging.enabled'
  )
  if not os.path.isfile(logging_marker):
    return

  app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
  log_dir = os.path.join(app_data, 'LocalFilesystemLinks')
  try:
    if not os.path.isdir(log_dir):
      os.makedirs(log_dir)
    LOG_PATH = os.path.join(log_dir, 'native-host.log')
    logging.basicConfig(
      filename=LOG_PATH,
      level=logging.DEBUG,
      format='%(asctime)s %(levelname)s %(message)s'
    )
    logger.info('Native host started; Python=%s platform=%s', sys.version, sys.platform)
  except Exception:
    sys.stderr.write('Could not initialize native host log at %s\n' % log_dir)
    sys.stderr.write(traceback.format_exc())

if currentOS == "win32":
  configure_logging()

fileExplorers = {
  "win32": {
    "open": r'cmd /c',
    "reveal": {
      "cmd": r'cmd /c explorer',
      "arg": r'/select,'
    }
  },
  "linux": [{
    # Ubunutu
    "open": r'xdg-open',
    "reveal": {
      "cmd": r'nautilus', # not perfect to use directly nautilus but xdg-open is not supporting select option
      "arg": r'--select '
    }
  },
  {
    # Open SUSE
    "open": r'xdg-open',
    "reveal": {
      "cmd": r'dolphin',
      "arg": r'--select '
    }
  }],
  "mac": {
    "open": r'open',
    "reveal": {
      "cmd": r'open',
      "arg": r'--reveal '
    }
  }
}

fileExplorer = fileExplorers['linux'][1] # default to linux

# On Windows, the default I/O mode is O_TEXT. Set this to O_BINARY
# to avoid unwanted modifications of the input/output streams.
if currentOS == "win32":
  import msvcrt
  import pywintypes
  import win32api

  msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
  msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

  fileExplorer = fileExplorers['win32']

  def is_exe(fpath):
    # just msi files are still executed - com, exe, bat files are blocked
    # send_message('{"debug": "hello"}')
    # helpful resource http://timgolden.me.uk/python/win32_how_do_i/tell-if-a-file-is-executable.html
    try:
      # print "Looking at", filePath
      r, executable = win32api.FindExecutable(fpath)
      executable = win32api.GetLongPathName(executable).lower()
    except pywintypes.error:
      #   print "Neither executable nor document" # e.g. just a path
      return False
    else:
      return executable == fpath.lower()
else:
  Popen = subprocess.Popen
  
  # helper to check if cmd exists (e.g. Nautilus or Dolphin)
  def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True, 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

  # Helper for checking if file is exec. returns file if executable (for unix)
  def is_exe(fpath):
    return os.path.exists(fpath) and os.access(fpath, os.X_OK) and os.path.isfile(fpath)

  if sys.platform.startswith('linux'):
    fileExplorer = fileExplorers['linux']

    if cmd_exists(fileExplorer[0]['reveal']['cmd']):
      fileExplorer = fileExplorer[0]
    elif cmd_exists(fileExplorer[1]['reveal']['cmd']):
      fileExplorer = fileExplorer[1]
    else:
      # no match fallback to default -- just reveal not working
      fileExplorer = fileExplorer[0]
  elif sys.platform == 'darwin':
    fileExplorer = fileExplorers['mac']
    #send_message(u'{"debug os": "%s"}' % sys.platform) #urllib.quote(pathStr.encode('utf-8')))


# Helper function that sends a message to the webapp.
def send_message(message):
  output = sys.stdout.buffer
  output.write(struct.pack('<I', len(message)))
  output.write(message)
  output.flush()

def preparePath(pathStr):
  # replace backslashes to slashes
  pathStr = re.sub(r'\\', r'/', pathStr)
  # send_message('{"debug prepare": "%s"}' % pathStr.encode('utf-8'))

  if currentOS == "win32":
      file_uri = re.match(r'^file:(/+)(.*)$', pathStr, re.IGNORECASE)
      if file_uri:
          uri_path = file_uri.group(2)
          if re.match(r'^[a-zA-Z]:/', uri_path):
              pathStr = uri_path
          elif len(file_uri.group(1)) >= 2:
              pathStr = '//' + uri_path.lstrip('/')
          else:
              pathStr = uri_path
  else:
      pathStr = re.sub(r'[a-z]*:[\/]{2}', '', pathStr) # remove file://

  pathStr = unquote(pathStr, encoding='utf-8', errors='strict')
  if sys.platform.startswith('linux') or sys.platform == 'darwin':
    # hack to have ~ path working in Linux & mac os
    # one or two slashes before ~ // stop at first / after ~
    # unixPath = unixPath.replace(/(\/){1,2}~\//, '~/');  # code from previous addon
    pathStr = re.sub(r'[/]{1,2}~/', '~/', pathStr)
    pathStr = os.path.expanduser(pathStr) # expand ~ to home/username

  pathStr = os.path.normpath(pathStr) # normalize slashes ----- not working?
  return pathStr

# Helper for check if path or file exists
def checkPath(pathStr):
  pathStr = preparePath(pathStr)
  # send_message(u'{"debug before match": "%s"}' % urllib.quote(pathStr))
  # send_message(u'{"debug match": "%s"}' % pathStr.startswith('//'))
  return os.path.exists(pathStr)

def getFallbackPath(pathStr, fallbackServer):
  normalized_uri = re.sub(r'\\', '/', pathStr)
  match = re.match(r'^file:///(?!/)([^/]+)(/.*)?$', normalized_uri, re.IGNORECASE)
  if not match or re.match(r'^[a-zA-Z]:$', match.group(1)):
    return None

  fallbackServer = fallbackServer.strip()
  if not fallbackServer:
    return None
  if not re.match(r'^[A-Za-z0-9][A-Za-z0-9.-]*$', fallbackServer):
    raise ValueError('Fallback server must be a hostname without a scheme or path')

  fallback_path = '//' + fallbackServer + '/' + match.group(1)
  if match.group(2):
    fallback_path += match.group(2)
  return preparePath(fallback_path)

def getFilePath(program, exeAllowed):
  filePath = preparePath(program)

  if is_exe(filePath) is True and exeAllowed is False:
    return None
  else:
    return filePath

def send_json(message):
  send_message(json.dumps(message).encode('utf-8'))

def openFile(pathStr, reveal=False):
    if currentOS == "win32":
      if reveal:
        folderPath = os.path.dirname(pathStr)
        result = win32api.ShellExecute(
          0, u'open', folderPath, None, None, 5
        )
        if result <= 32:
          raise OSError('ShellExecute could not open folder (code %s)' % result)
        logger.info(
          'Windows shell accepted folder-open request with result=%s folder=%r',
          result, folderPath
        )
      else:
        os.startfile(pathStr)
      return

    if reveal:
      command = fileExplorer['reveal']['cmd'] + ' ' + fileExplorer['reveal']['arg'] + "\"%s\"" % pathStr
    else:
      command = fileExplorer['open'] + " \"%s\"" % pathStr
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.communicate()

def process_message(data):
    fileStr = data['url']
    reveal = data.get('reveal', False)
    exeAllowed = data.get('exeAllowed', False)
    fallbackServer = data.get('fallbackServer', '')
    logger.info('Received request: url=%r reveal=%r executables_allowed=%r fallback_server=%r',
                fileStr, reveal, exeAllowed, fallbackServer)

    try:
      resolvedPath = preparePath(fileStr)
      fallbackPath = None
      pathExists = os.path.exists(resolvedPath)
      if not pathExists:
        fallbackPath = getFallbackPath(fileStr, fallbackServer)
        if fallbackPath and os.path.exists(fallbackPath):
          resolvedPath = fallbackPath
          pathExists = True
    except (AttributeError, TypeError, ValueError) as err:
      logger.warning('Invalid fallback server setting: %r', fallbackServer)
      send_json({
        "error": "ERROR_BAD_FALLBACK_SERVER",
        "url": fileStr,
        "detail": str(err)
      })
      return

    if fallbackPath and pathExists:
      logger.info('Using fallback server path: %r', fallbackPath)

    if pathExists:
      result = getFilePath(resolvedPath, exeAllowed)
      if result is None:
        logger.warning('Rejected executable link: %r', fileStr)
        send_json({"error": "ERROR_EXECTUBALES_NOT_ENABLED", "url": fileStr})
      else:
        try:
          if (reveal):
            openFile(result, True)
          else:
            openFile(result)
          logger.info('Open request dispatched successfully: %r', result)
          send_json({"error": None})
        except Exception as err:
          logger.exception('Could not open requested path: %r', result)
          send_json({
            "error": "ERROR_OPEN_FAILED",
            "url": fileStr,
            "detail": traceback.format_exc(),
            "errorType": err.__class__.__name__
          })
    else:
      if (reveal):
        result = getFilePath(fileStr, exeAllowed)
        if result is None:
          logger.warning('Rejected executable reveal request: %r', fileStr)
          send_json({"error": "ERROR_EXECTUBALES_NOT_ENABLED", "url": fileStr})
        else:
          try:
            openFile(os.path.dirname(result))
            logger.info('Reveal request dispatched successfully: %r', result)
            send_json({"error": None})
          except Exception as err:
            logger.exception('Could not reveal requested path: %r', result)
            send_json({
              "error": "ERROR_OPEN_FAILED",
              "url": fileStr,
              "detail": traceback.format_exc(),
              "errorType": err.__class__.__name__
            })
      else:
        logger.error('Requested file path does not exist: %r', fileStr)
        detail = "Resolved filesystem path: %s" % resolvedPath
        if fallbackPath:
          detail += "; fallback path tried: %s" % fallbackPath
        send_json({
          "error": "ERROR_BAD_LINK",
          "url": fileStr,
          "detail": detail
        })

# Thread that reads messages from the webapp.
def read_thread_func(queue):
  input_stream = sys.stdin.buffer
  text_length_bytes = input_stream.read(4)
  if len(text_length_bytes) == 0:
    logger.info('Native messaging input closed before receiving a request')
    sys.exit(0)

  data = {}
  try:
    while len(text_length_bytes) < 4:
      more_bytes = input_stream.read(4 - len(text_length_bytes))
      if not more_bytes:
        raise EOFError('Incomplete native messaging frame header')
      text_length_bytes += more_bytes

    text_length = struct.unpack('<I', text_length_bytes)[0]
    payload = bytearray()
    while len(payload) < text_length:
      chunk = input_stream.read(text_length - len(payload))
      if not chunk:
        raise EOFError('Incomplete native messaging frame payload')
      payload.extend(chunk)
    text = payload.decode('utf-8')
    data = json.loads(text)
    logger.debug('Decoded native messaging request: %r', data)
    process_message(data)
  except Exception as err:
    logger.exception('Unexpected native host failure')
    try:
      url = data.get('url', '') if isinstance(data, dict) else ''
      send_json({
        "error": "ERROR_NATIVE_HOST",
        "url": url,
        "detail": traceback.format_exc(),
        "errorType": err.__class__.__name__
      })
    except Exception:
      sys.stderr.write(traceback.format_exc())

    sys.exit(0)

def Main():
  read_thread_func(None)
  sys.exit(0)

if __name__ == '__main__':
  Main()
