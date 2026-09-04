// ── Sound Design ──────────────────────────────────────────────────────
// Subtle audio cues that make the app feel alive.
// Bloomberg, not video game. Most users won't consciously notice.
// They'll just feel the app is more polished.

const AudioCtx = typeof window !== 'undefined'
  ? (window.AudioContext || (window as any).webkitAudioContext)
  : null;

let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (!AudioCtx) return null;
  if (!ctx) ctx = new AudioCtx();
  return ctx;
}

// ── Sound Definitions ────────────────────────────────────────────────

function playTone(frequency: number, duration: number, volume = 0.08, type: OscillatorType = 'sine') {
  const c = getCtx();
  if (!c) return;

  const osc = c.createOscillator();
  const gain = c.createGain();

  osc.type = type;
  osc.frequency.setValueAtTime(frequency, c.currentTime);

  gain.gain.setValueAtTime(volume, c.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);

  osc.connect(gain);
  gain.connect(c.destination);

  osc.start(c.currentTime);
  osc.stop(c.currentTime + duration);
}

function playChord(frequencies: number[], duration: number, volume = 0.04) {
  frequencies.forEach(f => playTone(f, duration, volume));
}

// ── Public API ───────────────────────────────────────────────────────

/** Approval completed — two-note confirmation, warm */
export function playApproval() {
  playTone(523, 0.12, 0.06); // C5
  setTimeout(() => playTone(659, 0.15, 0.05), 80); // E5
}

/** Simulation finished — three-note ascending, satisfying */
export function playSimulationComplete() {
  playTone(440, 0.1, 0.05); // A4
  setTimeout(() => playTone(554, 0.1, 0.05), 100); // C#5
  setTimeout(() => playTone(659, 0.18, 0.04), 200); // E5
}

/** Risk alert — single low tone, attention-grabbing */
export function playRiskAlert() {
  playTone(220, 0.2, 0.08, 'triangle'); // A3
  setTimeout(() => playTone(277, 0.25, 0.06, 'triangle'), 150); // C#4
}

/** Comment received — soft ping */
export function playCommentReceived() {
  playTone(880, 0.08, 0.04); // A5
}

/** Error — two-note descending */
export function playError() {
  playTone(330, 0.15, 0.06, 'triangle'); // E4
  setTimeout(() => playTone(262, 0.2, 0.05, 'triangle'), 100); // C4
}

/** Navigation — subtle click */
export function playNavigate() {
  playTone(1047, 0.04, 0.03); // C6
}

/** Data refresh — soft shimmer */
export function playDataRefresh() {
  playTone(784, 0.06, 0.03); // G5
  setTimeout(() => playTone(988, 0.06, 0.02), 50); // B5
}

// ── Sound Map ────────────────────────────────────────────────────────

export const sounds = {
  approval: playApproval,
  simulation_complete: playSimulationComplete,
  risk_alert: playRiskAlert,
  comment_received: playCommentReceived,
  error: playError,
  navigate: playNavigate,
  data_refresh: playDataRefresh,
} as const;

export type SoundName = keyof typeof sounds;

let soundEnabled = true;

export function setSoundEnabled(enabled: boolean) {
  soundEnabled = enabled;
}

export function isSoundEnabled() {
  return soundEnabled;
}

export function play(name: SoundName) {
  if (soundEnabled) sounds[name]();
}
