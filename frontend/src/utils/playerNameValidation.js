export const PLAYER_NAME_MIN_LENGTH = 3;
export const PLAYER_NAME_MAX_LENGTH = 20;

const allowedCharactersPattern = /^[A-Za-z0-9 _.'-]+$/;
const playerNamePattern = /^(?:[._'-])?[A-Za-z0-9]+(?:[ _.'-][A-Za-z0-9]+)*(?:[._'-])?$/;
const alphanumericPattern = /[A-Za-z0-9]/;

export function normalizePlayerName(value) {
  return value.trim();
}

export function getPlayerNameValidation(value) {
  const normalized = normalizePlayerName(value);

  const rules = [
    {
      id: "length",
      label: `Use ${PLAYER_NAME_MIN_LENGTH}-${PLAYER_NAME_MAX_LENGTH} characters.`,
      valid: (
        normalized.length >= PLAYER_NAME_MIN_LENGTH
        && normalized.length <= PLAYER_NAME_MAX_LENGTH
      ),
    },
    {
      id: "characters",
      label: "Allowed: spaces, hyphens (-), apostrophes ('), underscores (_), and periods (.).",
      valid: normalized.length > 0 && allowedCharactersPattern.test(normalized),
    },
    {
      id: "alphanumeric",
      label: "Include at least one letter or number.",
      valid: alphanumericPattern.test(normalized),
    },
    {
      id: "separator-format",
      label: "No repeated separators. Spaces can't be at the start or end.",
      valid: normalized.length > 0 && playerNamePattern.test(normalized),
    },
  ];

  return {
    normalized,
    rules,
    isValid: rules.every((rule) => rule.valid),
  };
}

export function getPlayerNameErrorMessage(error) {
  if (!error?.message) {
    return "Failed to update name.";
  }

  try {
    const parsedError = JSON.parse(error.message);
    if (Array.isArray(parsedError.name) && parsedError.name.length > 0) {
      return parsedError.name[0];
    }
    if (typeof parsedError.detail === "string") {
      return parsedError.detail;
    }
  } catch {
    // Fall back to the raw error message when the API did not return JSON.
  }

  return error.message;
}
