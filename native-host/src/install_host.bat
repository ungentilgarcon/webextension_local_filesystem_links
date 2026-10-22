:: Copyright 2014 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: Change HKCU to HKLM if you want to install globally.
:: %~dp0 is the directory containing this bat script and ends with a backslash.
set "HOST_MANIFEST=%~dp0webextension_local_filesystem_links_win.json"
set "HOST_EXECUTABLE=%~dp0local-link-messaging-host.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$manifest = Get-Content -Raw -LiteralPath $env:HOST_MANIFEST | ConvertFrom-Json; $manifest.path = $env:HOST_EXECUTABLE; $json = ConvertTo-Json -InputObject $manifest -Depth 5; [System.IO.File]::WriteAllText($env:HOST_MANIFEST, $json, (New-Object System.Text.UTF8Encoding($false)))"
if errorlevel 1 (
  echo Failed to write native messaging host manifest.
  exit /b 1
)
REG ADD "HKCU\Software\Mozilla\NativeMessagingHosts\webextension_local_filesystem_links" /ve /t REG_SZ /d "%~dp0webextension_local_filesystem_links_win.json" /f
if errorlevel 1 exit /b 1
