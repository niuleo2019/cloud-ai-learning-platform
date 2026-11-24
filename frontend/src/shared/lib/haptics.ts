// Light iOS-style haptic feedback. On the phone it uses the native Taptic/vibration engine;
// in the browser it does nothing, so callers never need to check the platform.
import { Capacitor } from '@capacitor/core';
import { Haptics, ImpactStyle, NotificationType } from '@capacitor/haptics';

const native = Capacitor.isNativePlatform();

function run(action: () => Promise<void>) {
  if (!native) return;
  action().catch(() => {
    // haptics are a nicety; never let them break the action that triggered them
  });
}

/** A light tap: selecting, ticking, flipping. */
export function hapticTap() {
  run(() => Haptics.impact({ style: ImpactStyle.Light }));
}

/** A selection change in a segmented control or picker. */
export function hapticSelect() {
  run(() => Haptics.selectionChanged());
}

/** Something went right (correct dictation, task done). */
export function hapticSuccess() {
  run(() => Haptics.notification({ type: NotificationType.Success }));
}

/** Something needs attention (wrong answer, low score). */
export function hapticWarning() {
  run(() => Haptics.notification({ type: NotificationType.Warning }));
}
