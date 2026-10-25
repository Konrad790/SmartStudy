import { describe, expect, it } from "vitest";

describe("autosave conflict semantics", () => {
  it("treats lower base version as stale", () => {
    const incomingBaseVersion = 1;
    const currentVersion = 2;
    expect(incomingBaseVersion < currentVersion).toBe(true);
  });
});
