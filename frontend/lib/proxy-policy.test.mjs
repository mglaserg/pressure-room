import assert from 'node:assert/strict';
import test from 'node:test';
import {proxyHeaders} from './proxy-policy.mjs';

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
