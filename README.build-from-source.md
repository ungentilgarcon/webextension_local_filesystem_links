# Build from source: webextension_local_filesystem_links

1. Extract source code archive

2. Install dependencies:

    \$ npm install
    ...
    added 1208 packages in 25.165s

3. Generate the production version of the Firefox extension in the `dist` folder:

    \$ npm run build
    ...
    DONE Compiled successfully in 4841ms

4. Generate the Firefox add-on ZIP in the `web-ext-artifacts` folder:

    \$ npm run bundle
    ...
    Your web extension is ready: /home/gregor/dev/src/firefox_addon/sourcecode-archive/web-ext-artifacts/local_filesystem_links-0.99.60.zip

5. On Windows, build the native messaging host and its installer separately. Install the Python 2 dependencies from `native-host/requirements.txt`, ensure PyInstaller and Inno Setup 6 are available, then from `native-host/` run:

    $ sh build/build.sh
    $ ISCC.exe build/windows/InnoSetupScript.iss

    The installer is written to `native-host/bin/win32/native-app-setup.exe`.

6. Manually upload the Firefox ZIP here: https://addons.mozilla.org/en-US/developers/addon/local-filesystem-links/versions
    - Upload Version -> Select a file...
    - Troubleshooting:
        - red message: "Version 0.99.58 was uploaded before and deleted". No hint what to do next.
        - solution: upload new version 0.99.59 (npm run build, npm run bundle, upload the file)
    - Follow the instructions and provide source code
        - \$ ./make-sourcecode-archive.sh

## Older stuff

-   One-time: Install [web-ext](https://developer.mozilla.org/en-US/Add-ons/WebExtensions/Getting_started_with_web-ext) with `npm install web-ext`.
-   Find API key hiere: See Tools > Manage API Keys (https://addons.mozilla.org/en-US/developers/addon/api/key/)

    \$ ./node_modules/web-ext/bin/web-ext sign --api-key=userkey --api-secret=... -s dist
