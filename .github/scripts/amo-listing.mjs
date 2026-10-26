import { createHmac, randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';

const apiBase = 'https://addons.mozilla.org/api/v5';
const addonSlug = 'local-filesystem-links-reboot';
const expectedUsername = process.env.EXPECTED_AMO_USERNAME?.toLowerCase();
const issuer = process.env.AMO_JWT_ISSUER;
const secret = process.env.AMO_JWT_SECRET;

if (!expectedUsername || !issuer || !secret) {
    throw new Error(
        'Expected AMO username and API credentials must be configured.'
    );
}

const encode = value =>
    Buffer.from(JSON.stringify(value)).toString('base64url');
const issuedAt = Math.floor(Date.now() / 1000);
const signingInput = [
    encode({ alg: 'HS256', typ: 'JWT' }),
    encode({
        iss: issuer,
        jti: randomUUID(),
        iat: issuedAt,
        exp: issuedAt + 60
    })
].join('.');
const signature = createHmac('sha256', secret)
    .update(signingInput)
    .digest('base64url');
const token = `${signingInput}.${signature}`;

async function request(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, {
        ...options,
        headers: {
            Authorization: `JWT ${token}`,
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    const body = await response.json();
    if (!response.ok) {
        throw new Error(
            `AMO API request failed (${response.status}): ${JSON.stringify(
                body
            )}`
        );
    }
    return body;
}

const profile = await request('/accounts/profile/');
const profileName = (
    profile.name ||
    profile.display_name ||
    profile.username ||
    ''
).toLowerCase();
if (profileName !== expectedUsername) {
    throw new Error(
        `AMO credentials belong to "${profileName ||
            'an unknown account'}", not the expected publisher "${expectedUsername}".`
    );
}

const addon = await request(`/addons/addon/${addonSlug}/`);
const expectedAuthor = addon.authors.find(
    author => author.name?.toLowerCase() === expectedUsername
);
if (!expectedAuthor || expectedAuthor.id !== profile.id) {
    throw new Error(
        `Refusing to edit AMO listing "${addonSlug}": its authors do not match the authenticated publisher "${expectedUsername}".`
    );
}

console.log(`Verified AMO publisher and listing author: ${expectedUsername}`);
if (process.argv.includes('--verify-only')) {
    process.exit(0);
}

const metadataPath = process.env.AMO_METADATA_PATH || 'amo-metadata.json';
const metadata = JSON.parse(await readFile(metadataPath, 'utf8'));
const patch = {
    name: metadata.name,
    summary: metadata.summary,
    description: metadata.description,
    homepage: metadata.homepage,
    contributions_url: metadata.contributions_url,
    is_experimental: metadata.is_experimental
};
const updated = await request(`/addons/addon/${addonSlug}/`, {
    method: 'PATCH',
    body: JSON.stringify(patch)
});

console.log(
    `Updated AMO listing "${updated.name?.['en-US'] ||
        addonSlug}" with the current maintainer details and contribution link.`
);
