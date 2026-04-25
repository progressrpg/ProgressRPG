import { describe, expect, it } from "vitest";

import {
  PLAYER_NAME_MAX_LENGTH,
  PLAYER_NAME_MIN_LENGTH,
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
