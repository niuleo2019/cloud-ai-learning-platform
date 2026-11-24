<template>
  <main class="page mobile-page agent-page">
    <van-nav-bar
      :left-text="t('common.back')"
      left-arrow
      :right-text="messages.length > 0 ? t('agent.clear') : ''"
      @click-left="router.back()"
      @click-right="clearChat"
    >
      <template #title>
        <span class="agent-title" role="heading" aria-level="1" :aria-label="t('agent.title')">
          <WordBuddy mini still />
        </span>
      </template>
    </van-nav-bar>

    <section ref="listRef" class="agent-messages">
      <div v-if="messages.length === 0" class="agent-welcome">
        <van-icon name="chat-o" class="agent-welcome-icon" />
        <p>{{ t('agent.welcome') }}</p>
        <button v-for="key in examples" :key="key" type="button" class="agent-example" @click="send(t(key))">
          {{ t(key) }}
        </button>
      </div>

      <div v-for="(item, index) in messages" :key="index" class="agent-row" :class="item.role">
        <div v-if="item.toolCalls?.length" class="agent-tools">
          <van-tag
            v-for="(call, callIndex) in item.toolCalls"
            :key="callIndex"
            plain
            round
            :type="call.ok ? 'primary' : 'danger'"
          >
            {{ toolLabel(call) }}
          </van-tag>
        </div>
        <div class="agent-line">
          <div class="agent-bubble">{{ item.content }}</div>
          <WordBuddy v-if="item.role === 'user'" mini class="agent-avatar" />
        </div>
      </div>

      <div v-if="loading" class="agent-row assistant">
        <div class="agent-line">
          <div class="agent-bubble agent-thinking">
            <van-loading size="16px" />
            {{ t('agent.thinking') }}
          </div>
        </div>
      </div>
    </section>

    <form class="agent-input-bar" @submit.prevent="send(draft)">
      <van-field
        v-model="draft"
        class="agent-input"
        :placeholder="t('agent.placeholder')"
        :disabled="loading"
        maxlength="2000"
        autocomplete="off"
      />
      <van-button native-type="submit" type="primary" round size="small" :disabled="loading || !draft.trim()">
        {{ t('agent.send') }}
      </van-button>
    </form>
  </main>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { chatWithAgentApi, type AgentToolCall, type ChatTurn } from '@/features/agent/api/agentApi';
import { useSettingsStore } from '@/shared/model/settingsStore';
import WordBuddy from '@/shared/ui/WordBuddy.vue';

interface ChatMessage extends ChatTurn {
  toolCalls?: AgentToolCall[];
}

const STORAGE_KEY = 'vocab.agent.chat';
const examples = ['agent.example1', 'agent.example2', 'agent.example3'];

const router = useRouter();
const { t } = useSettingsStore();
const messages = ref<ChatMessage[]>(loadChat());
const draft = ref('');
const loading = ref(false);
const listRef = ref<HTMLElement | null>(null);

function loadChat(): ChatMessage[] {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    return saved ? (JSON.parse(saved) as ChatMessage[]) : [];
  } catch {
    return [];
  }
}

watch(
  messages,
  (value) => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch {
      // Storage unavailable (private mode): the chat still works for this page view.
    }
  },
  { deep: true }
);

function toolLabel(call: AgentToolCall) {
  const word = typeof call.input?.word === 'string' ? ` ${call.input.word}` : '';
  return `${t(`agent.tool.${call.name}`)}${word}${call.ok ? '' : ' ✕'}`;
}

async function scrollToBottom() {
  await nextTick();
  listRef.value?.scrollTo({ top: listRef.value.scrollHeight, behavior: 'smooth' });
}

async function send(text: string) {
  const message = text.trim();
  if (!message || loading.value) return;

  // Earlier turns go to the backend as plain text; tool details stay on the client.
  const history: ChatTurn[] = messages.value.map(({ role, content }) => ({ role, content }));
  messages.value.push({ role: 'user', content: message });
  draft.value = '';
  loading.value = true;
  scrollToBottom();

  try {
    const result = await chatWithAgentApi(message, history);
    messages.value.push({ role: 'assistant', content: result.reply, toolCalls: result.tool_calls });
  } catch (error) {
    // Show the backend's reason (e.g. "AI assistant is not configured") instead of a generic message.
    const reason = (error as { response?: { data?: { message?: string } } }).response?.data?.message;
    messages.value.push({ role: 'assistant', content: reason ? `${t('agent.failed')}\n(${reason})` : t('agent.failed') });
  } finally {
    loading.value = false;
    scrollToBottom();
  }
}

function clearChat() {
  if (loading.value) return;
  messages.value = [];
}

scrollToBottom();
</script>

<style scoped>
.agent-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* Leave room for the fixed bottom tab bar (82px) so the input bar stays above it. */
  padding-bottom: 82px;
}

.agent-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 2px 90px;
}

.agent-welcome {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  color: #334155;
  line-height: 1.5;
}

.agent-welcome p {
  margin: 0;
}

.agent-welcome-icon {
  font-size: 28px;
  color: #2563eb;
}

.agent-example {
  padding: 10px 12px;
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 12px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 14px;
  text-align: left;
}

.agent-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 86%;
}

.agent-row.user {
  align-self: flex-end;
  align-items: flex-end;
}

.agent-row.assistant {
  align-self: flex-start;
}

/* Like a chat app avatar: the character sits at the outer edge, level with the top of the blue bubble */
.agent-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.user .agent-line {
  justify-content: flex-end;
}

.agent-avatar {
  flex: none;
  margin-top: 4px;
}

.agent-title {
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.agent-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.agent-bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.user .agent-bubble {
  background: #2563eb;
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.assistant .agent-bubble {
  background: #ffffff;
  color: #0f172a;
  border-bottom-left-radius: 4px;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}

.agent-thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
}

.agent-input-bar {
  position: sticky;
  bottom: 82px; /* above the fixed tab bar */
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0 14px;
  background: inherit;
}

.agent-input {
  flex: 1;
  border-radius: 999px;
  padding: 8px 14px;
  background: #ffffff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}
</style>
