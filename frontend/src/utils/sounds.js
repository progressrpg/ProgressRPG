// utils/sounds.js
// Programmatic sound effects using the Web Audio API.
// No audio assets required – tones are synthesised on demand.

/**
 * Play a short note pattern. Silently does nothing if the Web Audio API is unavailable.
 */
function playChime(noteSequence) {
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
    noteSequence.forEach(({ frequency, offset, duration }) => {
      playTone(frequency, t + offset, duration);
    });

    const finalNoteEnd =
      noteSequence.reduce(
        (latestEnd, note) => Math.max(latestEnd, note.offset + note.duration),
        0,
      ) * 1000;
    setTimeout(() => ctx.close(), finalNoteEnd + 400);
  } catch {
    // Silently ignore errors (e.g. browser blocks AudioContext creation).
  }
}

export function playActivityStartedSound() {
  playChime([
    { frequency: 523, offset: 0, duration: 0.22 }, // C5
    { frequency: 784, offset: 0.16, duration: 0.22 }, // G5
    { frequency: 659, offset: 0.32, duration: 0.34 }, // E5
  ]);
}

/**
 * Play a short ascending chime to signal that the activity timer has reached
 * its limit.
 */
export function playLimitReachedSound() {
  playChime([
    { frequency: 523, offset: 0, duration: 0.18 }, // C5
    { frequency: 659, offset: 0.12, duration: 0.18 }, // E5
    { frequency: 784, offset: 0.24, duration: 0.18 }, // G5
    { frequency: 1047, offset: 0.36, duration: 0.28 }, // C6
  ]);
}
