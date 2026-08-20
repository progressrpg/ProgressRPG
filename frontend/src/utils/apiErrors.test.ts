import { describe, expect, it } from "vitest";

import { extractApiMessage, readJsonSafe } from "./apiErrors";

describe("readJsonSafe", () => {
  it("returns the parsed JSON body", async () => {
    const response = { json: async () => ({ detail: "nope" }) } as Response;
    await expect(readJsonSafe(response)).resolves.toEqual({ detail: "nope" });
  });

  it("returns null when the body is not valid JSON", async () => {
    const response = { json: async () => { throw new Error("invalid json"); } } as unknown as Response;
    await expect(readJsonSafe(response)).resolves.toBeNull();
  });
});

describe("extractApiMessage", () => {
  it("returns the fallback when data is null", () => {
    expect(extractApiMessage(null, "fallback")).toBe("fallback");
  });

  it("returns the fallback when data is not an object", () => {
    expect(extractApiMessage("oops" as never, "fallback")).toBe("fallback");
  });

  it("prefers a string detail field", () => {
    expect(extractApiMessage({ detail: "specific error" }, "fallback")).toBe("specific error");
  });

  it("ignores an empty detail string", () => {
    expect(extractApiMessage({ name: ["Name is required"], detail: "" }, "fallback")).toBe(
      "Name is required"
    );
  });

  it("falls back to the first value of the first field-error array", () => {
    expect(extractApiMessage({ name: ["Name is required"] }, "fallback")).toBe("Name is required");
  });

  it("stringifies a non-string first entry", () => {
    expect(extractApiMessage({ code: [404] }, "fallback")).toBe("404");
  });

  it("returns the fallback when the first entry is not a non-empty array", () => {
    expect(extractApiMessage({ name: [] }, "fallback")).toBe("fallback");
  });

  it("returns the fallback when there are no fields at all", () => {
    expect(extractApiMessage({}, "fallback")).toBe("fallback");
  });
});
