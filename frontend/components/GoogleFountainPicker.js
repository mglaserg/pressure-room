'use client';

import {useState} from 'react';
import {api} from '@/lib/api';

let pickerLoader = null;

function loadPickerApi() {
  if (typeof window === 'undefined') return Promise.reject(new Error('Google Picker requires a browser.'));
  if (window.google?.picker) return Promise.resolve();

  if (!pickerLoader) {
    pickerLoader = new Promise((resolve, reject) => {
      const finish = () => {
        if (!window.gapi) {
          reject(new Error('Google Picker did not load.'));
          return;
        }
        window.gapi.load('picker', {
          callback: resolve,
          onerror: () => reject(new Error('Google Picker could not be initialized.')),
        });
      };

      const existing = document.querySelector('script[data-pressure-room-google-api]');
      if (existing) {
        if (window.gapi) finish();
        else existing.addEventListener('load', finish, {once: true});
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://apis.google.com/js/api.js';
      script.async = true;
      script.defer = true;
      script.dataset.pressureRoomGoogleApi = 'true';
      script.onload = finish;
      script.onerror = () => reject(new Error('Google Picker script could not be loaded.'));
      document.head.appendChild(script);
    });
  }

  return pickerLoader;
}

export default function GoogleFountainPicker({
  onOpened,
  className = 'button secondary',
  label = 'Open Fountain from Drive',
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function openPicker() {
    setBusy(true);
    setMessage('');

    try {
      const config = await api('/google/picker');
      await loadPickerApi();

      if (!window.google?.picker) throw new Error('Google Picker is unavailable.');

      const view = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
        .setIncludeFolders(false)
        .setMode(window.google.picker.DocsViewMode.LIST)
        .setMimeTypes('text/plain');

      const picker = new window.google.picker.PickerBuilder()
        .addView(view)
        .enableFeature(window.google.picker.Feature.NAV_HIDDEN)
        .setOAuthToken(config.access_token)
        .setDeveloperKey(config.api_key)
        .setAppId(config.app_id)
        .setCallback(async data => {
          const action = data[window.google.picker.Response.ACTION];

          if (action === window.google.picker.Action.CANCEL) {
            setBusy(false);
            return;
          }

          if (action !== window.google.picker.Action.PICKED) return;

          try {
            const docs = data[window.google.picker.Response.DOCUMENTS] || [];
            const doc = docs[0];
            const fileId = doc?.[window.google.picker.Document.ID];
            const fileName = doc?.[window.google.picker.Document.NAME] || '';

            if (!fileId) throw new Error('Google Picker did not return a file.');
            if (!fileName.toLowerCase().endsWith('.fountain')) throw new Error('Choose a .fountain file.');

            setMessage(`Opening ${fileName}…`);
            const result = await api('/google/fountain/open', {
              method: 'POST',
              body: JSON.stringify({file_id: fileId}),
            });
            setMessage(result.already_linked ? 'Linked Fountain opened.' : `Linked ${result.scene_count || 0} scenes.`);
            await onOpened?.(result);
          } catch (error) {
            setMessage(error.message || 'Could not open that Fountain file.');
          } finally {
            setBusy(false);
          }
        })
        .build();

      picker.setVisible(true);
    } catch (error) {
      setMessage(error.message || 'Could not open Google Picker.');
      setBusy(false);
    }
  }

  return <span className="picker-action"><button className={className} disabled={busy} onClick={openPicker}>{busy ? 'Opening Drive…' : label}</button>{message&&<span className="form-message">{message}</span>}</span>;
}
