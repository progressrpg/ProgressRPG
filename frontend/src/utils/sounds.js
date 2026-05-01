// utils/sounds.js
// Programmatic sound effects using the Web Audio API.
// No audio assets required – tones are synthesised on demand.

/**
 * Play a short ascending chime to signal that the activity timer has reached
 * its limit. Silently does nothing if the Web Audio API is unavailable.
 */
export function playLimitReachedSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;

    const ctx = new AudioContext();

    const playTone = (frequency, startTime, duration) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "sine";
      osc.frequency.value = frequency;
      gain.gain.setValueAtTime(0.25, startTime);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
      osc.start(startTime);
      osc.stop(startTime + duration);
    };

    const t = ctx.currentTime;
    playTone(523, t, 0.25);        // C5
    playTone(659, t + 0.18, 0.25); // E5
    playTone(784, t + 0.36, 0.4);  // G5

    // Release the audio context after all tones finish (~760ms) plus a small buffer.
    setTimeout(() => ctx.close(), 1200);
  } catch {
    // Silently ignore errors (e.g. browser blocks AudioContext creation).
  }
}
