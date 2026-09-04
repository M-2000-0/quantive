// ── Alert Sounds Service ──────────────────────────────────────────────
// Configurable sound notifications using Web Audio API.
// Generates synthetic sounds — no external audio files needed.

export type AlertSoundType = 'critical' | 'high' | 'medium' | 'low' | 'success' | 'info';

interface SoundConfig {
  type: AlertSoundType;
  frequencies: number[];
  duration: number;
  waveform: OscillatorType;
  volume: number;
  pattern: 'single' | 'double' | 'triple' | 'chime';
}

const SOUND_CONFIGS: Record<AlertSoundType, SoundConfig> = {
  critical: {
    type: 'critical',
    frequencies: [880, 660, 880],
    duration: 0.15,
    waveform: 'square',
    volume: 0.3,
    pattern: 'triple',
  },
  high: {
    type: 'high',
    frequencies: [660, 880],
    duration: 0.2,
    waveform: 'sine',
    volume: 0.25,
    pattern: 'double',
  },
  medium: {
    type: 'medium',
    frequencies: [523],
    duration: 0.3,
    waveform: 'sine',
    volume: 0.2,
    pattern: 'single',
  },
  low: {
    type: 'low',
    frequencies: [440],
    duration: 0.4,
    waveform: 'sine',
    volume: 0.15,
    pattern: 'single',
  },
  success: {
    type: 'success',
    frequencies: [523, 659, 784],
    duration: 0.2,
    waveform: 'sine',
    volume: 0.2,
    pattern: 'chime',
  },
  info: {
    type: 'info',
    frequencies: [440, 554],
    duration: 0.15,
    waveform: 'triangle',
    volume: 0.15,
    pattern: 'double',
  },
};

class AlertSoundService {
  private audioContext: AudioContext | null = null;
  private enabled = true;
  private volume = 1.0;
  private muted = false;

  private getContext(): AudioContext {
    if (!this.audioContext) {
      this.audioContext = new AudioContext();
    }
    return this.audioContext;
  }

  /**
   * Play a sound by type.
   */
  play(type: AlertSoundType): void {
    if (!this.enabled || this.muted) return;

    const config = SOUND_CONFIGS[type];
    if (!config) return;

    const ctx = this.getContext();
    const effectiveVolume = config.volume * this.volume;

    switch (config.pattern) {
      case 'single':
        this.playTone(ctx, config.frequencies[0], config.duration, config.waveform, effectiveVolume);
        break;
      case 'double':
        this.playTone(ctx, config.frequencies[0], config.duration, config.waveform, effectiveVolume);
        setTimeout(() => {
          this.playTone(ctx, config.frequencies[1], config.duration, config.waveform, effectiveVolume);
        }, config.duration * 1000);
        break;
      case 'triple':
        config.frequencies.forEach((freq, i) => {
          setTimeout(() => {
            this.playTone(ctx, freq, config.duration, config.waveform, effectiveVolume);
          }, i * config.duration * 1000 * 1.2);
        });
        break;
      case 'chime':
        config.frequencies.forEach((freq, i) => {
          setTimeout(() => {
            this.playTone(ctx, freq, config.duration, config.waveform, effectiveVolume);
          }, i * config.duration * 1000 * 0.8);
        });
        break;
    }
  }

  private playTone(
    ctx: AudioContext,
    frequency: number,
    duration: number,
    waveform: OscillatorType,
    volume: number
  ): void {
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.type = waveform;
    oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);

    // ADSR envelope
    gainNode.gain.setValueAtTime(0, ctx.currentTime);
    gainNode.gain.linearRampToValueAtTime(volume, ctx.currentTime + 0.01);
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration);

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + duration);
  }

  /**
   * Enable or disable sounds.
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Set global volume (0-1).
   */
  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume));
  }

  /**
   * Mute/unmute.
   */
  setMuted(muted: boolean): void {
    this.muted = muted;
  }

  /**
   * Get current settings.
   */
  getSettings(): { enabled: boolean; volume: number; muted: boolean } {
    return { enabled: this.enabled, volume: this.volume, muted: this.muted };
  }

  /**
   * Preview a sound type.
   */
  preview(type: AlertSoundType): void {
    this.play(type);
  }
}

// ── Singleton ─────────────────────────────────────────────────────────

let instance: AlertSoundService | null = null;

export function getAlertSounds(): AlertSoundService {
  if (!instance) {
    instance = new AlertSoundService();
  }
  return instance;
}

/**
 * Map severity to sound type.
 */
export function severityToSoundType(severity: string): AlertSoundType {
  switch (severity) {
    case 'critical': return 'critical';
    case 'high': return 'high';
    case 'medium': return 'medium';
    case 'low': return 'low';
    default: return 'info';
  }
}

/**
 * Map signal type to sound type.
 */
export function signalToSoundType(signalType: string): AlertSoundType {
  if (signalType.includes('credit') || signalType.includes('deterioration')) return 'critical';
  if (signalType.includes('maturity')) return 'high';
  if (signalType.includes('refinance')) return 'success';
  if (signalType.includes('duration')) return 'medium';
  return 'info';
}
