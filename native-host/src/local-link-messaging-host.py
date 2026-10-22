#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# A native messaging host.

import struct
import sys
import json
import urllib
import subprocess
from subprocess import PIPE
import os
import re

currentOS = sys.platform

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
  # import win32api # if active state python is installed or install pywin32 package seperately
  import os, msvcrt
  import sys
  # from get_binary_type import GetBinaryType
  import pywintypes
  import win32api
  from subprocess_fix import Popen

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
  from subprocess import Popen
  
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
   # Write message size.
  sys.stdout.write(struct.pack('I', len(message)))
  # Write the message itself.
  sys.stdout.write(message)
  sys.stdout.flush()

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

  # pathStr = urllib.unquote(pathStr).decode('utf8')   # why was this here?
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
        Popen(["explorer.exe", "/select,", pathStr])
      else:
        os.startfile(pathStr)
      return

    if reveal:
      command = fileExplorer['reveal']['cmd'] + ' ' + fileExplorer['reveal']['arg'] + "\"%s\"" % pathStr
    else:
      command = fileExplorer['open'] + " \"%s\"" % pathStr
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.communicate()

# Thread that reads messages from the webapp.
def read_thread_func(queue):
  message_number = 0
  while 1:
    # Read the message length (first 4 bytes).
    text_length_bytes = sys.stdin.read(4)

    if len(text_length_bytes) == 0:
      sys.exit(0)

    # Unpack message length as 4 byte integer.
    text_length = struct.unpack("i", text_length_bytes)[0]

    # Read the text (JSON object) of the message.
    text = sys.stdin.read(text_length).decode('utf-8')

    data = json.loads(text)

    fileStr = data['url']
    reveal = data['reveal']

    exeAllowed = data['exeAllowed']
    # send_message(u"{\"debug\": \"%s\"}" % urllib.quote(fileStr.encode('utf-8')))
    if (checkPath(fileStr)):
      result = getFilePath(fileStr, exeAllowed)
      if result is None:
        send_json({"error": "ERROR_EXECTUBALES_NOT_ENABLED"})
      else:
        try:
          if (reveal):
            openFile(result, True)
          else:
            openFile(result)
          send_json({"error": None})
        except Exception as err:
          send_json({
            "error": "ERROR_OPEN_FAILED",
            "url": fileStr,
            "detail": str(err)
          })
    else:
      # send_message(u"{\"debug not found\": \"%s\"}" % urllib.quote(fileStr.encode('utf-8')))
      if (reveal):
        result = getFilePath(fileStr, exeAllowed)
        if result is None:
          send_json({"error": "ERROR_EXECTUBALES_NOT_ENABLED"})
        else:
          try:
            openFile(os.path.dirname(result))
            send_json({"error": None})
          except Exception as err:
            send_json({
              "error": "ERROR_OPEN_FAILED",
              "url": fileStr,
              "detail": str(err)
            })
      else:
        send_json({
          "error": "ERROR_BAD_LINK",
          "url": fileStr
        })

    sys.exit(0)

def Main():
  read_thread_func(None)
  sys.exit(0)

if __name__ == '__main__':
  Main()
