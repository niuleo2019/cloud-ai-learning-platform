// Review reminders that follow the user's spaced-repetition progress (phone app only).
//
// One local notification is kept scheduled at a time:
//  - words already due   -> a nudge at 20:00 (today, or tomorrow if that has passed)
//  - nothing due yet     -> when the next word becomes due, moved into 9:00–21:00 so it never rings at night
// The text says how many words will be due by then; tapping it opens the review page.
// It is recalculated whenever the app opens or comes back to the foreground, and after each review.
import { Capacitor } from '@capacitor/core';
import { LocalNotifications } from '@capacitor/local-notifications';
import type { Router } from 'vue-router';
import { getWordsApi } from '@/features/words/api/wordApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import type { Word } from '@/shared/types';

const NOTIFICATION_ID = 4201;
const STORAGE_KEY = 'vocab-review-reminders';
const DAY_START = 9;
const DAY_END = 21;
const EVENING = 20;

const native = Capacitor.isNativePlatform();

export function remindersEnabled() {
  try {
    return localStorage.getItem(STORAGE_KEY) !== 'off';
  } catch {
    return true;
  }
}

export async function setRemindersEnabled(on: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off');
  } catch {
    // storage unavailable: the switch just won't persist
  }
  await syncReviewReminders();
}

/** The backend stores review times in UTC without a zone marker. */
function parseUtc(value?: string) {
  if (!value) return NaN;
  const iso = value.includes('T') ? value : value.replace(' ', 'T');
  return Date.parse(/(z|[+-]\d\d:?\d\d)$/i.test(iso) ? iso : `${iso}Z`);
}

/** Keep reminders inside waking hours. */
function intoDaytime(time: Date) {
  const at = new Date(time);
  if (at.getHours() < DAY_START) {
    at.setHours(DAY_START, 0, 0, 0);
  } else if (at.getHours() >= DAY_END) {
    at.setDate(at.getDate() + 1);
    at.setHours(DAY_START, 0, 0, 0);
  }
  return at;
}

/** When to remind and how many words will be due by then (null: nothing to review). */
export function planReminder(words: Pick<Word, 'next_review_at'>[], now = new Date()) {
  const dues = words
    .map((word) => parseUtc(word.next_review_at))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);
  if (!dues.length) return null;

  let at: Date;
  if (dues[0] <= now.getTime()) {
    at = new Date(now);
    at.setHours(EVENING, 0, 0, 0);
    if (at <= now) at.setDate(at.getDate() + 1);
  } else {
    at = intoDaytime(new Date(dues[0]));
  }
  if (at.getTime() - now.getTime() < 60_000) at = new Date(now.getTime() + 60_000);

  const count = dues.filter((time) => time <= at.getTime()).length;
  return { at, count };
}

async function ensurePermission() {
  let { display } = await LocalNotifications.checkPermissions();
  if (display === 'prompt' || display === 'prompt-with-rationale') {
    ({ display } = await LocalNotifications.requestPermissions());
  }
  return display === 'granted';
}

let syncing: Promise<void> | null = null;

/** Recalculate and (re)schedule the reminder. Safe to call often. */
export function syncReviewReminders() {
  if (!native) return Promise.resolve();
  syncing ??= (async () => {
    try {
      await LocalNotifications.cancel({ notifications: [{ id: NOTIFICATION_ID }] });
      if (!remindersEnabled()) return;

      const plan = planReminder(await getWordsApi());
      if (!plan || !plan.count || !(await ensurePermission())) return;

      const zh = useSettingsStore().language.value === 'zh';
      await LocalNotifications.schedule({
        notifications: [
          {
            id: NOTIFICATION_ID,
            title: zh ? '该复习单词啦' : 'Time to review',
            body: zh
              ? `有 ${plan.count} 个单词等你复习，点这里开始`
              : `${plan.count} word${plan.count === 1 ? ' is' : 's are'} ready for review. Tap to start.`,
            schedule: { at: plan.at, allowWhileIdle: true },
            extra: { route: '/reviews' }
          }
        ]
      });
    } catch {
      // signed out, offline or notifications blocked: try again next time
    } finally {
      syncing = null;
    }
  })();
  return syncing;
}

/** Called once at start-up: tapping a reminder opens the review page; re-plan whenever the app returns. */
export function initReviewReminders(router: Router) {
  if (!native) return;
  LocalNotifications.addListener('localNotificationActionPerformed', (action) => {
    const route = (action.notification.extra as { route?: string } | undefined)?.route || '/reviews';
    router.push(route);
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') syncReviewReminders();
  });
  syncReviewReminders();
}
