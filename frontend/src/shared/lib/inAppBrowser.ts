import { Capacitor } from '@capacitor/core';
import { Browser } from '@capacitor/browser';

/**
 * Open an external page without leaving the app.
 * Android app: an in-app browser sheet (Chrome Custom Tab) over the app; closing it returns here.
 * Web: a new browser tab.
 */
export async function openInAppBrowser(url: string) {
  if (!/^https?:\/\//i.test(url)) return;
  if (Capacitor.isNativePlatform()) {
    await Browser.open({ url, toolbarColor: '#0f172a', presentationStyle: 'popover' });
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}
