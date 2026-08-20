import { describe, expect, it } from "vitest";

import { asArray } from "./arrayUtils";

describe("asArray", () => {
  it("returns the array unchanged when given an array", () => {
    expect(asArray([1, 2, 3])).toEqual([1, 2, 3]);
  });

  it("returns an empty array for null", () => {
    expect(asArray(null)).toEqual([]);
  });

  it("returns an empty array for undefined", () => {
    expect(asArray(undefined)).toEqual([]);
  });
});
