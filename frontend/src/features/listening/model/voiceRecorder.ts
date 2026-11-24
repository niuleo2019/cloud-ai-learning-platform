/** Microphone recording for retell attempts (MediaRecorder; works in Chrome and the Android WebView). */

const MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];

export interface Recording {
  blob: Blob;
  filename: string;
  url: string;
}

export class MicrophoneUnavailableError extends Error {}

export function canRecord() {
  return typeof window !== 'undefined' && typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;
}

function pickMimeType() {
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || '';
}

function extensionFor(mimeType: string) {
  if (mimeType.includes('mp4')) return 'm4a';
  if (mimeType.includes('ogg')) return 'ogg';
  return 'webm';
}

export class VoiceRecorder {
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private stopTimer: number | undefined;

  get recording() {
    return this.recorder?.state === 'recording';
  }

  async start(maxSeconds = 30, onAutoStop?: () => void) {
    if (!canRecord()) throw new MicrophoneUnavailableError('Recording is not supported here');
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch (error) {
      throw new MicrophoneUnavailableError((error as Error)?.message || 'Microphone permission denied');
    }
    const mimeType = pickMimeType();
    this.chunks = [];
    this.recorder = mimeType ? new MediaRecorder(this.stream, { mimeType }) : new MediaRecorder(this.stream);
    this.recorder.ondataavailable = (event) => {
      if (event.data.size > 0) this.chunks.push(event.data);
    };
    this.recorder.start();
    this.stopTimer = window.setTimeout(() => onAutoStop?.(), maxSeconds * 1000);
  }

  stop(): Promise<Recording> {
    window.clearTimeout(this.stopTimer);
    const recorder = this.recorder;
    if (!recorder || recorder.state === 'inactive') {
      this.release();
      return Promise.reject(new Error('Not recording'));
    }
    return new Promise((resolve) => {
      recorder.onstop = () => {
        const type = recorder.mimeType || this.chunks[0]?.type || 'audio/webm';
        const blob = new Blob(this.chunks, { type });
        this.release();
        resolve({ blob, filename: `retell.${extensionFor(type)}`, url: URL.createObjectURL(blob) });
      };
      recorder.stop();
    });
  }

  cancel() {
    window.clearTimeout(this.stopTimer);
    if (this.recorder && this.recorder.state !== 'inactive') {
      this.recorder.onstop = null;
      this.recorder.stop();
    }
    this.release();
  }

  private release() {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.recorder = null;
  }
}
