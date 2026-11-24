<template>
  <main class="page mobile-page home-page">
    <!-- Top-left menu (replaces the old "Me" tab) -->
    <button
      type="button"
      class="home-menu-button"
      :class="{ hidden: active || menuOpen }"
      :aria-label="language === 'zh' ? '菜单' : 'Menu'"
      :aria-expanded="menuOpen"
      @click="menuOpen = !menuOpen"
    >
      <span class="home-menu-bars" :class="{ open: menuOpen }"><i /><i /><i /></span>
    </button>
    <Transition name="home-menu">
      <div v-if="menuOpen" class="home-menu-backdrop" @click="menuOpen = false">
        <!-- Side drawer that slides in from the left edge -->
        <nav class="home-menu" @click.stop>
          <div class="home-menu-head">
            <WordBuddy mini still />
            <button
              type="button"
              class="home-menu-close"
              :aria-label="language === 'zh' ? '关闭' : 'Close'"
              @click="menuOpen = false"
            >
              <van-icon name="cross" />
            </button>
          </div>
          <!-- Imported MDX dictionaries -->
          <section class="home-menu-dicts">
            <h2>{{ language === 'zh' ? '词典' : 'Dictionaries' }}</h2>
            <button
              v-for="dict in dictionaries"
              :key="dict.id"
              type="button"
              class="home-menu-dict"
              :class="{ off: !dict.enabled }"
              @click="openDictionaries"
            >
              <van-icon name="bookmark-o" />
              <span class="home-menu-dict-text">
                <strong>{{ dict.title }}</strong>
                <small>
                  {{ dict.entry_count.toLocaleString() }} {{ language === 'zh' ? '词条' : 'entries' }}
                  <template v-if="!dict.enabled"> · {{ language === 'zh' ? '已停用' : 'off' }}</template>
                </small>
              </span>
            </button>
            <button v-if="dictionariesLoaded && !dictionaries.length" type="button" class="home-menu-dict" @click="openDictionaries">
              <van-icon name="add-o" />
              <span class="home-menu-dict-text">
                <strong>{{ language === 'zh' ? '导入词典' : 'Import a dictionary' }}</strong>
              </span>
            </button>
          </section>
          <div class="home-menu-spacer" />
          <button type="button" class="home-menu-item" @click="openSettings">
            <van-icon name="setting-o" />
            <span>{{ language === 'zh' ? '设置' : 'Settings' }}</span>
          </button>
          <!-- Account at the bottom, under a faint divider -->
          <button type="button" class="home-menu-account" @click="openSettings">
            <span class="home-menu-avatar">{{ userInitial }}</span>
            <span class="home-menu-account-text">
              <strong>{{ user?.username || 'Learner' }}</strong>
              <small>{{ user?.email || '' }}</small>
            </span>
          </button>
        </nav>
      </div>
    </Transition>

    <div class="home-stage" :class="{ active }">
      <!-- Centred title; it folds away when the search rises to the top -->
      <header class="home-brand">
        <div>
          <WordBuddy @search="startSearch" />
          <h1 class="visually-hidden">{{ language === 'zh' ? '查词' : 'Vocabulary' }}</h1>
        </div>
      </header>

      <div class="home-search-row">
        <form class="ios-search" role="search" @submit.prevent="handleSearch">
          <van-icon name="search" class="ios-search-icon" />
          <input
            ref="searchInput"
            v-model="keyword"
            type="search"
            enterkeyhint="search"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            :placeholder="t('home.placeholder')"
            @focus="active = true"
            @click="active = true"
          />
          <button v-if="keyword" type="button" class="ios-search-clear" aria-label="clear" @click="keyword = ''">
            <van-icon name="clear" />
          </button>
          <button v-else type="button" class="home-camera" :aria-label="t('vision.entry')" @click="router.push('/vision')">
            <van-icon name="photograph" />
          </button>
        </form>
        <button v-if="active" type="button" class="home-cancel" @click="cancelSearch">
          {{ language === 'zh' ? '取消' : 'Cancel' }}
        </button>
      </div>
    </div>

    <Transition name="home-results">
      <div v-if="active" class="home-results">
        <!-- While typing: suggestions as an inset grouped list -->
        <section v-if="keyword.trim()" class="home-group">
          <button type="button" class="home-row" @click="handleSearch">
            <van-icon name="search" class="home-row-icon" />
            <span class="home-row-text">{{ t('home.search') }} “{{ keyword.trim() }}”</span>
            <van-icon name="arrow" class="home-row-chevron" />
          </button>
          <button v-for="word in suggestions" :key="word" type="button" class="home-row" @click="selectSuggestion(word)">
            <van-icon name="search" class="home-row-icon" />
            <span class="home-row-text">{{ word }}</span>
            <van-icon name="arrow" class="home-row-chevron" />
          </button>
        </section>

        <template v-else>
          <section v-if="recent.length" class="home-recent">
            <div class="home-recent-head">
              <h2>{{ language === 'zh' ? '最近搜索' : 'Recent' }}</h2>
              <button type="button" @click="confirmClear">{{ language === 'zh' ? '清除' : 'Clear' }}</button>
            </div>
            <div class="home-group">
              <van-swipe-cell v-for="item in recent" :key="item.word">
                <button type="button" class="home-row home-recent-row" @click="selectSuggestion(item.word)">
                  <van-icon name="clock-o" class="home-row-icon" />
                  <span class="home-recent-text">
                    <strong>{{ item.word }}</strong>
                    <small v-if="item.meaning">{{ item.meaning }}</small>
                  </span>
                  <van-icon name="arrow" class="home-row-chevron" />
                </button>
                <template #right>
                  <button type="button" class="home-recent-delete" @click="removeSearch(item.word)">
                    {{ language === 'zh' ? '删除' : 'Delete' }}
                  </button>
                </template>
              </van-swipe-cell>
            </div>
          </section>
          <div v-else class="home-recent-empty">
            <van-icon name="clock-o" />
            <p>{{ language === 'zh' ? '搜过的单词会显示在这里' : 'Words you look up will appear here' }}</p>
          </div>
        </template>
      </div>
    </Transition>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { showConfirmDialog, showFailToast } from 'vant';
import { getWordSuggestions } from '@/features/words/model/wordSuggestions';
import {
  clearSearchHistory,
  hasStoredHistory,
  removeSearch,
  seedSearchHistory,
  useSearchHistory
} from '@/features/words/model/searchHistory';
import { getWordsApi } from '@/features/words/api/wordApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import WordBuddy from '@/shared/ui/WordBuddy.vue';
import { hapticTap } from '@/shared/lib/haptics';
import { getUser } from '@/features/auth/model/authStore';
import { getDictionariesApi, type ImportedDictionary } from '@/features/dictionaries/api/dictionaryLibraryApi';

const router = useRouter();
const { language, t } = useSettingsStore();
const keyword = ref('');
// The search sits mid-screen until it is tapped, then rises and the history appears (iOS-style).
const active = ref(false);
const searchInput = ref<HTMLInputElement>();

function startSearch() {
  active.value = true;
  searchInput.value?.focus();
}

const menuOpen = ref(false);
const dictionaries = ref<ImportedDictionary[]>([]);
const dictionariesLoaded = ref(false);

// Refresh the dictionary list each time the drawer opens.
watch(menuOpen, async (open) => {
  if (!open) return;
  try {
    dictionaries.value = await getDictionariesApi();
  } catch {
    // offline: keep whatever was shown last time
  } finally {
    dictionariesLoaded.value = true;
  }
});

function openDictionaries() {
  menuOpen.value = false;
  hapticTap();
  router.push('/settings/dictionaries');
}
const user = getUser();
const userInitial = computed(() => user?.username?.slice(0, 1).toUpperCase() || 'V');

function openSettings() {
  menuOpen.value = false;
  hapticTap();
  router.push('/me');
}

function cancelSearch() {
  keyword.value = '';
  active.value = false;
  searchInput.value?.blur();
}

const suggestions = computed(() => getWordSuggestions(keyword.value, 4));

const history = useSearchHistory();
const recent = computed(() => history.value.slice(0, 10));

onMounted(async () => {
  if (hasStoredHistory()) return;
  try {
    seedSearchHistory(await getWordsApi());
  } catch {
    // offline or signed out: the list fills as words are looked up
  }
});

function confirmClear() {
  showConfirmDialog({
    message: language.value === 'zh' ? '清除全部搜索记录？' : 'Clear all recent searches?',
    confirmButtonText: language.value === 'zh' ? '清除' : 'Clear',
    confirmButtonColor: 'var(--ios-red)'
  })
    .then(clearSearchHistory)
    .catch(() => undefined);
}

function selectSuggestion(word: string) {
  keyword.value = word;
  router.push({ path: '/lookup', query: { word } });
}

function handleSearch() {
  const word = keyword.value.trim();
  if (!word) {
    showFailToast(t('home.emptySearch'));
    return;
  }

  router.push({ path: '/lookup', query: { word } });
}
</script>

<style scoped>
/* Hamburger in the top-left; the three bars turn into an X while the menu is open */
.home-menu-button {
  position: absolute;
  z-index: 41;
  top: calc(12px + env(safe-area-inset-top));
  left: 12px;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition: opacity 0.25s ease;
}

.home-menu-button:active {
  background: var(--ios-fill-strong);
}

.home-menu-button.hidden {
  opacity: 0;
  pointer-events: none;
}

.home-menu-bars {
  display: grid;
  gap: 5px;
  width: 20px;
}

.home-menu-bars i {
  display: block;
  height: 2px;
  border-radius: 2px;
  background: var(--ios-label);
  transition:
    transform 0.3s var(--ios-ease),
    opacity 0.2s ease;
}

.home-menu-bars.open i:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}

.home-menu-bars.open i:nth-child(2) {
  opacity: 0;
}

.home-menu-bars.open i:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

/* Dimmed backdrop + drawer from the left */
.home-menu-backdrop {
  position: fixed;
  z-index: 40;
  inset: 0;
  background: rgba(0, 0, 0, 0.32);
}

.home-menu {
  display: flex;
  flex-direction: column;
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: min(78%, 300px);
  padding: calc(12px + env(safe-area-inset-top)) 12px 24px;
  background: var(--ios-card);
  box-shadow: 8px 0 32px rgba(0, 0, 0, 0.18);
}

.home-menu-spacer {
  flex: 1;
}

.home-menu-dicts {
  display: grid;
  gap: 2px;
  min-height: 0;
  overflow-y: auto;
}

.home-menu-dicts h2 {
  margin: 0 0 6px 8px;
  color: var(--ios-secondary);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.home-menu-dict {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 52px;
  padding: 6px 8px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--ios-label);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.home-menu-dict:active {
  background: var(--ios-fill-strong);
}

.home-menu-dict .van-icon {
  flex: none;
  color: var(--ios-blue);
  font-size: 20px;
}

.home-menu-dict.off {
  opacity: 0.5;
}

.home-menu-dict-text {
  display: grid;
  min-width: 0;
  gap: 1px;
}

.home-menu-dict-text strong,
.home-menu-dict-text small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-menu-dict-text strong {
  font-size: 15px;
  font-weight: 500;
}

.home-menu-dict-text small {
  color: var(--ios-secondary);
  font-size: 12px;
}

.home-menu-account {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  margin-top: 10px;
  padding: 16px 8px calc(4px + env(safe-area-inset-bottom));
  border: 0;
  border-top: 0.5px solid var(--ios-separator);
  background: transparent;
  color: var(--ios-label);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.home-menu-avatar {
  display: grid;
  flex: none;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--ios-blue);
  color: #fff;
  font-size: 17px;
  font-weight: 700;
}

.home-menu-account-text {
  display: grid;
  min-width: 0;
  gap: 1px;
}

.home-menu-account-text strong,
.home-menu-account-text small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-menu-account-text strong {
  font-size: 16px;
  font-weight: 600;
}

.home-menu-account-text small {
  color: var(--ios-secondary);
  font-size: 13px;
}

/* Buddy on the left, close button on the right, level with where the hamburger sits */
.home-menu-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
  margin-bottom: 14px;
  padding-left: 8px;
}

.home-menu-close {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--ios-fill-strong);
  color: var(--ios-secondary);
  font-size: 18px;
  cursor: pointer;
}

.home-menu-close:active {
  opacity: 0.6;
}

/* Inside the desktop phone frame, stay within the screen (and below its status bar) */
@media (min-width: 768px) {
  .app-device-screen .home-menu-button {
    top: 62px;
  }

  .app-device-screen .home-menu-backdrop {
    position: absolute;
  }

  .app-device-screen .home-menu {
    padding-top: 62px;
  }
}

.home-menu-item {
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 48px;
  padding: 0 16px;
  border: 0;
  background: transparent;
  color: var(--ios-label);
  font: inherit;
  font-size: 17px;
  text-align: left;
  cursor: pointer;
}

.home-menu-item:active {
  background: var(--ios-fill-strong);
}

.home-menu-item .van-icon {
  color: var(--ios-secondary);
  font-size: 22px;
}

.home-menu-enter-active,
.home-menu-leave-active {
  transition: background-color 0.35s var(--ios-ease);
}

.home-menu-enter-active .home-menu,
.home-menu-leave-active .home-menu {
  transition: transform 0.35s var(--ios-ease);
}

.home-menu-enter-from,
.home-menu-leave-to {
  background-color: rgba(0, 0, 0, 0);
}

.home-menu-enter-from .home-menu,
.home-menu-leave-to .home-menu {
  transform: translateX(-100%);
}

.home-page {
  display: grid;
  align-content: start;
  position: relative;
  gap: 16px;
}

.home-stage {
  display: grid;
  transform: translateY(14vh);
  transition: transform 0.55s var(--ios-ease);
}

.home-stage.active {
  transform: none;
}

.home-brand {
  display: grid;
  grid-template-rows: 1fr;
  opacity: 1;
  text-align: center;
  transition:
    grid-template-rows 0.5s var(--ios-ease),
    opacity 0.25s ease;
}

.home-brand > div {
  min-height: 0;
  overflow: hidden;
  padding: 24px 0;
}

.home-stage.active .home-brand {
  grid-template-rows: 0fr;
  opacity: 0;
}

.home-results {
  display: grid;
  gap: 16px;
}

.home-results-enter-active {
  transition:
    opacity 0.35s var(--ios-ease) 0.15s,
    transform 0.45s var(--ios-ease) 0.1s;
}

.home-results-leave-active {
  transition: opacity 0.15s ease;
}

.home-results-enter-from {
  opacity: 0;
  transform: translateY(16px);
}

.home-results-leave-to {
  opacity: 0;
}

.home-cancel {
  flex: none;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--ios-blue);
  font: inherit;
  font-size: 17px;
  cursor: pointer;
  animation: home-cancel-in 0.3s var(--ios-ease);
}

@keyframes home-cancel-in {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* iOS search field: grey fill, magnifier, no border */
.ios-search {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 8px 0 10px;
  border-radius: 12px;
  background: var(--ios-fill-strong);
}

.ios-search-icon {
  color: var(--ios-secondary);
  font-size: 18px;
}

.ios-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--ios-label);
  font: inherit;
  font-size: 17px;
}

.ios-search input::placeholder {
  color: var(--ios-secondary);
}

.ios-search input::-webkit-search-cancel-button {
  display: none;
}

.ios-search-clear {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ios-secondary);
  font-size: 18px;
  cursor: pointer;
}

.home-search-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.home-search-row .ios-search {
  flex: 1;
  min-width: 0;
}

/* Quiet camera inside the field, same grey as the magnifier */
.home-camera {
  display: grid;
  flex: none;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ios-secondary);
  font-size: 19px;
  cursor: pointer;
}

.home-camera:active {
  opacity: 0.5;
}

.home-recent-empty {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 72px 24px 0;
  color: var(--ios-tertiary);
  text-align: center;
}

.home-recent-empty .van-icon {
  font-size: 40px;
}

.home-recent-empty p {
  margin: 0;
  color: var(--ios-secondary);
  font-size: 15px;
}

/* Inset grouped list */
.home-group {
  overflow: hidden;
  border-radius: var(--ios-radius);
  background: var(--ios-card);
}

.home-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  border: 0;
  background: transparent;
  color: var(--ios-label);
  font: inherit;
  font-size: 17px;
  text-align: left;
  cursor: pointer;
}

.home-row:active {
  background: var(--ios-fill-strong);
}

.home-row + .home-row::before {
  position: absolute;
  top: 0;
  right: 0;
  left: 54px;
  border-top: 0.5px solid var(--ios-separator);
  content: '';
}

.home-row-icon {
  flex: none;
  width: 28px;
  color: var(--ios-secondary);
  font-size: 18px;
  text-align: center;
}

.home-row-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-recent-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 4px 8px;
}

.home-recent-head h2 {
  margin: 0;
  color: var(--ios-label);
  font-size: 20px;
  font-weight: 700;
}

.home-recent-head button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ios-blue);
  font: inherit;
  font-size: 15px;
  cursor: pointer;
}

.home-recent-row {
  min-height: 56px;
}

.home-group :deep(.van-swipe-cell + .van-swipe-cell) .home-row::before {
  position: absolute;
  top: 0;
  right: 0;
  left: 54px;
  border-top: 0.5px solid var(--ios-separator);
  content: '';
}

.home-recent-text {
  display: grid;
  flex: 1;
  min-width: 0;
  gap: 2px;
}

.home-recent-text strong,
.home-recent-text small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-recent-text strong {
  font-size: 17px;
  font-weight: 600;
}

.home-recent-text small {
  color: var(--ios-secondary);
  font-size: 14px;
}

.home-recent-delete {
  height: 100%;
  padding: 0 20px;
  border: 0;
  background: var(--ios-red);
  color: #fff;
  font: inherit;
  font-size: 15px;
}

.home-row-chevron {
  color: var(--ios-tertiary);
  font-size: 14px;
}
</style>
