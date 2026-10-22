# local-filesystem-links

## Overview

This is the alien-local-filesystem-links extension for Mozilla Firefox.

It contains:

-   extension source code (src/)
-   native app source code (native-host/)
-   tests (test/)
-   documentation (doc/)

## Features

-   Adds a click event to every link that is including `file://` or `smb://` in `href` tag. (smb not working yet)
-   Shows a link icon close to the link. Icon can be disabled in preferences.
-   Dynamic loaded content supported because link events are delegated with `$(document).on(...)`
-   Content scripts are registered declaratively in each browser manifest and initialize only on pages matching the configured whitelist.
-   File links in dynamically loaded content and embedded frames are intercepted during the capture phase before page click handlers run.
-   Supports links with double and triple slashes (e.g. `file://` or `file:///`).
-   On Windows, `file:///dfsburo/Donnees/path.docx` opens the network share `\\dfsburo\Donnees\path.docx`; drive-letter links such as `file:///C:/path/file.docx` continue to work.
-   For a server-qualified network link, use `file://server/share/path`; for example, `file://villeurbanne.fr/dfsburo/Donnees/path.docx` maps to `\\villeurbanne.fr\dfsburo\Donnees\path.docx`. The host in the URL is significant.
-   An optional fallback server can be set in the extension settings for unqualified `file:///...` links. When the original path is unavailable, the host is prepended to the path; entering `villeurbanne.fr` maps `file:///dfsburo/Donnees/path.docx` to `\\villeurbanne.fr\dfsburo\Donnees\path.docx` on Windows (and `//villeurbanne.fr/dfsburo/Donnees/path.docx` on Linux). Existing local paths and server-qualified links are unchanged.
-   Percent-encoded filename characters (such as `%20` for spaces) are decoded before checking or opening the Windows path.
-   Windows opens documents through their registered file association; the reveal action selects the file in File Explorer.
-   Windows reveal requests use the ShellExecute API to open a new File Explorer window and select the requested file; failures are reported instead of being treated as successful launches.
-   Native-host failures include the URL and Python traceback in the extension notification and background console.
-   The Windows native host writes startup and request diagnostics to `%LOCALAPPDATA%\LocalFilesystemLinks\native-host.log`.
-   (Not available: Right click context menu that opens a text selection that contains a file link + option to reveal the directory of a directly linked file.)
-   Whitelist option to enable local links only at a specific url e.g. `*.trello.com`
-   Statusbar icon for displaying if links are active for current tab & for easier access to addon settings
-   Option to change the default text link behaviour (open or reveal)
-   Localization (current languages German, English, Russian)

## Screenshots

![Addon at local test server](/doc/screenshots/addon_in_action.png)
![Context menu](/doc/screenshots/addon_context_menu.png)

## License

-   GPLv3 or later
-   www.mozilla.org/MPL/ v2 or later

## Start developing

See README.dev.md

## Donations

If you like the extension and you want to support the development - please consider to donate. Any donations are greatly appreciated.

-   AWolf81 - current main developer:

    -   [Paypal.me to AWolf81](https://www.paypal.me/awlf81) (coding contributions)
    -   What are we doing with the donations?
        -   Buy a code signing certificate (needed for Windows) cost around 100 USD
        -   Incentive / motivation - this helps to stay motivated.

-   Feinstaub - original author and addon management:
    -   No direct donations possible yet (waiting for something private and decentrally organized like [GNU Taler](https://taler.net/en))
        -   [Some people do not use Paypal](https://github.com/feinstaub/webextension_local_filesystem_links/issues/98#issuecomment-357984115), maybe because of https://de.wikipedia.org/wiki/PayPal#Kritik
    -   Any donation that supports a Free Software community helps to maintain a technical and social environment where the development of software like this addon are possible. If you have no idea which community you would like to support, I recommend these organisations:
        -   **KDE**: https://www.kde.org/community/donations/others.php
            -   Vision: ["A world in which everyone has control over their digital life and enjoys freedom and privacy."](https://dot.kde.org/2016/04/05/kde-presents-its-vision-future)
            -   [supports Bitpay](https://bitpay.com/990273/donate)
        -   **Free Software Foundation**: https://www.fsf.org/about/ways-to-donate
        -   **Software Freedom Conservancy**: https://sfconservancy.org/donate
            -   ["helps promote, improve, develop, and defend Free, Libre, and Open Source Software (FLOSS) projects"](https://sfconservancy.org/about/)
        -   **Mozilla**: https://donate.mozilla.org/de/
    -   For Germany, there are related organisations which help Free Software indirectly by supporting the underlying values:
        -   **DigitalCourage**: https://digitalcourage.de/ueber-uns
            -   "Digitalcourage arbeitet für eine lebenswerte Welt im digitalen Zeitalter."
            -   "setzt sich seit 1987 für Grundrechte und Datenschutz ein"
        -   **Forum InformatikerInnen für Frieden und gesellschaftliche Verantwortung e.V.**: https://www.fiff.de
            -   "FIfF wurde 1984 [...] aus einer historischen Situation heraus gegründet, als es galt, das Schweigen einer Zunft zu brechen, die so maßgeblich an der Entwicklung automatisierter und informatisierter Kriegsführung beteiligt war."
