import { describe, expect, it } from "vitest";

function assertBoardOwnership(input: { ownerId: string; currentUserId: string }) {
  if (!input.currentUserId || !input.ownerId) {
    throw new Error("FORBIDDEN");
  }
  if (input.ownerId !== input.currentUserId) {
    throw new Error("FORBIDDEN");
  }
}

describe("board authorization", () => {
  it("allows owner", () => {
    expect(() =>
      assertBoardOwnership({ ownerId: "user-1", currentUserId: "user-1" })
    ).not.toThrow();
  });

  it("rejects non-owner", () => {
    expect(() =>
      assertBoardOwnership({ ownerId: "user-1", currentUserId: "user-2" })
    ).toThrow("FORBIDDEN");
  });
});
