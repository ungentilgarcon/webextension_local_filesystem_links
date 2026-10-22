import * as CONSTANTS from '../constants';
import { showInstallationTab } from './checkInstallation';
import notify from './notify';
import { prepareWhitelist } from './helpers/whitelist';

const { defaultSettings, DELAY_BETWEEN_RETRIES } = CONSTANTS;

/** Event handler methods of the extension */
export class ExtensionEventHandlers {
    /** Initialize EventHandler
     * @param {object} settings reference to app settings.
     */
    constructor(settings) {
        this.settings = settings;
        this.retriesOnFailure = 0;
    }

    /** Global Error handler
     *  @param {object} err error object
     *  @returns {undefined}
     */
    static onError(err) {
        // console.log('error handler:', err.name, err.message, err.stack,
        // err.lineNumber); // todo - check that really the connection to the native app isn't open
        const nativeAppNotInstalled = err.message.includes('disconnected port')
            ? ' Please check that you have installed the native app. ' +
              'See installation guide in addon-bar ' +
              'menu.'
            : '';

        // console.log('error', err);
        notify(err.name, err.message + '.' + nativeAppNotInstalled);
    }

    /**
     * Send native message with retries
     * @param {object} request
     * @param {string} uri
     */
    static sendNativeMessage(request, uri, handler) {
        browser.runtime
            .sendNativeMessage(
                // direct sending --> opens port to native app
                'webextension_local_filesystem_links',
                {
                    url: uri,
                    reveal: request.reveal,
                    exeAllowed: handler.settings.enableExecutables
                }
            )
            .then(function(response) {
                // console.log('received response', response);
                if (response && response.error) {
                    if (
                        handler.retriesOnFailure >=
                        handler.settings.retriesOnFailure
                    ) {
                        console.error(
                            'Native messaging host returned an error',
                            {
                                uri,
                                response
                            }
                        );
                        const url = response.url
                            ? window.decodeURI(response.url)
                            : '';
                        const messageKey =
                            response.error === 'ERROR_NATIVE_HOST'
                                ? 'ERROR_NATIVE_HOST'
                                : response.error === 'ERROR_OPEN_FAILED'
                                ? 'ERROR_OPEN_FAILED'
                                : response.error;
                        const substitutions =
                            messageKey === 'ERROR_NATIVE_HOST'
                                ? [
                                      url,
                                      response.errorType || 'UnknownError',
                                      response.detail || ''
                                  ]
                                : messageKey === 'ERROR_OPEN_FAILED'
                                ? [url, response.detail || '']
                                : url;
                        const msg =
                            browser.i18n.getMessage(
                                messageKey,
                                substitutions
                            ) ||
                            response.detail ||
                            response.error;

                        notify(
                            'Native host error',
                            response.detail && messageKey === 'ERROR_BAD_LINK'
                                ? msg + '\n' + response.detail
                                : msg,
                            10000
                        );
                    } else {
                        setTimeout(() => {
                            ExtensionEventHandlers.sendNativeMessage(
                                request,
                                uri,
                                handler
                            );
                            handler.retriesOnFailure++;
                        }, DELAY_BETWEEN_RETRIES);
                    }
                }
            })
            .catch(err => {
                console.error('Native messaging host launch failed', {
                    uri,
                    error: err
                });
                const nativeAppNotInstalled = err.message.includes(
                    'disconnected port'
                )
                    ? ' Please check that you have installed ' +
                      'the native app. ' +
                      'See installation guide in addon-bar ' +
                      'menu.'
                    : '';

                notify(
                    'Native messaging host error',
                    [
                        err.name + ': ' + err.message,
                        'URL: ' + uri,
                        'If the host started, check %LOCALAPPDATA%\\LocalFilesystemLinks\\native-host.log.',
                        err.stack || ''
                    ]
                        .filter(Boolean)
                        .join('\n'),
                    10000
                );
            });
    }

    /**
     * Handler for content script messages
     * @param {object} request information about the request (e.g. action)
     * @param {object} sender sender info
     * @param {callback} sendResponse sends response to content script.
     * @returns {undefined}
     */
    onMessage(request, sender, sendResponse) {
        switch (request.action) {
            case 'initializeContent':
                if (!sender.tab) {
                    sendResponse(null);
                    break;
                }
                if (sender.tab.url && sender.tab.url.indexOf('.xml') !== -1) {
                    sendResponse(null);
                    break;
                }

                browser.storage.local
                    .get()
                    .then(settings =>
                        this.onSettingsLoaded(
                            settings,
                            (loadedSettings, whitelist) => {
                                browser.tabs
                                    .query({ url: whitelist })
                                    .then(tabs => {
                                        if (
                                            !tabs.some(
                                                tab => tab.id === sender.tab.id
                                            )
                                        ) {
                                            sendResponse(null);
                                            return;
                                        }

                                        return Promise.all(
                                            [
                                                'css/self-hosted-materialize.css',
                                                'css/style.css'
                                            ].map(file =>
                                                browser.tabs.insertCSS(
                                                    sender.tab.id,
                                                    {
                                                        file,
                                                        frameId: sender.frameId,
                                                        matchAboutBlank: true
                                                    }
                                                )
                                            )
                                        ).then(() => {
                                            sendResponse({
                                                options: {
                                                    enableLinkIcons:
                                                        loadedSettings.enableLinkIcons,
                                                    revealOpenOption:
                                                        loadedSettings.revealOpenOption
                                                },
                                                constants: JSON.parse(
                                                    JSON.stringify(CONSTANTS)
                                                )
                                            });
                                        });
                                    })
                                    .catch(err => {
                                        console.error(
                                            'Failed to initialize Local Filesystem Links content script',
                                            err
                                        );
                                        sendResponse({ error: err.message });
                                    });
                            }
                        )
                    )
                    .catch(err => {
                        console.error(
                            'Failed to load Local Filesystem Links settings',
                            err
                        );
                        sendResponse({ error: err.message });
                    });
                return true;
            case 'showInstallInfoTab':
                showInstallationTab();
                break;
            case 'open':
                var uri = request.url;
                console.log('opening', uri);

                if (request.directOpen) {
                    // setting commented at the moment --> re-add later
                    browser.tabs.create({
                        active: true,
                        url: window.decodeURI(uri) // illegal URL --> not priveleged to add file:// - fix later
                    });
                } else {
                    this.retriesOnFailure = 0; // reset failure count
                    ExtensionEventHandlers.sendNativeMessage(
                        request,
                        uri,
                        this
                    );
                }
                break;
            default:
        }
    }

    /** Handler for app settingss loaded
     * @param {object} settings reference to settings of extension
     * @param {function} callback do somehing with the loaded settings
     * @returns {undefined}
     */
    onSettingsLoaded(settings, callback) {
        const loadedSettings = Object.assign({}, defaultSettings, settings);
        this.settings = loadedSettings;
        const whitelist = loadedSettings.whitelist.trim()
            ? prepareWhitelist(loadedSettings.whitelist.trim())
            : [];
        // const whitelist = ['*']; //['http://127.0.0.1:3000/*', '*://*.localhost/*', '*://*.google.de/*', '*://*.trello.com/*'];

        callback(loadedSettings, whitelist);
    }
}
