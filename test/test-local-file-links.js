'use strict';

const assert = require('node:assert/strict');
const { test } = require('node:test');
const {
    getNativeHostUrl,
    isLocalFileLinkHref
} = require('../src/extension/helpers/localFileLinks');

test('recognizes file URLs and direct Windows drive paths', () => {
    assert.equal(isLocalFileLinkHref('file:///C:/Windows'), true);
    assert.equal(isLocalFileLinkHref('G:\\Donnees\\'), true);
    assert.equal(isLocalFileLinkHref('c:/windows/'), true);
});

test('does not treat ordinary or drive-relative URLs as local links', () => {
    assert.equal(isLocalFileLinkHref('https://example.com'), false);
    assert.equal(isLocalFileLinkHref('C:folder\\file.txt'), false);
    assert.equal(isLocalFileLinkHref('mailto:user@example.com'), false);
});

test('passes direct Windows paths unchanged to the native host', () => {
    const path = 'G:\\Donnees\\Dossier été\\';
    assert.equal(
        getNativeHostUrl(path, 'g:\\Donnees\\Dossier%20%C3%A9t%C3%A9\\'),
        path
    );
});

test('decodes file URL paths for the native host', () => {
    assert.equal(
        getNativeHostUrl(
            'file:///C:/Documents/Dossier%20%C3%A9t%C3%A9.docx',
            'file:///C:/Documents/Dossier%20%C3%A9t%C3%A9.docx'
        ),
        'file:///C:/Documents/Dossier été.docx'
    );
});
