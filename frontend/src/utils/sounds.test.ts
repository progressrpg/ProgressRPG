import { afterEach, describe, expect, it, vi } from "vitest";

class FakeAudioParam {
  value = 0;
  setValueAtTime = vi.fn();
  exponentialRampToValueAtTime = vi.fn();
}

class FakeOscillatorNode {
  type = "";
  frequency = new FakeAudioParam();
  connect = vi.fn();
  start = vi.fn();
  stop = vi.fn();
}

class FakeGainNode {
  gain = new FakeAudioParam();
  connect = vi.fn();
}

function createFakeAudioContext(state: "running" | "suspended" = "running") {
  const resume = vi.fn().mockResolvedValue(undefined);
  return {
    state,
    currentTime: 0,
    createOscillator: vi.fn(() => new FakeOscillatorNode()),
    createGain: vi.fn(() => new FakeGainNode()),
    destination: {},
    resume,
  };
}

// sounds.ts keeps a module-level AudioContext singleton, so each test needs a
// fresh module instance to control which fake context getContext() sees.
async function loadSounds() {
  vi.resetModules();
  return import("./sounds");
}

describe("sounds", () => {
  const originalAudioContext = window.AudioContext;

  afterEach(() => {
    window.AudioContext = originalAudioContext;
    vi.useRealTimers();
  });

  it("does nothing when AudioContext is unsupported", async () => {
    // @ts-expect-error simulating an environment without AudioContext
    delete window.AudioContext;
    const { playActivityStartedSound, primeAudio } = await loadSounds();

    expect(() => playActivityStartedSound()).not.toThrow();
    expect(() => primeAudio()).not.toThrow();
  });

  it("schedules oscillator notes for the activity-started chime", async () => {
    const fakeCtx = createFakeAudioContext("running");
    window.AudioContext = vi.fn(function () { return fakeCtx; }) as unknown as typeof AudioContext;
    const { playActivityStartedSound } = await loadSounds();

    playActivityStartedSound();

    expect(fakeCtx.createOscillator).toHaveBeenCalledTimes(3);
    expect(fakeCtx.createGain).toHaveBeenCalledTimes(3);
  });

  it("schedules oscillator notes for the limit-reached chime", async () => {
    const fakeCtx = createFakeAudioContext("running");
    window.AudioContext = vi.fn(function () { return fakeCtx; }) as unknown as typeof AudioContext;
    const { playLimitReachedSound } = await loadSounds();

    playLimitReachedSound();

    expect(fakeCtx.createOscillator).toHaveBeenCalledTimes(4);
  });

  it("resumes a suspended context before scheduling notes", async () => {
    const fakeCtx = createFakeAudioContext("suspended");
    window.AudioContext = vi.fn(function () { return fakeCtx; }) as unknown as typeof AudioContext;
    const { playActivityStartedSound } = await loadSounds();

    playActivityStartedSound();
    expect(fakeCtx.resume).toHaveBeenCalledTimes(1);
    expect(fakeCtx.createOscillator).not.toHaveBeenCalled();

    await fakeCtx.resume.mock.results[0].value;
    expect(fakeCtx.createOscillator).toHaveBeenCalledTimes(3);
  });

  it("primes and resumes a suspended context synchronously", async () => {
    const fakeCtx = createFakeAudioContext("suspended");
    window.AudioContext = vi.fn(function () { return fakeCtx; }) as unknown as typeof AudioContext;
    const { primeAudio } = await loadSounds();

    primeAudio();

    expect(fakeCtx.resume).toHaveBeenCalledTimes(1);
  });

  it("does not resume an already-running context when primed", async () => {
    const fakeCtx = createFakeAudioContext("running");
    window.AudioContext = vi.fn(function () { return fakeCtx; }) as unknown as typeof AudioContext;
    const { primeAudio } = await loadSounds();

    primeAudio();

    expect(fakeCtx.resume).not.toHaveBeenCalled();
  });

  it("swallows errors thrown while creating or scheduling a chime", async () => {
    window.AudioContext = vi.fn(() => {
      throw new Error("blocked by browser");
    }) as unknown as typeof AudioContext;
    const { playActivityStartedSound, primeAudio } = await loadSounds();

    expect(() => playActivityStartedSound()).not.toThrow();
    expect(() => primeAudio()).not.toThrow();
  });

  it("reuses the same AudioContext instance across calls", async () => {
    const fakeCtx = createFakeAudioContext("running");
    const factory = vi.fn(function () { return fakeCtx; });
    window.AudioContext = factory as unknown as typeof AudioContext;
    const { playActivityStartedSound, playLimitReachedSound } = await loadSounds();

    playActivityStartedSound();
    playLimitReachedSound();

    expect(factory).toHaveBeenCalledTimes(1);
  });
});
