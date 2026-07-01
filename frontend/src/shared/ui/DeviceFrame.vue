<template>
  <div class="device-stage">
    <div class="device-shell" :aria-label="device">
      <div class="device-side-button left top"></div>
      <div class="device-side-button left bottom"></div>
      <div class="device-side-button right"></div>

      <div class="device-screen app-device-screen">
        <div class="device-status-bar" aria-hidden="true">
          <span class="status-time">{{ currentTime }}</span>
          <div class="status-icons">
            <span class="signal-icon">
              <i></i>
              <i></i>
              <i></i>
              <i></i>
            </span>
            <span class="wifi-icon"></span>
            <span class="bluetooth-icon">B</span>
            <span class="battery-icon">
              <span></span>
            </span>
          </div>
        </div>
        <div class="dynamic-island"></div>
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

defineProps<{
  device: string;
}>();

const now = ref(new Date());
let timerId: number | undefined;

const currentTime = computed(() =>
  new Intl.DateTimeFormat('en-AU', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: false
  }).format(now.value)
);

onMounted(() => {
  timerId = window.setInterval(() => {
    now.value = new Date();
  }, 30000);
});

onBeforeUnmount(() => {
  if (timerId) {
    window.clearInterval(timerId);
  }
});
</script>

<style scoped>
.device-stage {
  min-height: 100vh;
  background:
    radial-gradient(circle at 18% 12%, rgba(37, 99, 235, 0.14), transparent 30%),
    radial-gradient(circle at 82% 8%, rgba(20, 184, 166, 0.16), transparent 28%),
    #eaf0f8;
}

.device-shell {
  position: relative;
  width: min(100vw, 430px);
  min-height: 100vh;
  margin: 0 auto;
  background: #0b1220;
}

.device-screen {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: #f4f7fb;
}

.dynamic-island,
.device-status-bar,
.device-side-button {
  display: none;
}

@media (min-width: 768px) {
  .device-stage {
    display: grid;
    place-items: center;
    padding: 32px;
  }

  .device-shell {
    width: 393px;
    height: 852px;
    min-height: 0;
    padding: 13px;
    border-radius: 58px;
    background:
      linear-gradient(135deg, #111827 0%, #020617 54%, #1f2937 100%);
    box-shadow:
      0 28px 80px rgba(15, 23, 42, 0.28),
      inset 0 0 0 2px rgba(255, 255, 255, 0.08),
      inset 0 0 0 7px #020617;
  }

  .device-screen {
    height: 100%;
    min-height: 0;
    overflow: hidden;
    border-radius: 45px;
  }

  .dynamic-island {
    display: block;
    position: absolute;
    top: 18px;
    left: 50%;
    z-index: 40;
    width: 118px;
    height: 34px;
    transform: translateX(-50%);
    border-radius: 999px;
    background: #020617;
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.08);
  }

  .device-status-bar {
    display: flex;
    position: absolute;
    top: 12px;
    left: 28px;
    right: 28px;
    z-index: 35;
    align-items: center;
    justify-content: space-between;
    height: 26px;
    color: #111827;
    font-size: 13px;
    font-weight: 700;
    pointer-events: none;
  }

  .status-time {
    min-width: 54px;
    text-align: center;
  }

  .status-icons {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .signal-icon {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
    height: 12px;
  }

  .signal-icon i {
    display: block;
    width: 3px;
    border-radius: 999px;
    background: #111827;
  }

  .signal-icon i:nth-child(1) {
    height: 4px;
  }

  .signal-icon i:nth-child(2) {
    height: 6px;
  }

  .signal-icon i:nth-child(3) {
    height: 9px;
  }

  .signal-icon i:nth-child(4) {
    height: 12px;
  }

  .wifi-icon {
    position: relative;
    width: 15px;
    height: 11px;
    overflow: hidden;
  }

  .wifi-icon::before,
  .wifi-icon::after {
    content: "";
    position: absolute;
    left: 50%;
    border: 2px solid #111827;
    border-bottom: 0;
    border-radius: 999px 999px 0 0;
    transform: translateX(-50%);
  }

  .wifi-icon::before {
    bottom: 1px;
    width: 15px;
    height: 9px;
  }

  .wifi-icon::after {
    bottom: 1px;
    width: 8px;
    height: 5px;
  }

  .bluetooth-icon {
    font-size: 11px;
    line-height: 1;
  }

  .battery-icon {
    position: relative;
    display: inline-flex;
    align-items: center;
    width: 24px;
    height: 12px;
    padding: 2px;
    border: 1.5px solid #111827;
    border-radius: 4px;
  }

  .battery-icon::after {
    content: "";
    position: absolute;
    right: -3px;
    width: 2px;
    height: 5px;
    border-radius: 0 2px 2px 0;
    background: #111827;
  }

  .battery-icon span {
    display: block;
    width: 72%;
    height: 100%;
    border-radius: 2px;
    background: #111827;
  }

  .device-side-button {
    display: block;
    position: absolute;
    width: 4px;
    border-radius: 999px;
    background: #111827;
  }

  .device-side-button.left {
    left: -3px;
    height: 54px;
  }

  .device-side-button.left.top {
    top: 142px;
  }

  .device-side-button.left.bottom {
    top: 214px;
  }

  .device-side-button.right {
    right: -3px;
    top: 178px;
    height: 88px;
  }
}
</style>
