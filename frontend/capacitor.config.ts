import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'tech.devjourney.vocab',
  appName: 'Vocab AI',
  webDir: 'dist',
  server: {
    // The app talks to the backend over plain HTTP while testing on the home Wi-Fi.
    // Switch to an HTTPS server address before sharing the app.
    androidScheme: 'http',
    cleartext: true
  }
};

export default config;
