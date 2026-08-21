import { describe, expect, it } from "vitest";

import {
  PLAYER_NAME_MAX_LENGTH,
  PLAYER_NAME_MIN_LENGTH,
  getPlayerNameErrorMessage,
  getPlayerNameValidation,
  normalizePlayerName,
} from "./playerNameValidation";

describe("playerNameValidation", () => {
  it("trims outer whitespace", () => {
    expect(normalizePlayerName("  -Red Fox-  ")).toBe("-Red Fox-");
  });

  it("accepts boundary punctuation separators", () => {
    expect(getPlayerNameValidation("-Red Fox-").isValid).toBe(true);
    expect(getPlayerNameValidation("'Ava").isValid).toBe(true);
  });

  it("rejects repeated separators", () => {
    const validation = getPlayerNameValidation("Red--Fox");

    expect(validation.isValid).toBe(false);
    expect(
      validation.rules.find((rule) => rule.id === "separator-format")?.valid
    ).toBe(false);
  });

  it("rejects names outside the length bounds", () => {
    expect(getPlayerNameValidation("ab").isValid).toBe(false);
    expect(
      getPlayerNameValidation("a".repeat(PLAYER_NAME_MAX_LENGTH + 1)).isValid
    ).toBe(false);
    expect(
      getPlayerNameValidation("a".repeat(PLAYER_NAME_MIN_LENGTH)).isValid
    ).toBe(true);
  });
});

describe("getPlayerNameErrorMessage", () => {
  it("returns a generic message when there is no error", () => {
    expect(getPlayerNameErrorMessage(null)).toBe("Failed to update name.");
    expect(getPlayerNameErrorMessage(undefined)).toBe("Failed to update name.");
  });

  it("returns a generic message when the error has no message", () => {
    expect(getPlayerNameErrorMessage({})).toBe("Failed to update name.");
  });

  it("extracts the first field error from a DRF-style JSON message", () => {
    const error = { message: JSON.stringify({ name: ["This name is taken."] }) };
    expect(getPlayerNameErrorMessage(error)).toBe("This name is taken.");
  });

  it("falls back to a JSON detail field when there is no name error", () => {
    const error = { message: JSON.stringify({ detail: "Server error." }) };
    expect(getPlayerNameErrorMessage(error)).toBe("Server error.");
  });

  it("returns the raw message when it is not JSON", () => {
    expect(getPlayerNameErrorMessage({ message: "Network error" })).toBe("Network error");
  });

  it("returns the raw message when the parsed JSON has neither name nor detail", () => {
    const error = { message: JSON.stringify({ other: "field" }) };
    expect(getPlayerNameErrorMessage(error)).toBe(error.message);
  });
});
