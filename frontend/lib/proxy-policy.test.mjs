import assert from 'node:assert/strict';
import test from 'node:test';
import {canonicalGoogleConnectUrl, proxyHeaders} from './proxy-policy.mjs';

test('proxy removes browser Origin but preserves Sec-Fetch-Site', () => {
  const headers = proxyHeaders(new Headers({
    origin: 'https://main.example.amplifyapp.com',
    'sec-fetch-site': 'same-origin',
    'content-type': 'application/json',
  }));
  assert.equal(headers.get('origin'), null);
  assert.equal(headers.get('sec-fetch-site'), 'same-origin');
  assert.equal(headers.get('content-type'), 'application/json');
});

test('proxy preserves cross-site signal for backend CSRF rejection', () => {
  const headers = proxyHeaders(new Headers({
    origin: 'https://evil.example',
    'sec-fetch-site': 'cross-site',
  }));
  assert.equal(headers.get('origin'), null);
  assert.equal(headers.get('sec-fetch-site'), 'cross-site');
});

test('Google connect canonicalizes non-local frontend hostnames', () => {
  assert.equal(
    canonicalGoogleConnectUrl({
      path: ['google', 'connect'],
      incomingUrl: 'https://main.example.amplifyapp.com/api/google/connect?next=1',
      canonicalOrigin: 'https://pressure-room.com',
    }),
    'https://pressure-room.com/api/google/connect?next=1',
  );
  assert.equal(
    canonicalGoogleConnectUrl({
      path: ['google', 'connect'],
      incomingUrl: 'https://pressure-room.com/api/google/connect',
      canonicalOrigin: 'https://pressure-room.com',
    }),
    null,
  );
  assert.equal(
    canonicalGoogleConnectUrl({
      path: ['google', 'connect'],
      incomingUrl: 'http://localhost:3000/api/google/connect',
      canonicalOrigin: 'https://pressure-room.com',
    }),
    null,
  );
});
