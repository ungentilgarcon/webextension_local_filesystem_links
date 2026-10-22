# Local Filesystem Links

Local Filesystem Links lets Firefox open `file://` links using the computer's
normal file handler or file manager. **To make it work, install both the Firefox
add-on and the native host for your operating system.**

## Quick setup

### 1. Install the Firefox add-on

-   [Install Local Filesystem Links from Firefox Add-ons (AMO)](https://addons.mozilla.org/firefox/addon/local-filesystem-links/).
-   Alternatively, download the [signed Firefox add-on ZIP](https://github.com/ungentilgarcon/webextension_local_filesystem_links/releases/latest/download/local_filesystem_links-0.101.5.zip)
    from the [latest release](https://github.com/ungentilgarcon/webextension_local_filesystem_links/releases/latest).

### 2. Install the native host

The add-on needs this small companion application to open files outside the
browser:

-   **Windows:** [Download and run the native-host installer](https://github.com/ungentilgarcon/webextension_local_filesystem_links/releases/latest/download/native-app-setup.exe).
    Diagnostic logging is optional in the installer and off by default.
-   **Linux:** There is no prebuilt Linux native-host download in the current
    release. Linux users need to build and install it from source; see
    [Linux native-host setup](README.build-from-source.md#linux-native-host).

The browser add-on ZIP is the same whichever operating system you use. Only the
native host is operating-system specific. The current public release provides a
Windows installer; check [all release assets](https://github.com/ungentilgarcon/webextension_local_filesystem_links/releases)
before installing to see whether a Linux package has since been published.

### Browser support

The supported ready-to-install browser is **Firefox**. A Chrome manifest is
included for development, but this release does not provide a supported Chrome
package or register the native host for Chrome. Follow the Firefox instructions
above; installing the Firefox package in Chrome will not make native links work.

## Configure a network fallback server

Use this when a link has no server name and the network share cannot be resolved
from the current computer. For example, a page may contain:

```text
file:///dfsburo/Donnees/DGRT/DSI/ENT/Dossier%20ORIGINALB_RAEP_a%20imprimer%20-%20pour%20fusion.docx
```

On Windows, that unqualified URL is initially interpreted as a UNC path such as
`\\dfsburo\Donnees\...`. If the reachable server is `villeurbanne.fr`, configure
the fallback as follows:

1. In Firefox, open the Local Filesystem Links toolbar button and choose
   **Change settings...**.
2. In **Fallback server for unqualified network links**, enter only:
   `villeurbanne.fr`
3. Save/close settings, then retry the link.

When the original unqualified path cannot be opened, the add-on retries it using
the fallback server. The example resolves to:

```text
Windows: \\villeurbanne.fr\dfsburo\Donnees\DGRT\DSI\ENT\Dossier ORIGINALB_RAEP_a imprimer - pour fusion.docx
Linux:   //villeurbanne.fr/dfsburo/Donnees/DGRT/DSI/ENT/Dossier ORIGINALB_RAEP_a imprimer - pour fusion.docx
```

Enter a hostname only: **do not** include `file://`, `https://`, slashes, a
share name, or a folder path. The fallback is only for unqualified network
links; explicit server links such as `file://villeurbanne.fr/dfsburo/Donnees/file.docx`
and local drive paths such as `file:///C:/Documents/file.docx` are left unchanged.
The computer must still have network access and permission to reach the share.

## Using the add-on

The add-on detects `file://` links on pages where it is enabled. Clicking a link
opens the file with the operating system's associated application. The toolbar
settings let you choose whether the default link action opens a file or reveals
it in its containing folder, and let you restrict link handling with a page
whitelist. A whitelist value of `*` enables all pages; an empty value disables
all pages.

Supported path details include:

-   Windows drive-letter links, for example `file:///C:/Documents/file.docx`.
-   Windows network links, for example `file://server/share/folder/file.docx`.
-   Percent-encoded filename characters such as `%20` for spaces.
-   An optional fallback server for unqualified network links, as described above.

## Troubleshooting

-   Confirm that both the Firefox add-on and native host are installed. Restart
    Firefox after installing the native host.
-   Confirm the target file/share is reachable from the computer running Firefox.
    A fallback hostname cannot grant access to a server or share the user cannot
    already reach.
-   Confirm the page is allowed by the add-on's whitelist.
-   On Windows, diagnostic logging can be selected during installation. When
    enabled, the native host writes to
    `%LOCALAPPDATA%\LocalFilesystemLinks\native-host.log`; logging is off by
    default.

## Project and development

The repository contains the Firefox extension source in `src/`, native-host
source in `native-host/`, tests in `test/`, and additional documentation in
`doc/`. See [README.dev.md](README.dev.md) for development and
[README.build-from-source.md](README.build-from-source.md) for production and
Linux native-host build details.

## License

-   GPLv3 or later
-   Mozilla Public License v2 or later

## Donations

ungentilgarcon is the current maintainer and main contributor. To support
ongoing development and maintenance, [contribute via PayPal](https://paypal.me/ungentilgarcon).
