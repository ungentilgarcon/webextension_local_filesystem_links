import checkInstallation from './checkInstallation';
import { updateAddonbarIcon } from './addonbarIcon';
import { ExtensionEventHandlers } from './EventHandlers';

/** Main background script class of the extension */
class LocalFileSystemExtension {
    /** Initialize the extension
     */
    constructor() {
        this.settings = {};
        this.eventHandlers = new ExtensionEventHandlers(this.settings);
        this.addListeners();
    }

    /** Add eventlisteners of the extension
     * @returns {undefined}
     */
    addListeners() {
        // add message handling
        browser.runtime.onMessage.addListener(
            this.eventHandlers.onMessage.bind(this)
        );

        const checkPage = () => {
            updateAddonbarIcon(false); // always toggle to inactive
            this.checkUrls();
        };

        browser.windows.onCreated.addListener(checkPage); // initial load of firefox
        browser.tabs.onActivated.addListener(checkPage); // switched between tabs
        browser.windows.onFocusChanged.addListener(checkPage); // switched from other window
        checkPage();

        const updateHandler = (tabId, changeInfo, tab) => {
            if (tab.active && changeInfo.status === 'complete') {
                this.checkUrls();
            }
        };

        browser.tabs.onUpdated.addListener(updateHandler);

        // check if first installation or update
        browser.runtime.onInstalled.addListener(checkInstallation);
    }
    /** Check the urls (if active tab is whitelisted)
     * @returns {undefined}
     */
    checkUrls() {
        // load settings from local storage
        browser.storage.local
            .get()
            .then(settings =>
                this.eventHandlers.onSettingsLoaded(
                    settings,
                    this.loadExtension.bind(this)
                )
            );
    }

    /** Load the extension if query matches whitelist
     * @param {object} settings loaded app settings
     * @param {array} whitelist contains urls that are whitelisted
     * @returns {undefined}
     */
    loadExtension(settings, whitelist) {
        const excludeFileExtensions = ['.xml'];

        // set settings
        this.settings = settings;

        const queryCallback = tabs => {
            if (!tabs || tabs.length === 0) {
                updateAddonbarIcon(false);
                return; // no match
            }

            const activeTab = tabs.filter(tab => tab.active)[0];

            if (!activeTab) {
                updateAddonbarIcon(false);
                // console.log('no active tab');
                // needed if tab is newly removed from the whitelist --> stop active content script
                // --> removed below as it was causing an issue with multiple events. Removing means a whitelist change requires a page reload. Acceptable behaviour.
                // Note: Also an unfocused window will also trigger this case
                return; // no tab active --> e.g. about:addons
            }

            if (
                excludeFileExtensions.some(
                    val => activeTab.url.indexOf(val) !== -1
                )
            ) {
                updateAddonbarIcon(false);
                // don't enhance xml files = don't affect xml viewer
                // array so it's easily possible to add more excludes
                return;
            }

            // show enhancement at addon bar icon
            updateAddonbarIcon(true);
        };

        // execute query
        browser.tabs
            .query({
                active: true,
                lastFocusedWindow: true,
                url: whitelist
            })
            .then(tabs => queryCallback(tabs))
            .catch(ExtensionEventHandlers.onError);
    }
}

// start extension's background script
const extension = new LocalFileSystemExtension();
