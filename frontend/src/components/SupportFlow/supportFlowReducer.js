// SupportFlow/supportFlowReducer.js
// State machine for the support / activity modal flow.

// ---------------------------------------------------------------------------
// Configuration objects – extend these to add new options without touching
// reducer or screen logic.
// ---------------------------------------------------------------------------

export const SUPPORT_ACTIONS = {
  breathing: {
    id: "breathing",
    label: "Breathing exercise",
    steps: [
      "Breathe in slowly for 4 counts.",
      "Hold for 4 counts.",
      "Breathe out slowly for 6 counts.",
      "Repeat 3 times.",
    ],
  },
  eat_drink: {
    id: "eat_drink",
    label: "Eat or drink something",
    steps: [
      "Get a glass of water.",
      "Take 5 slow sips.",
      "Optional: grab a small snack.",
    ],
  },
  toilet: {
    id: "toilet",
    label: "Go to the toilet",
    steps: ["Stand up.", "Go now.", "Wash your hands.", "Come back ready."],
  },
};

export const ACTIVITY_PRESETS = {
  tiniest_step: {
    id: "tiniest_step",
    label: "Write the tiniest first step",
    durationSeconds: null,
    placeholder: "e.g. open the document, send one email, write one sentence",
    hint: "Make it so small it feels almost too easy. Examples: open the file, write the first line, send a single message.",
  },
  five_minutes: {
    id: "five_minutes",
    label: "Do it for 5 minutes",
    durationSeconds: 5 * 60,
    placeholder: "e.g. work on the report",
    hint: null,
  },
  other: {
    id: "other",
    label: "Something else",
    durationSeconds: null,
    placeholder: "What are you going to do?",
    hint: null,
  },
};

// ---------------------------------------------------------------------------
// Initial context
// ---------------------------------------------------------------------------

const initialCtx = (entrypoint = null) => ({
  entrypoint,
  supportActionId: null,
  activityPresetId: null,
  activityText: "",
  durationSeconds: null,
});

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

/**
 * Flow state shape:
 *   { isOpen: false }
 *   | { isOpen: true, screen: Screen, ctx: FlowContext }
 */
export function supportFlowReducer(state, event) {
  // Global events that work regardless of current screen
  switch (event.type) {
    case "OPEN_DAILY_REWARD":
      return {
        isOpen: true,
        screen: "DAILY_REWARD",
        ctx: initialCtx("daily"),
      };

    case "OPEN_ACTIVITY_REWARD":
      return {
        isOpen: true,
        screen: "ACTIVITY_REWARD",
        ctx: initialCtx("postActivity"),
      };

    case "CLOSE":
      return { isOpen: false };

    default:
      break;
  }

  // Remaining events require the modal to be open
  if (!state.isOpen) return state;

  switch (event.type) {
    case "GO_SUPPORT_MENU":
      return { ...state, screen: "SUPPORT_MENU" };

    case "READY_START":
      return {
        ...state,
        screen: "READY_ACTIVITY_MENU",
        ctx: { ...state.ctx, activityPresetId: null },
      };

    case "NOT_READY":
      return {
        ...state,
        screen: "NOT_READY_MENU",
        ctx: { ...state.ctx, supportActionId: null },
      };

    case "PICK_ACTIVITY_PRESET": {
      const preset = ACTIVITY_PRESETS[event.preset];
      const newCtx = {
        ...state.ctx,
        activityPresetId: event.preset,
        durationSeconds: preset?.durationSeconds ?? null,
        activityText: "",
      };
      return { ...state, screen: "ACTIVITY_INPUT", ctx: newCtx };
    }

    case "SET_ACTIVITY_TEXT":
      return { ...state, ctx: { ...state.ctx, activityText: event.text } };

    case "SET_DURATION_SECONDS":
      return {
        ...state,
        ctx: { ...state.ctx, durationSeconds: event.seconds },
      };

    case "PICK_SUPPORT_ACTION":
      return {
        ...state,
        screen: "SUPPORT_DETAIL",
        ctx: { ...state.ctx, supportActionId: event.id },
      };

    case "POST_SUPPORT_TRY_TASK":
      return {
        ...state,
        screen: "READY_ACTIVITY_MENU",
        ctx: { ...state.ctx, activityPresetId: null },
      };

    case "POST_SUPPORT_MORE_SUPPORT":
      return {
        ...state,
        screen: "NOT_READY_MENU",
        ctx: { ...state.ctx, supportActionId: null },
      };

    case "SHOW_POST_SUPPORT_MENU":
      return { ...state, screen: "POST_SUPPORT_MENU" };

    default:
      return state;
  }
}
