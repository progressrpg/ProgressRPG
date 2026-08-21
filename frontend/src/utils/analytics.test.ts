import { afterEach, describe, expect, it, vi } from "vitest";

const initialize = vi.fn();
const send = vi.fn();
const event = vi.fn();

vi.mock("react-ga4", () => ({
  default: { initialize, send, event },
}));

interface AnalyticsEnv {
  PROD?: boolean;
  VITE_GA_TRACKING_ID?: string;
  VITE_GA_TEST_MODE?: string;
}

async function loadAnalytics(env: AnalyticsEnv) {
  vi.resetModules();
  vi.stubEnv("PROD", env.PROD ?? false);
  vi.stubEnv("VITE_GA_TRACKING_ID", env.VITE_GA_TRACKING_ID ?? "");
  vi.stubEnv("VITE_GA_TEST_MODE", env.VITE_GA_TEST_MODE ?? "");
  return import("./analytics");
}

describe("analytics", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("does nothing outside prod/test mode, even with a tracking id", async () => {
    const { initGA, logPageView, trackEvent } = await loadAnalytics({
      PROD: false,
      VITE_GA_TRACKING_ID: "G-TEST",
    });

    initGA();
    logPageView("/tasks");
    trackEvent("task_completed");

    expect(initialize).not.toHaveBeenCalled();
    expect(send).not.toHaveBeenCalled();
    expect(event).not.toHaveBeenCalled();
  });

  it("does nothing when active but no tracking id is configured", async () => {
    const { initGA, logPageView, trackEvent } = await loadAnalytics({
      VITE_GA_TEST_MODE: "true",
    });

    initGA();
    logPageView("/tasks");
    trackEvent("task_completed");

    expect(initialize).not.toHaveBeenCalled();
    expect(send).not.toHaveBeenCalled();
    expect(event).not.toHaveBeenCalled();
  });

  it("initializes, logs page views, and tracks events when test mode and a tracking id are set", async () => {
    const { initGA, logPageView, trackEvent } = await loadAnalytics({
      VITE_GA_TEST_MODE: "true",
      VITE_GA_TRACKING_ID: "G-TEST",
    });

    initGA();
    expect(initialize).toHaveBeenCalledWith("G-TEST", { testMode: true });

    logPageView("/tasks");
    expect(send).toHaveBeenCalledWith({ hitType: "pageview", page: "/tasks" });

    trackEvent("task_completed", { taskId: 5 });
    expect(event).toHaveBeenCalledWith("task_completed", { taskId: 5 });
  });

  it("defaults trackEvent's params to an empty object", async () => {
    const { trackEvent } = await loadAnalytics({
      VITE_GA_TEST_MODE: "true",
      VITE_GA_TRACKING_ID: "G-TEST",
    });

    trackEvent("task_completed");

    expect(event).toHaveBeenCalledWith("task_completed", {});
  });
});
