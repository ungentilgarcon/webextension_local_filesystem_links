'use strict';

const windowsDrivePathPattern = /^[a-z]:[\\/]/i;

function isLocalFileLinkHref(href) {
    return (
        typeof href === 'string' &&
        (/^file:/i.test(href) || windowsDrivePathPattern.test(href))
    );
}

function getNativeHostUrl(href, resolvedHref) {
    return windowsDrivePathPattern.test(href)
        ? href
        : decodeURIComponent(resolvedHref);
}

module.exports = { isLocalFileLinkHref, getNativeHostUrl };
